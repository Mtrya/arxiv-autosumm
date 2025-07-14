"""
Complete ArXiv-AutoSumm summarization workflow
"""

import logging
from datetime import date
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from pipeline import (
    Cacher, fetch, RendererConfig,
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

def fetch_new_papers(category, cacher: Cacher, fetch_config: dict, verbose: bool = False) -> List[PaperMetadata]:
    """Fetch new papers from ArXiv, check cache for duplicates."""
    logger = logging.getLogger(__name__)
    
    try:
        fetch_results = fetch(category, fetch_config)
        papers = [PaperMetadata(
            idx=idx,
            title=result.title,
            pdf_url=result.pdf_url,
            arxiv_id=result.arxiv_id,
        ) for idx,result in enumerate(fetch_results) if not cacher.is_paper_processed(result.arxiv_id)]

        for paper in papers:
            try:
                paper.embed_score = cacher.get_similarity_score(paper.arxiv_id) # if not cached, will return None
                score = cacher.get_rating_score(paper.arxiv_id)
                if score is not None:
                    paper.llm_score, _ = score
                if verbose:
                    logger.debug(f"Checked {paper.arxiv_id} for cached scores. Embed score: {paper.embed_score}, LLM score: {paper.llm_score}.")
            except Exception as e:
                logger.warning(f"Error checking cached scores for {paper.arxiv_id}: {e}")
                paper.embed_score = None
                paper.llm_score = None

        return papers
    except Exception as e:
        logger.error(f"Failed to fetch new papers: {e}")
        return []

def parse_papers(papers: List[PaperMetadata], parse_config, vlm: bool, batch_config=None, verbose: bool = False) -> List[PaperMetadata]:
    """Assign value for parsed_content field using parse_fast or parse_vlm"""
    logger = logging.getLogger(__name__)
    
    if not papers:
        return []
    
    successfully_parsed = []
    pdf_urls = [paper.pdf_url for paper in papers]
    
    try:
        if vlm:
            parse_results = parse_vlm(pdf_urls, parse_config, batch_config)
        else:
            parse_results = parse_fast(pdf_urls, parse_config)

        for paper, result in zip(papers, parse_results):
            try:
                if result.success:
                    paper.parsed_content = result.content
                    successfully_parsed.append(paper)
                    if verbose:
                        logger.debug(f"Successfully parsed content for {paper.arxiv_id}")
                else:
                    logger.warning(f"Parse failed for {paper.arxiv_id}: {result.error}")
            except Exception as e:
                logger.error(f"Error processing parse result for {paper.arxiv_id}: {e}")
        
        logger.info(f"Parsed {len(successfully_parsed)} out of {len(papers)} papers")
        return successfully_parsed
    except Exception as e:
        logger.error(f"Parse operation failed: {e}")
        return []

def select_papers_embed(papers: List[PaperMetadata], cacher: Cacher, rate_config, batch_config, verbose: bool = False) -> List[PaperMetadata]:
    """First selection with embedding model"""
    logger = logging.getLogger(__name__)
    
    papers_with_score = [p for p in papers if p.embed_score is not None]
    papers_to_rate = [p for p in papers if p.embed_score is None]

    logger.info(f"Found {len(papers_with_score)} papers with cached embed scores, {len(papers_to_rate)} to rate")
    
    if not papers_to_rate:
        logger.info("No papers need embedder rating, using cached scores")
        return papers_with_score
    
    try:
        contents = [p.parsed_content for p in papers_to_rate]
        rate_results = rate_embed(contents, rate_config, batch_config)
        
        for paper, result in zip(papers_to_rate, rate_results):
            try:
                if result.success:
                    paper.embed_score = result.score
                    papers_with_score.append(paper)
                    cacher.store_similarity_score(paper.arxiv_id, paper.embed_score)
                    if verbose:
                        logger.debug(f"rate_embed for {paper.arxiv_id} success: {result.score}")
                else:
                    logger.warning(f"rate_embed for {paper.arxiv_id} failed: {result.error}")
            except Exception as e:
                logger.error(f"Error processing embed rating result for {paper.arxiv_id}: {e}")

        if len(papers_with_score) < rate_config.top_k:
            logger.info(f"Returning {len(papers_with_score)} papers (fewer than top_k={rate_config.top_k})")
            return papers_with_score
        else:
            papers_with_score = sorted(papers_with_score, key=lambda p: p.embed_score, reverse=True)
            selected = papers_with_score[:rate_config.top_k]
            logger.info(f"Selected top {len(selected)} papers by embed score")
            return selected
    except Exception as e:
        logger.error(f"Embed rating operation failed: {e}")
        return papers_with_score
    
def select_papers_llm(papers: List[PaperMetadata], cacher: Cacher, rate_config, batch_config, verbose: bool = False) -> List[PaperMetadata]:
    """Second selection with llm"""
    logger = logging.getLogger(__name__)
    
    papers_with_score = [p for p in papers if p.llm_score is not None]
    papers_to_rate = [p for p in papers if p.llm_score is None]

    logger.info(f"Found {len(papers_with_score)} papers with cached LLM scores, {len(papers_to_rate)} to rate")
    
    if not papers_to_rate:
        papers_with_score = sorted(papers_with_score, key=lambda p: p.llm_score, reverse=True)
        selected = papers_with_score[:rate_config.max_selected]
        logger.info(f"Using cached LLM scores, selected {len(selected)} papers")
        return selected
    
    try:
        contents = [p.parsed_content for p in papers_to_rate]
        rate_results = rate_llm(contents, rate_config, batch_config)
        
        for paper, result in zip(papers_to_rate, rate_results):
            try:
                if result.success:
                    paper.llm_score = result.score
                    papers_with_score.append(paper)
                    cacher.store_rating_score(paper.arxiv_id, paper.llm_score, {})
                    if verbose:
                        logger.debug(f"rate_llm for {paper.arxiv_id} succeeded: {result.score}")
                else:
                    logger.warning(f"rate_llm for {paper.arxiv_id} failed: {result.error}")
            except Exception as e:
                logger.error(f"Error processing LLM rating result for {paper.arxiv_id}: {e}")
    
        if len(papers_with_score) <= rate_config.max_selected:
            logger.info(f"Returning {len(papers_with_score)} papers (within max_selected={rate_config.max_selected})")
            return papers_with_score
        else:
            papers_with_score = sorted(papers_with_score, key=lambda p: p.llm_score, reverse=True)
            selected = papers_with_score[:rate_config.max_selected]
            logger.info(f"Selected top {len(selected)} papers by LLM score")
            return selected
    except Exception as e:
        logger.error(f"LLM rating operation failed: {e}")
        return papers_with_score

def summarize_paper(papers: List[PaperMetadata], cacher: Cacher, summarize_config, render_config, batch_config, verbose: bool = False) -> List[PaperMetadata]:
    """Summarize papers using LLM"""
    logger = logging.getLogger(__name__)
    
    if not papers:
        logger.info("No papers to summarize")
        return []
    
    try:
        parsed_contents = [paper.parsed_content for paper in papers]
        summary_results = summarize(parsed_contents, summarize_config, batch_config)

        successful_summaries = 0
        for paper, result in zip(papers, summary_results):
            try:
                if result.success:
                    paper.summary = result.content
                    successful_summaries += 1
                    if verbose:
                        logger.debug(f"summarize for {paper.arxiv_id} succeeded: {len(result.content)} tokens")
                else:
                    logger.warning(f"summarize for {paper.arxiv_id} failed: {result.error}")
            except Exception as e:
                logger.error(f"Error processing summary result for {paper.arxiv_id}: {e}")

        logger.info(f"Successfully generated {successful_summaries} out of {len(papers)} summaries")

        renderable_papers = []
        failed_render_count = 0

        for paper in papers:
            if not paper.summary:
                logger.warning(f"Skipping {paper.arxiv_id} - no summary generated")
                continue
                
            test_render_config = RendererConfig(
                formats=render_config.formats,
                output_dir=render_config.output_dir,
                base_filename=f"test",
                md=render_config.md,
                pdf=render_config.pdf,
                html=render_config.html,
                azw3=render_config.azw3
            )
            
            try:
                render_results = render([paper.summary], "test", test_render_config)
                all_succeeded = all(result.success for result in render_results)
                
                for result in render_results:
                    if result.success and Path(result.path).exists():
                        Path(result.path).unlink(missing_ok=True)
                
                if all_succeeded:
                    renderable_papers.append(paper)
                    cacher.mark_paper_processed(paper.arxiv_id, {})
                    if verbose:
                        logger.debug(f"Successfully rendered test for {paper.arxiv_id}")
                else:
                    failed_render_count += 1
                    logger.warning(f"Test render failed for {paper.arxiv_id}")
                    
            except Exception as e:
                failed_render_count += 1
                logger.error(f"Summary for {paper.arxiv_id} failed to render: {e}")
        
        logger.info(f"Successfully rendered {len(renderable_papers)} papers, {failed_render_count} failed")
        return renderable_papers
    except Exception as e:
        logger.error(f"Summarize operation failed: {e}")
        return []




def setup_logging(verbose: bool = False):
    """Set up logging with appropriate verbosity level"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)

def run_pipeline(config_path, verbose: bool=False):
    """Main pipeline of ArXiv AutoSumm"""
    logger = setup_logging(verbose)
    
    try:
        # 0. Load and check configuration change
        logger.info("Loading configuration...")
        config = MainConfig.from_yaml(config_path).get_pipeline_configs()
        cacher = Cacher(config["cache"])
        cacher.detect_and_handle_config_changes(config["rate"])
        logger.info("Configuration loaded successfully")

        # 1. Determine category to fetch
        today = date.today()
        categories = config["categories"]
        category = categories[int(today.strftime('%j')) % len(categories)]
        logger.info(f"Processing category: {category} for date {today}")
        
        # 2&3. Fetch paper metadata and get cached ratings
        logger.info("Fetching new papers...")
        papers = fetch_new_papers(category, cacher, config["fetch"], verbose=verbose)
        logger.info(f"Found {len(papers)} new papers to process")
        
        if not papers:
            logger.info("No new papers found, exiting pipeline")
            return
        
        # 4. Parse papers (coarse)
        logger.info("Parsing papers (coarse)...")
        papers = parse_papers(papers, config["parse"], vlm=False, verbose=verbose)
        logger.info(f"Successfully parsed {len(papers)} papers")
        
        if not papers:
            logger.warning("No papers could be parsed, exiting pipeline")
            return

        # 5&6&7. Rate papers (with embedder) + cache embedder ratings + select top-k papers
        if config["rate"].top_k < 1000: # a large top_k means the user want to rely on llm selection, skip embedder rating
            logger.info("Rating papers with embedding model...")
            papers = select_papers_embed(papers, cacher, config["rate"], config["batch"], verbose=verbose)
            logger.info(f"Selected {len(papers)} papers after embedding rating")
        else:
            logger.info("Skipping embedder rating (top_k >= 1000)")

        # 8&9&10. Rate papers (with llm) + cache llm ratings + select max_selected papers to summarize
        if config["rate"].top_k > 1: # a very small top_k means the user want to rely on embedder selection, skip llm rating
            logger.info("Rating papers with LLM...")
            papers = select_papers_llm(papers, cacher, config["rate"], config["batch"], verbose=verbose)
            logger.info(f"Selected {len(papers)} papers after LLM rating")
        else: # if llm rating isn't used, still need to select max_selected papers instead of top_k papers
            logger.info("Skipping LLM rating (top_k <= 1)")
            papers = sorted(papers, key=lambda p: p.embed_score, reverse=True)
            papers = papers[:config["rate"].max_selected]
            logger.info(f"Selected top {len(papers)} papers by embed score")

        if not papers:
            logger.warning("No papers selected for summarization, exiting pipeline")
            return

        # 11. Parse papers (fine)
        if config["parse"].enable_vlm:
            logger.info("Parsing papers (fine with VLM)...")
            papers = parse_papers(papers, config["parse"], vlm=True, batch_config=config["batch"], verbose=verbose)
            logger.info(f"Successfully refined {len(papers)} papers")

        # 12&13. Summarize selected papers, track selected papers
        logger.info("Summarizing papers...")
        papers = summarize_paper(papers, cacher, config["summarize"], config["render"], config["batch"], verbose=verbose)
        logger.info(f"Successfully summarized {len(papers)} papers")

        if not papers:
            logger.warning("No papers could be summarized, exiting pipeline")
            return

        # 14. Render
        logger.info("Rendering summaries...")
        summaries = [p.summary for p in papers]
        render_result = render(summaries, category, config["render"])
        logger.info(f"Rendered summaries to {len(render_result)} formats")

        # 15. Deliver
        logger.info("Delivering results...")
        paths = [r.path for r in render_result]
        deliver(paths, config["deliver"], "arxiv_summary_test")
        logger.info("Pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=verbose)
        raise



if __name__ == "__main__":
    config_path = "my_own_config.yaml"
    run_pipeline(config_path)