"""
SQLite-based caching system for ArXiv summarization pipeline.
Caches similarity scores, rating scores, summaries, and processed papers.
Handles config change detection and automatic cache invalidation.
"""

import sqlite3
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

@dataclass
class CacheConfig:
    dir: str
    ttl_days: int

class CacheManager:
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache_dir = Path(config.dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Database and summaries directory
        self.db_path = self.cache_dir / "cache.db"
        self.summaries_dir = self.cache_dir / "summaries"
        self.summaries_dir.mkdir(exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Similarity scores from embedder
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS similarity_scores (
                arxiv_id TEXT PRIMARY KEY,
                score REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Rating scores from LLM
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rating_scores (
                arxiv_id TEXT PRIMARY KEY,
                score REAL NOT NULL,
                details_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Summary file references
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS summaries (
                arxiv_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Delivered papers tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_papers (
                arxiv_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata_json TEXT NOT NULL
            )
        ''')
        
        # Config change tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_history (
                config_hash TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _calculate_config_hash(self, config_dict: Dict[str, Any]) -> str:
        """Calculate hash of configuration dictionary."""
        # Convert to JSON string with sorted keys for consistent hashing
        config_str = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()
    
    def _get_component_hash(self, config_dict: Dict[str, Any], component: str) -> str:
        """Calculate hash for specific component configuration."""
        if component in config_dict:
            component_str = json.dumps(config_dict[component], sort_keys=True)
            return hashlib.sha256(component_str.encode()).hexdigest()
        return ""
    
    # Similarity scores (from embedder)
    def get_similarity_score(self, arxiv_id: str) -> Optional[float]:
        """Get cached similarity score for paper."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT score FROM similarity_scores WHERE arxiv_id = ?',
            (arxiv_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def store_similarity_score(self, arxiv_id: str, score: float):
        """Store similarity score for paper."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT OR REPLACE INTO similarity_scores (arxiv_id, score) VALUES (?, ?)',
            (arxiv_id, score)
        )
        
        conn.commit()
        conn.close()
    
    # Rating scores (from LLM rater)
    def get_rating_score(self, arxiv_id: str) -> Optional[Tuple[float, Dict]]:
        """Get cached rating score and details for paper."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT score, details_json FROM rating_scores WHERE arxiv_id = ?',
            (arxiv_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            score, details_json = result
            details = json.loads(details_json)
            return score, details
        return None
    
    def store_rating_score(self, arxiv_id: str, score: float, details: Dict):
        """Store rating score and details for paper."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        details_json = json.dumps(details)
        cursor.execute(
            'INSERT OR REPLACE INTO rating_scores (arxiv_id, score, details_json) VALUES (?, ?, ?)',
            (arxiv_id, score, details_json)
        )
        
        conn.commit()
        conn.close()
    
    # Summaries (stored as files)
    def get_summary(self, arxiv_id: str) -> Optional[str]:
        """Get cached summary for paper."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT file_path FROM summaries WHERE arxiv_id = ?',
            (arxiv_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            file_path = Path(result[0])
            if file_path.exists():
                return file_path.read_text(encoding='utf-8')
            else:
                # File doesn't exist, remove stale record
                self._remove_summary_record(arxiv_id)
        
        return None
    
    def store_summary(self, arxiv_id: str, summary: str):
        """Store summary for paper."""
        # Generate filename with timestamp for uniqueness
        timestamp = int(time.time())
        filename = f"{arxiv_id}_{timestamp}.md"
        file_path = self.summaries_dir / filename
        
        # Write summary to file
        file_path.write_text(summary, encoding='utf-8')
        
        # Store reference in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT OR REPLACE INTO summaries (arxiv_id, file_path) VALUES (?, ?)',
            (arxiv_id, str(file_path))
        )
        
        conn.commit()
        conn.close()
    
    def _remove_summary_record(self, arxiv_id: str):
        """Remove stale summary record from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM summaries WHERE arxiv_id = ?', (arxiv_id,))
        
        conn.commit()
        conn.close()
    
    # Processed papers tracking
    def is_paper_processed(self, arxiv_id: str) -> bool:
        """Check if paper has been processed (delivered)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT 1 FROM processed_papers WHERE arxiv_id = ?',
            (arxiv_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def mark_paper_processed(self, arxiv_id: str, metadata: Dict):
        """Mark paper as processed (delivered)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata)
        cursor.execute(
            'INSERT OR REPLACE INTO processed_papers (arxiv_id, metadata_json) VALUES (?, ?)',
            (arxiv_id, metadata_json)
        )
        
        conn.commit()
        conn.close()
    
    # Config change detection & cache clearing
    def detect_and_handle_config_changes(self, current_config: Dict[str, Any]):
        """Detect config changes and clear appropriate caches."""
        current_hash = self._calculate_config_hash(current_config)
        
        # Get the last config hash
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT config_hash FROM config_history ORDER BY created_at DESC LIMIT 1'
        )
        result = cursor.fetchone()
        last_hash = result[0] if result else None
        
        if last_hash != current_hash:
            print(f"Configuration changed. Previous: {last_hash}, Current: {current_hash}")
            
            # Check which components changed
            if last_hash is None:
                print("First run - no cache clearing needed")
            else:
                # For simplicity, we'll clear all caches on any config change
                # In a more sophisticated implementation, we could compare component hashes
                print("Configuration changed - clearing all caches except processed papers")
                self.clear_all_cache(preserve_processed_papers=True)
            
            # Update config hash
            cursor.execute(
                'INSERT INTO config_history (config_hash) VALUES (?)',
                (current_hash,)
            )
            conn.commit()
        
        conn.close()
    
    def clear_embedder_cache(self):
        """Clear cached similarity scores."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM similarity_scores')
        
        conn.commit()
        conn.close()
        print("Cleared embedder cache (similarity scores)")
    
    def clear_rater_cache(self):
        """Clear cached rating scores."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM rating_scores')
        
        conn.commit()
        conn.close()
        print("Cleared rater cache (rating scores)")
    
    def clear_summarizer_cache(self):
        """Clear cached summaries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all summary file paths before deleting records
        cursor.execute('SELECT file_path FROM summaries')
        file_paths = [row[0] for row in cursor.fetchall()]
        
        # Delete database records
        cursor.execute('DELETE FROM summaries')
        conn.commit()
        conn.close()
        
        # Delete summary files
        for file_path in file_paths:
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception as e:
                print(f"Warning: Could not delete summary file {file_path}: {e}")
        
        print("Cleared summarizer cache (summaries)")
    
    def clear_all_cache(self, preserve_processed_papers: bool = True):
        """Clear all caches, optionally preserving processed papers tracking."""
        self.clear_embedder_cache()
        self.clear_rater_cache()
        self.clear_summarizer_cache()
        
        if not preserve_processed_papers:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM processed_papers')
            conn.commit()
            conn.close()
            print("Cleared processed papers tracking")
    
    # Maintenance
    def cleanup_expired(self):
        """Remove expired cache entries based on TTL."""
        cutoff_date = datetime.now() - timedelta(days=self.config.ttl_days)
        cutoff_timestamp = cutoff_date.isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get expired summary file paths before deleting
        cursor.execute(
            'SELECT file_path FROM summaries WHERE created_at < ?',
            (cutoff_timestamp,)
        )
        expired_files = [row[0] for row in cursor.fetchall()]
        
        # Delete expired records
        tables = ['similarity_scores', 'rating_scores', 'summaries', 'processed_papers']
        total_deleted = 0
        
        for table in tables:
            cursor.execute(f'DELETE FROM {table} WHERE created_at < ?', (cutoff_timestamp,))
            deleted = cursor.rowcount
            total_deleted += deleted
            if deleted > 0:
                print(f"Deleted {deleted} expired records from {table}")
        
        conn.commit()
        conn.close()
        
        # Delete expired summary files
        files_deleted = 0
        for file_path in expired_files:
            try:
                Path(file_path).unlink(missing_ok=True)
                files_deleted += 1
            except Exception as e:
                print(f"Warning: Could not delete expired summary file {file_path}: {e}")
        
        if files_deleted > 0:
            print(f"Deleted {files_deleted} expired summary files")
        
        if total_deleted == 0 and files_deleted == 0:
            print("No expired cache entries found")
        
        return total_deleted + files_deleted
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Count records in each table
        tables = ['similarity_scores', 'rating_scores', 'summaries', 'processed_papers']
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[f'{table}_count'] = cursor.fetchone()[0]
        
        # Calculate total cache size
        cache_size_bytes = 0
        if self.db_path.exists():
            cache_size_bytes += self.db_path.stat().st_size
        
        # Add summary files size
        summary_files_size = 0
        summary_files_count = 0
        if self.summaries_dir.exists():
            for file_path in self.summaries_dir.glob('*.md'):
                try:
                    summary_files_size += file_path.stat().st_size
                    summary_files_count += 1
                except Exception:
                    pass
        
        cache_size_bytes += summary_files_size
        
        stats.update({
            'cache_size_bytes': cache_size_bytes,
            'cache_size_mb': round(cache_size_bytes / (1024 * 1024), 2),
            'summary_files_count': summary_files_count,
            'summary_files_size_mb': round(summary_files_size / (1024 * 1024), 2),
            'ttl_days': self.config.ttl_days,
            'cache_directory': str(self.cache_dir)
        })
        
        conn.close()
        return stats

if __name__ == "__main__":
    """Example usage and testing."""
    config = CacheConfig(
        dir="~/.cache/arxiv-autosumm",
        ttl_days=14,
        store_pdf=False
    )
    
    cache = CacheManager(config)
    
    # Test config change detection
    test_config = {
        "embedder": {"model": "test-model"},
        "summarizer": {"model": "test-summarizer"}
    }
    cache.detect_and_handle_config_changes(test_config)
    
    # Test caching operations
    arxiv_id = "2301.00001"
    
    # Test similarity score
    cache.store_similarity_score(arxiv_id, 0.85)
    score = cache.get_similarity_score(arxiv_id)
    print(f"Similarity score: {score}")
    
    # Test rating score
    rating_details = {"novelty": 4, "methodology": 5}
    cache.store_rating_score(arxiv_id, 4.2, rating_details)
    rating = cache.get_rating_score(arxiv_id)
    print(f"Rating score: {rating}")
    
    # Test summary
    test_summary = "This is a test summary of the paper."
    cache.store_summary(arxiv_id, test_summary)
    cached_summary = cache.get_summary(arxiv_id)
    print(f"Summary: {cached_summary}")
    
    # Test processed papers
    cache.mark_paper_processed(arxiv_id, {"title": "Test Paper"})
    is_processed = cache.is_paper_processed(arxiv_id)
    print(f"Is processed: {is_processed}")
    
    # Print stats
    stats = cache.get_cache_stats()
    print(f"Cache stats: {stats}")