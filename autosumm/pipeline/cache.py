"""
SQLite-based caching system for ArXiv summarization pipeline.
Caches similarity scores, rating scores, and tracks delivered papers.
Handles config change detection and automatic cache invalidation.
"""

import sqlite3
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, is_dataclass
from typing import Optional, Tuple, Dict, Any, List

logger = logging.getLogger(__name__)

@dataclass
class CacherConfig:
    dir: str
    ttl_days: int
    max_pdf_cache_size_mb: int = 1024

class Cacher:
    def __init__(self, config: CacherConfig):
        self.config = config
        self.cache_dir = Path(config.dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Database path
        self.db_path = self.cache_dir / "cache.db"

        # PDF cache directory
        self.pdf_cache_dir = self.cache_dir / "pdfs"
        self.pdf_cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing cacher at {self.db_path}")
        logger.info(f"Cache TTL: {config.ttl_days} days")

        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        logger.debug("Creating database tables...")
        
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
        
        # Delivered papers tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delivered_papers (
                arxiv_id TEXT PRIMARY KEY,
                delivered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        logger.info("Database tables initialized successfully")
    
    def _to_serializable(self, obj: Any) -> Any:
        """Recursively converts objects to JSON-serializable types. Handles dataclasses/Pydantic models, dictionaries and lists"""
        if hasattr(obj, 'model_dump'):
            return self._to_serializable(obj.model_dump())
        elif hasattr(obj,'dict'):
            return self._to_serializable(obj.dict())
        elif is_dataclass(obj):
            return self._to_serializable(asdict(obj))
        elif isinstance(obj,dict):
            return {k: self._to_serializable(v) for k,v in obj.items()}
        elif isinstance(obj,list):
            return [self._to_serializable(item) for item in obj]
        else:
            return obj

    def _calculate_config_hash(self, config_dict: Dict[str, Any]) -> str:
        """Calculate hash of configuration dictionary."""
        serializable_config = self._to_serializable(config_dict)
        config_str = json.dumps(serializable_config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()
    
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
        
        if result:
            logger.info(f"Cache hit: similarity score for {arxiv_id} = {result[0]}")
            return result[0]
        else:
            logger.debug(f"Cache miss: no similarity score for {arxiv_id}")
            return None
    
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
        logger.debug(f"Stored similarity score for {arxiv_id}: {score}")
    
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
            logger.info(f"Cache hit: rating score for {arxiv_id} = {score}")
            return score, details
        else:
            logger.debug(f"Cache miss: no rating score for {arxiv_id}")
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
        logger.debug(f"Stored rating score for {arxiv_id}: {score}")
    
    # Delivered papers tracking
    def is_paper_delivered(self, arxiv_id: str) -> bool:
        """Check if paper has been delivered."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT 1 FROM delivered_papers WHERE arxiv_id = ?',
            (arxiv_id,)
        )
        result = cursor.fetchone()
        conn.close()

        delivered = result is not None
        logger.debug(f"Paper {arxiv_id} delivered: {delivered}")
        return delivered

    def mark_paper_delivered(self, arxiv_id: str, metadata: Dict):
        """Mark paper as delivered."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        metadata_json = json.dumps(metadata)
        cursor.execute(
            'INSERT OR REPLACE INTO delivered_papers (arxiv_id, metadata_json) VALUES (?, ?)',
            (arxiv_id, metadata_json)
        )

        conn.commit()
        conn.close()
        logger.info(f"Marked paper {arxiv_id} as delivered")
        
    # Config change detection & cache clearing
    def detect_and_handle_config_changes(self, current_config: Dict[str, Any]):
        """Detect config changes and clear appropriate caches."""
        current_hash = self._calculate_config_hash(current_config)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT config_hash FROM config_history ORDER BY created_at DESC LIMIT 1'
        )
        result = cursor.fetchone()
        last_hash = result[0] if result else None
        
        if last_hash != current_hash:
            logger.info(f"Configuration changed. Previous: {last_hash}, Current: {current_hash}")
            
            if last_hash is None:
                logger.info("First run - no cache clearing needed")
            else:
                logger.info("Configuration changed - clearing all caches except delivered papers")
                self.clear_all_cache(preserve_delivered_papers=True)
            
            cursor.execute(
                'INSERT INTO config_history (config_hash) VALUES (?)',
                (current_hash,)
            )
            conn.commit()
        else:
            logger.debug("Configuration unchanged - no cache clearing needed")
        
        conn.close()
    
    def clear_embedder_cache(self):
        """Clear cached similarity scores."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM similarity_scores')
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"Cleared embedder cache (similarity scores) - deleted {deleted} entries")
    
    def clear_rater_cache(self):
        """Clear cached rating scores."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM rating_scores')
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"Cleared rater cache (rating scores) - deleted {deleted} entries")
    
    def clear_all_cache(self, preserve_delivered_papers: bool = True):
        """Clear all caches, optionally preserving delivered papers tracking."""
        logger.info("Clearing all caches...")
        self.clear_embedder_cache()
        self.clear_rater_cache()

        if not preserve_delivered_papers:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM delivered_papers')
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            logger.info(f"Cleared delivered papers tracking - deleted {deleted} entries")
    
    # Maintenance
    def cleanup_expired(self):
        """Remove expired cache entries based on TTL."""
        cutoff_date = datetime.now() - timedelta(days=self.config.ttl_days)
        cutoff_timestamp = cutoff_date.isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tables = ['similarity_scores', 'rating_scores', 'delivered_papers']
        total_deleted = 0
        
        for table in tables:
            cursor.execute(f'DELETE FROM {table} WHERE created_at < ?', (cutoff_timestamp,))
            deleted = cursor.rowcount
            total_deleted += deleted
            if deleted > 0:
                logger.info(f"Deleted {deleted} expired records from {table}")
        
        conn.commit()
        conn.close()
        
        if total_deleted == 0:
            logger.debug("No expired cache entries found")
        else:
            logger.info(f"Total expired entries cleaned: {total_deleted}")
        
        return total_deleted
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Count records in each table
        tables = ['similarity_scores', 'rating_scores', 'delivered_papers']
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[f'{table}_count'] = cursor.fetchone()[0]
        
        # Calculate database size
        cache_size_bytes = 0
        if self.db_path.exists():
            cache_size_bytes = self.db_path.stat().st_size
        
        stats.update({
            'cache_size_bytes': cache_size_bytes,
            'cache_size_mb': round(cache_size_bytes / (1024 * 1024), 2),
            'ttl_days': self.config.ttl_days,
            'cache_directory': str(self.cache_dir)
        })
        
        conn.close()
        return stats

    def cleanup_pdf_cache(self, used_pdf_urls: List[str]):
        """
        Remove unused PDFs if cache size exceeds max_pdf_cache_size_mb.
        Removes a fraction of oldest unused PDFs when size limit is exceeded.

        Args:
            used_pdf_urls: List of PDF URLs used in current run
        """
        if not self.pdf_cache_dir.exists():
            return

        # Calculate current cache size
        total_size = 0
        pdf_files = []

        for pdf_file in self.pdf_cache_dir.glob("*.pdf"):
            file_size = pdf_file.stat().st_size
            filename_hash = pdf_file.stem  # Remove .pdf extension
            total_size += file_size
            pdf_files.append({
                'path': pdf_file,
                'filename_hash': filename_hash,
                'size': file_size,
                'mtime': pdf_file.stat().st_mtime
            })

        total_size_mb = total_size / (1024 * 1024)

        if total_size_mb <= self.config.max_pdf_cache_size_mb:
            logger.debug(f"PDF cache size {total_size_mb:.2f}MB is within limit {self.config.max_pdf_cache_size_mb}MB")
            return

        logger.info(f"PDF cache size {total_size_mb:.2f}MB exceeds limit {self.config.max_pdf_cache_size_mb}MB, cleaning up...")

        # Create set of used URL hashes
        used_hashes_set = {hashlib.md5(url.encode()).hexdigest() for url in used_pdf_urls}

        # Separate used and unused PDFs
        unused_pdfs = [pdf for pdf in pdf_files if pdf['filename_hash'] not in used_hashes_set]

        if not unused_pdfs:
            logger.info("No unused PDFs to remove, cache contains only used files")
            return

        # Sort unused PDFs by modification time (oldest first)
        unused_pdfs.sort(key=lambda x: x['mtime'])

        # Calculate target size: 80% of max or max-128MB, whichever is larger
        target_size_mb = max(self.config.max_pdf_cache_size_mb * 0.8, 
                           self.config.max_pdf_cache_size_mb - 128)
        size_to_remove_mb = total_size_mb - target_size_mb

        removed_files = 0
        removed_size_mb = 0

        for pdf in unused_pdfs:
            if removed_size_mb >= size_to_remove_mb:
                break

            try:
                pdf['path'].unlink()
                removed_size_mb += pdf['size'] / (1024 * 1024)
                removed_files += 1
                logger.debug(f"Removed unused PDF: {pdf['path']}")
            except Exception as e:
                logger.warning(f"Failed to remove PDF {pdf['path']}: {e}")

        new_total_size_mb = total_size_mb - removed_size_mb
        logger.info(f"Removed {removed_files} unused PDFs ({removed_size_mb:.2f}MB), "
                   f"new cache size: {new_total_size_mb:.2f}MB")