"""
Prototype main function to test the ArXiv summarization pipeline.
Tests the complete workflow: fetch -> parse -> rate -> summarize -> save
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

# Import all the implemented modules
from pipeline.fetch import fetch_paper_metadata, FetchConfig
from pipeline.parse import parse_fast, parse_vlm, ParseConfig, ParserVLMConfig
from pipeline.rate import rate_embed, rate_llm, RateConfig, RaterEmbedderConfig, RaterLLMConfig
from pipeline.summarize import summarize, SummarizerConfig
from pipeline.cache import CacheManager, CacheConfig
from pipeline.client import BatchConfig


def main():
    print("=== ArXiv Summarization Pipeline Prototype ===\n")
    
    # === 1. Setup Hardcoded Configurations ===
    print("Setting up configurations...")
    
    # Date range: last 7 days for testing
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    start_date_str = start_date.strftime("%Y%m%d") 
    end_date_str = end_date.strftime("%Y%m%d")
    
    # Fetch config
    fetch_config = FetchConfig(
        categories=["cs.LG"],  # Computer Science - Artificial Intelligence
        start_date=start_date_str,
        end_date=end_date_str,
        max_results=10,  # Fetch 10 papers
        max_retires=2,
        output_dir="./tmp/downloads"
    )
    
    # Parse configs
    parse_config = ParseConfig(
        enable_vlm=True,
        tmp_dir="./tmp"
    )
    
    vlm_config = ParserVLMConfig(
        provider="aliyun",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-vl-plus",
        batch=True,
        dpi=200
    )
    
    # Rate configs
    embedder_config = RaterEmbedderConfig(
        provider="ollama",
        api_key=None,
        base_url="http://localhost:11434",
        model="dengcao/Qwen3-Embedding-8B:Q5_K_M",
        query_template="High-quality {user_interests} research paper with novel contributions, rigorous methodology, clear presentation, and significant impact",
        user_interests="AI, machine learning and computer science",
        context_length=32768
    )
    
    llm_rater_config = RaterLLMConfig(
        provider="ollama",
        api_key=None,
        base_url="http://localhost:11434",
        model="qwen2.5:3b",
        batch=False,
        system_prompt="""You are an expert research paper reviewer with deep knowledge in computer science, AI, and machine learning. Your task is to evaluate research papers based on multiple criteria and provide structured ratings.

You must respond with a valid JSON object containing:
1. "ratings": A dictionary with numerical scores (1-10) for each criterion
2. "justifications": A dictionary with brief explanations for each rating

Be objective, concise, and focus on the paper's technical merit.""",
        user_prompt_template="""Please evaluate this research paper based on the following criteria:

{criteria_text}

Rate each criterion on a scale of 1-10 where:
- 1-3: Poor/Below average
- 4-6: Average/Adequate  
- 7-8: Good/Above average
- 9-10: Excellent/Outstanding

Paper content:
{paper_text}

Provide your response as a JSON object with "ratings" and "justifications" fields.""",
        completion_options={
            "temperature": 0.2,
            "max_tokens": 1024
        },
        context_length=32768,
        criteria={
            "novelty": {
                "description": "How original and innovative are the contributions?",
                "weight": 0.3
            },
            "methodology": {
                "description": "How rigorous is the experimental design and evaluation?",
                "weight": 0.25
            },
            "clarity": {
                "description": "How well-written and understandable is the paper?",
                "weight": 0.2
            },
            "impact": {
                "description": "How significant are the potential applications and impact?",
                "weight": 0.15
            },
            "relevance": {
                "description": "How well does this paper match the user's research interests?",
                "weight": 0.1
            }
        }
    )
    
    rate_config = RateConfig(
        top_k=5,  # Rate top 5 papers with LLM after embedding
        embedder=embedder_config,
        llm=llm_rater_config
    )
    
    # Summarizer config
    summarizer_config = SummarizerConfig(
        provider="siliconflow",
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        base_url="https://api.siliconflow.cn/v1",
        model="THUDM/GLM-4-9B-0414",
        batch=False,  # Use single requests for simplicity in prototype
        system_prompt="""You are an expert research assistant specializing in academic paper analysis. Your task is to create concise, comprehensive summaries of research papers that capture the key contributions, methodology, and significance while remaining accessible to researchers in related fields.""",
        user_prompt_template="""Please provide a structured summary of the following research paper. Focus on:

1. **Main Contribution**: What is the primary novel contribution or finding?
2. **Methodology**: What approach or techniques were used?
3. **Key Results**: What are the most important results or findings?
4. **Significance**: Why is this work important and what are its implications?

Keep the summary concise but comprehensive, suitable for researchers who want to quickly understand the paper's value and relevance.

Paper content:
{paper_content}

Summary:""",
        completion_options={
            "temperature": 0.6,
            "max_tokens": 4096,
            "top_p": 0.9
        },
        context_length=32768
    )
    
    # Cache config
    cache_config = CacheConfig(
        dir="./tmp/cache",
        ttl_days=14,
        store_pdf=False
    )
    
    # Batch config
    batch_config = BatchConfig(
        tmp_dir="./tmp",
        max_wait_hours=1,
        poll_intervall_seconds=10,
        fallback_on_error=True
    )
    
    # Initialize cache
    cache = CacheManager(cache_config)
    
    # === 2. Fetch Papers ===
    print(f"Fetching papers from {start_date_str} to {end_date_str}...")
    papers = fetch_paper_metadata(fetch_config)
    print(f"Fetched {len(papers)} papers")
    
    if not papers:
        print("No papers found. Exiting.")
        return
    
    # === 3. Check Processed Papers ===
    print("Checking for already processed papers...")
    unprocessed_papers = [p for p in papers if not cache.is_paper_processed(p.arxiv_id)]
    print(f"Found {len(unprocessed_papers)} unprocessed papers")
    
    if not unprocessed_papers:
        print("All papers already processed. Exiting.")
        return
    
    # === 4. Fast Parse for Rating ===
    print("Fast parsing papers for rating...")
    pdf_urls = [p.pdf_url for p in unprocessed_papers]
    fast_parse_results = parse_fast(pdf_urls, parse_config)
    
    # Filter successful parses
    successful_parses = []
    successful_papers = []
    for paper, parse_result in zip(unprocessed_papers, fast_parse_results):
        if parse_result.success:
            successful_parses.append(parse_result.content)
            successful_papers.append(paper)
        else:
            print(f"Fast parse failed for {paper.title}: {parse_result.error}")
    
    print(f"Successfully fast parsed {len(successful_parses)} papers")
    
    if not successful_parses:
        print("No successful parses. Exiting.")
        return
    
    # === 5. Rate Papers (Coarse-to-Fine) ===
    print("Rating papers with embedder (coarse filtering)...")
    embed_results = rate_embed(successful_parses, rate_config)
    
    # Combine papers with their embedding scores
    paper_scores = []
    for paper, parse_content, embed_result in zip(successful_papers, successful_parses, embed_results):
        if embed_result.success:
            # Check cache first
            cached_score = cache.get_similarity_score(paper.arxiv_id)
            if cached_score is not None:
                score = cached_score
            else:
                score = embed_result.score
                cache.store_similarity_score(paper.arxiv_id, score)
            
            paper_scores.append({
                'paper': paper,
                'content': parse_content,
                'embed_score': score
            })
    
    # Sort by embedding score and take top-k for LLM rating
    paper_scores.sort(key=lambda x: x['embed_score'], reverse=True)
    top_k_for_llm = paper_scores[:rate_config.top_k]
    
    print(f"Selected top {len(top_k_for_llm)} papers for LLM rating")
    
    # Rate with LLM (fine filtering)
    print("Rating top papers with LLM (fine filtering)...")
    top_k_contents = [item['content'] for item in top_k_for_llm]
    llm_results = rate_llm(top_k_contents, rate_config, batch_config)
    
    # Combine LLM scores and cache them
    final_scores = []
    for item, llm_result in zip(top_k_for_llm, llm_results):
        if llm_result.success:
            # Check cache first
            cached_rating = cache.get_rating_score(item['paper'].arxiv_id)
            if cached_rating is not None:
                llm_score, details = cached_rating
            else:
                llm_score = llm_result.score
                details = {"method": llm_result.method}
                cache.store_rating_score(item['paper'].arxiv_id, llm_score, details)
            
            # Combine embedding and LLM scores (you can adjust weighting)
            combined_score = 0.3 * item['embed_score'] + 0.7 * llm_score
            final_scores.append({
                'paper': item['paper'],
                'content': item['content'],
                'embed_score': item['embed_score'],
                'llm_score': llm_score,
                'combined_score': combined_score
            })
    
    # === 6. Select Best Papers for Summarization ===
    final_scores.sort(key=lambda x: x['combined_score'], reverse=True)
    selected_papers = final_scores[:2]  # Select top 2 papers for summarization
    
    print(f"Selected {len(selected_papers)} papers for summarization:")
    for i, item in enumerate(selected_papers):
        print(f"  {i+1}. {item['paper'].title} (combined score: {item['combined_score']:.3f})")
    
    # === 7. VLM Parse Selected Papers ===
    print("VLM parsing selected papers for high-quality content...")
    selected_pdf_urls = [item['paper'].pdf_url for item in selected_papers]
    vlm_parse_results = parse_vlm(selected_pdf_urls, vlm_config, batch_config)
    
    # Filter successful VLM parses
    papers_for_summary = []
    contents_for_summary = []
    for item, vlm_result in zip(selected_papers, vlm_parse_results):
        if vlm_result.success:
            papers_for_summary.append(item['paper'])
            contents_for_summary.append(vlm_result.content)
        else:
            print(f"VLM parse failed for {item['paper'].title}: {vlm_result.error}")
    
    print(f"Successfully VLM parsed {len(contents_for_summary)} papers")
    
    if not contents_for_summary:
        print("No successful VLM parses. Exiting.")
        return
    
    # === 8. Summarize Papers ===
    print("Generating summaries...")
    summary_results = summarize(contents_for_summary, summarizer_config, batch_config)
    
    # === 9. Save to Markdown Files ===
    print("Saving summaries to markdown files...")
    output_dir = Path("./summaries")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for paper, summary_result in zip(papers_for_summary, summary_results):
        if summary_result.success:
            # Create filename
            safe_title = "".join(c for c in paper.title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
            filename = f"{paper.arxiv_id}_{safe_title}_{timestamp}.md"
            filepath = output_dir / filename
            
            # Create markdown content with metadata
            markdown_content = f"""# {paper.title}

**Authors:** {', '.join(paper.authors)}
**ArXiv ID:** {paper.arxiv_id}
**Categories:** {', '.join(paper.categories)}
**Submitted:** {paper.submitted_date.strftime('%Y-%m-%d')}
**PDF URL:** {paper.pdf_url}

---

## Summary

{summary_result.content}

---

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            # Write to file
            filepath.write_text(markdown_content, encoding='utf-8')
            print(f"  Saved: {filepath}")
            
            # Cache the summary
            cache.store_summary(paper.arxiv_id, summary_result.content)
            
            # Mark paper as processed
            paper_metadata = {
                'title': paper.title,
                'authors': paper.authors,
                'categories': paper.categories,
                'submitted_date': paper.submitted_date.isoformat()
            }
            cache.mark_paper_processed(paper.arxiv_id, paper_metadata)
        else:
            print(f"  Failed to summarize {paper.title}: {summary_result.error}")
    
    print(f"\n=== Pipeline Complete ===")
    print(f"Successfully processed {len([r for r in summary_results if r.success])} papers")
    print(f"Summaries saved to: {output_dir.absolute()}")
    
    # Print cache stats
    stats = cache.get_cache_stats()
    print(f"Cache stats: {stats['summaries_count']} summaries, {stats['cache_size_mb']} MB total")


if __name__ == "__main__":
    main()