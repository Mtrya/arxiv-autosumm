"""
Complete ArXiv-AutoSumm summarization workflow
"""

import os
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from pipeline import (
    Cacher, fetch,
    parse_fast, parse_vlm,
    rate_embed, rate_llm,
    summarize, render, deliver
)

from config import MainConfig

@dataclass
class PaperMetadata:
    idx: int
    title: str
    pdf_url: str
    arxiv_id: str
    embed_score: Optional[float]=None
    llm_score: Optional[float]=None
    parsed_content: Optional[str]=None
    summary: Optional[str]=None

def fetch_new_papers(category, cacher: Cacher, fetch_config: dict) -> List[PaperMetadata]:
    """Fetch new papers from ArXiv, check cache for duplicates."""
    fetch_results = fetch(category, fetch_config)
    papers = [PaperMetadata(
        idx=idx,
        title=result.title,
        pdf_url=result.pdf_url,
        arxiv_id=result.arxiv_id,
    ) for idx,result in enumerate(fetch_results) if not cacher.is_paper_processed(result.arxiv_id)]

    for paper in papers:
        paper.embed_score = cacher.get_similarity_score(paper.arxiv_id) # if not cached, will return None
        score = cacher.get_rating_score(paper.arxiv_id)
        if score is not None:
            paper.llm_score, detail = score
        print(f"Checked {paper.arxiv_id} for cached scores. Embed score: {paper.embed_score}, LLM score: {paper.llm_score}.")

    return papers

def parse_papers(papers: List[PaperMetadata], parse_config, vlm: bool, batch_config=None) -> List[PaperMetadata]:
    """Assign value for parsed_content field using parse_fast or parse_vlm"""
    if not papers:
        return []
    successfully_parsed = []
    pdf_urls = [paper.pdf_url for paper in papers]
    if vlm:
        parse_results = parse_vlm(pdf_urls, parse_config, batch_config)
    else:
        parse_results = parse_fast(pdf_urls, parse_config)

    for paper, result in zip(papers, parse_results):
        if result.success:
            paper.parsed_content = result.content
            successfully_parsed.append(paper)
            print(f"Successfully parsed content for {paper.arxiv_id}")
        else:
            print(f"parse_fast for {paper.arxiv_id} failed: {result.error}")
    
    print(f"Parsed {len(successfully_parsed)} papers.")
    return successfully_parsed

def select_papers_embed(papers: List[PaperMetadata], cacher: Cacher, rate_config, batch_config) -> List[PaperMetadata]:
    """First selection with embedding model"""
    papers_with_score = [p for p in papers if p.embed_score is not None]
    papers_to_rate = [p for p in papers if p.embed_score is None]

    if not papers_to_rate:
        return papers_with_score
    
    contents = [p.parsed_content for p in papers_to_rate]
    rate_results = rate_embed(contents, rate_config, batch_config)
    for paper, result in zip(papers_to_rate, rate_results):
        if result.success:
            paper.embed_score = result.score
            papers_with_score.append(paper)
            cacher.store_similarity_score(paper.arxiv_id, paper.embed_score)
            print(f"rate_embed for {paper.arxiv_id} success: {result.score}")
        else:
            print(f"rate_embed for {paper.arxiv_id} failed: {result.error}")

    if len(papers_with_score) < rate_config.top_k:
        return papers_with_score
    else:
        papers_with_score = sorted(papers_with_score, key=lambda p: p.embed_score, reverse=True)
        return papers_with_score[:rate_config.top_k]
    
def select_papers_llm(papers: List[PaperMetadata], cacher: Cacher, rate_config, batch_config) -> List[PaperMetadata]:
    """Second selection with llm"""
    papers_with_score = [p for p in papers if p.llm_score is not None]
    papers_to_rate = [p for p in papers if p.llm_score is None]

    if not papers_to_rate:
        papers_with_score = sorted(papers_with_score, key=lambda p: p.llm_score, reverse=True)
        return papers_with_score[:rate_config.max_selected]
    
    contents = [p.parsed_content for p in papers_to_rate]
    rate_results = rate_llm(contents, rate_config, batch_config)
    for paper, result in zip(papers_to_rate, rate_results):
        if result.success:
            paper.llm_score = result.score
            papers_with_score.append(paper)
            cacher.store_rating_score(paper.arxiv_id, paper.llm_score, {})
            print(f"rate_llm for {paper.arxiv_id} succeeded: {result.score}")
        else:
            print(f"rate_llm for {paper.arxiv_id} failed: {result.error}")
    
    if len(papers_with_score) <= rate_config.max_selected:
        return papers_with_score
    else:
        papers_with_score = sorted(papers_with_score, key=lambda p: p.llm_score, reverse=True)
        return papers_with_score[:rate_config.max_selected]

def summarize_paper(papers: List[PaperMetadata], cacher: Cacher, summarize_config, render_config, batch_config) -> List[PaperMetadata]:
    """Summarize papers using LLM"""
    if not papers:
        return []
    
    parsed_contents = [paper.parsed_content for paper in papers]
    summary_results = summarize(parsed_contents, summarize_config, batch_config)

    for paper, result in zip(papers, summary_results):
        if result.success:
            paper.summary = result.content
            print(f"summarize for {paper.arxiv_id} succeeded: {len(result.content)} tokens")
        else:
            print(f"summarize for {paper.arxiv_id} failed: {result.error}")

    renderable_papers = []

    for paper in papers:
        test_render_config = render_config.copy()
        test_render_config.base_filename = f"test"
        
        render_results = render([paper.summary], "test", test_render_config)
        all_succeeded = all(result.success for result in render_results)

        for result in render_results:
            if result.success and Path(result.path).exists():
                Path(result.path).unlink(missing_ok=True)
        if all_succeeded:
            renderable_papers.append(paper)
            cacher.mark_paper_processed(paper.arxiv_id,{})
        
    return renderable_papers


   

def run_pipeline(config_path):
    """Main pipeline of ArXiv AutoSumm"""
    # 0. Load and check configuration change
    config = MainConfig.from_yaml(config_path).get_pipeline_configs()
    cacher = Cacher(config["cache"])
    cacher.detect_and_handle_config_changes(config["rate"])

    # 1. Determine category to fetch
    today = date.today()
    categories = config["categories"]
    category = categories[int(today.strftime('%j')) % len(categories)]
    
    # 2&3. Fetch paper metadata and get cached ratings
    papers = fetch_new_papers(category, cacher, config["fetch"])
    
    # 4. Parse papers (coarse)
    papers = parse_papers(papers, config["parse"], vlm=False)

    # 5&6&7. Rate papers (with embedder) + cache embedder ratings + select top-k papers
    if config["rate"].top_k < 1000: # a large top_k means the user want to rely on llm selection, skip embedder rating
        papers = select_papers_embed(papers, cacher, config["rate"], config["batch"])

    # 8&9&10. Rate papers (with llm) + cache llm ratings + select max_selected papers to summarize
    if config["rate"].top_k > 1: # a very small top_k means the user want to rely on embedder selection, skip llm rating
        papers = select_papers_llm(papers, cacher, config["rate"], config["batch"])
    else: # if llm rating isn't used, still need to select max_selected papers instead of top_k papers
        papers = sorted(papers, key=lambda p: p.embed_score, reverse=True)
        papers = papers[:config["rate"].max_selected]

    # 11. Parse papers (fine)
    if config["parse"].enable_vlm:
        papers = parse_papers(papers, config["parse"], vlm=True, batch_config=config["batch"])

    # 12&13. Summarize selected papers, track selected papers
    papers = summarize_paper(papers, cacher, config["summarize"], config["batch"])

    # 14. Render
    summaries = [p.summary for p in papers]
    render_result = render(summaries,category, config["render"])

    # 15. Deliver
    paths = [r.path for r in render_result]
    deliver(paths, config["deliver"], "arxiv_summary_test")



if __name__ == "__main__":
    config_path = "my_own_config.yaml"
    run_pipeline(config_path)