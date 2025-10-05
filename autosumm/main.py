"""
Complete ArXiv-AutoSumm summarization workflow
"""

import os
import logging
import shutil
from datetime import date, datetime
from typing import Optional, List
from dataclasses import dataclass

from .pipeline import (
    Cacher, fetch_metadata, fetch_pdf,
    parse_fast, parse_vlm,
    rate_embed, rate_llm,
    summarize, render, deliver
)

from .config import MainConfig, arxiv_categories

@dataclass
class PaperMetadata:
    idx: int
    title: str
    pdf_url: str
    arxiv_id: str
    cache_path: Optional[str]=None
    embed_score: Optional[float]=None
    llm_score: Optional[float]=None
    parsed_content: Optional[str]=None
    summary: Optional[str]=None

def fetch_new_papers(category, cacher: Cacher, fetch_config: dict, verbose: bool = False) -> List[PaperMetadata]:
    """
    Fetch new papers from ArXiv with simplified PDF caching workflow.

    Workflow: fetch-metadata -> download-all-pdfs -> filter-valid-papers -> load-cached-scores
    """
    logger = logging.getLogger(__name__)

    try:
        # Step 1: Fetch metadata from ArXiv and filter out already summarized papers
        fetch_results = fetch_metadata(category, fetch_config)
        new_results = [result for result in fetch_results if not cacher.is_paper_processed(result.arxiv_id)]
        logger.info(f"Fetched {len(fetch_results)} papers from ArXiv, found {len(new_results)} new papers to process")

        if not new_results:
            return []

        # Step 2: Create PaperMetadata objects and collect all PDF URLs
        papers = []
        pdf_urls = []
        for idx, result in enumerate(new_results):
            paper = PaperMetadata(
                idx=idx,
                title=result.title,
                pdf_url=result.pdf_url,
                arxiv_id=result.arxiv_id,
            )
            papers.append(paper)
            pdf_urls.append(result.pdf_url)

        # Step 3: Download all PDFs (fetch_pdf handles existence checking internally)
        downloaded_paths = fetch_pdf(pdf_urls, str(cacher.pdf_cache_dir), fetch_config)

        # Step 4: Assign cache paths and filter out papers without valid PDFs
        valid_papers = []
        for paper, pdf_path in zip(papers, downloaded_paths):
            if pdf_path and os.path.exists(pdf_path):
                paper.cache_path = pdf_path
                valid_papers.append(paper)
                if verbose:
                    logger.debug(f"Valid PDF for {paper.arxiv_id}: {pdf_path}")
            else:
                logger.warning(f"No valid PDF for {paper.arxiv_id}")

        logger.info(f"Returning {len(valid_papers)} papers with valid PDFs out of {len(papers)} total")

        # Step 5: Clean up PDF cache if needed
        used_pdf_urls = [paper.pdf_url for paper in valid_papers]
        cacher.cleanup_pdf_cache(used_pdf_urls)

        # Step 6: Load cached scores for valid papers
        for paper in valid_papers:
            try:
                paper.embed_score = cacher.get_similarity_score(paper.arxiv_id)
                score = cacher.get_rating_score(paper.arxiv_id)
                if score is not None:
                    paper.llm_score, _ = score
                if verbose:
                    logger.debug(f"Checked {paper.arxiv_id} for cached scores. Embed score: {paper.embed_score}, LLM score: {paper.llm_score}.")
            except Exception as e:
                logger.warning(f"Error checking cached scores for {paper.arxiv_id}: {e}")
                paper.embed_score = None
                paper.llm_score = None

        return valid_papers
    except Exception as e:
        logger.error(f"Failed to fetch new papers: {e}", exc_info=True)
        return []

def parse_papers(papers: List[PaperMetadata], parse_config, vlm: bool, batch_config=None, verbose: bool = False) -> List[PaperMetadata]:
    """Assign value for parsed_content field using parse_fast or parse_vlm"""
    logger = logging.getLogger(__name__)
    
    if not papers:
        return []
    
    successfully_parsed = []
    cache_paths = [paper.cache_path for paper in papers]
    
    try:
        if vlm:
            parse_results = parse_vlm(cache_paths, parse_config, batch_config)
        else:
            parse_results = parse_fast(cache_paths)

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
        logger.error(f"Parse operation failed: {e}", exc_info=True)
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
                    try:
                        cacher.store_similarity_score(paper.arxiv_id, paper.embed_score)
                    except Exception as e:
                        logger.warning(f"Failed to cache similarity score for {paper.arxiv_id}: {e}", exc_info=True)
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
        logger.error(f"Embed rating operation failed: {e}", exc_info=True)
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
                    try:
                        cacher.store_rating_score(paper.arxiv_id, paper.llm_score, {})
                    except Exception as e:
                        logger.warning(f"Failed to cache llm rating score for {paper.arxiv_id}: {e}", exc_info=True)
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
        for paper in papers:
            if not paper.summary:
                logger.warning(f"Skipping {paper.arxiv_id} - no summary generated")
                continue
            
            renderable_papers.append(paper)
            try:
                cacher.mark_paper_processed(paper.arxiv_id, {})
            except Exception as e:
                logger.warning(f"Failed to mark {paper.arxiv_id} as processed: {e}", exc_info=True)
            if verbose:
                logger.debug(f"Successfully prepared summary for {paper.arxiv_id}")
        
        logger.info(f"Successfully prepared {len(renderable_papers)} papers for rendering")
        return renderable_papers
    except Exception as e:
        logger.error(f"Summarize operation failed: {e}")
        return []

def setup_logging(log_dir: str, send_log: bool, verbose: bool = False):
    """Set up logging with appropriate verbosity level"""
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler()]
    log_file_path = None

    if send_log:
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, f"run-{date.today().isoformat()}-{datetime.now().strftime('%H')}.txt")
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True
    )

    # Suppress INFO/WARNING logs from noisy libraries
    logging.getLogger('arxiv').setLevel(logging.ERROR)
    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    
    return logging.getLogger(__name__), log_file_path



def run_pipeline(config_path, verbose: bool=False, specified_category: Optional[str]=None):
    """Main pipeline of ArXiv AutoSumm"""
    log_file_path = None
    config = {}
    
    try:
        # 0. Load and check configuration change
        config = MainConfig.from_yaml(config_path).get_pipeline_configs()
        logger, log_file_path = setup_logging(
            log_dir=config.get("log_dir","./logs"),
            send_log=config.get("send_log",False),
            verbose=verbose
        )
        logger.info("Configuration loaded successfully")
        cacher = Cacher(config["cache"])
        try:
            cacher.detect_and_handle_config_changes(config["rate"])
            logger.info("Cache handled successfully")
        except Exception as e:
            logger.warning(f"Cache operation failed: {e}")

        # 1. Determine category to fetch
        today = date.today()
        if (specified_category is not None) and (specified_category != "None"):
            # Validate single category requirement
            if ',' in specified_category:
                logger.error(f"Multiple categories specified: {specified_category}. Only one category allowed.")
                raise ValueError("Only one category can be specified at a time.")

            if specified_category in arxiv_categories:
                category = specified_category
            else:
                logger.warning(f"Specified category '{specified_category}' invalid, fallback to default date-based category")
                categories = config["categories"]
                category = categories[int(today.strftime('%j')) % len(categories)]
        else:
            categories = config["categories"]
            category = categories[int(today.strftime('%j')) % len(categories)]
        logger.info(f"Processing category: {category} for date {today}")

        # 2&3. Fetch paper metadata and get cached ratings
        logger.info("Fetching new papers...")
        papers = fetch_new_papers(category, cacher, config["fetch"], verbose=verbose)
        logger.info(f"Found {len(papers)} new papers to process")
        
        if not papers:
            logger.info("No new papers found, exiting pipeline")
            if log_file_path:
                deliver([log_file_path], config[deliver])
            return
        
        # 4. Parse papers (coarse)
        logger.info("Parsing papers (coarse parsing with pdfminer)...")
        papers = parse_papers(papers, config["parse"], vlm=False, verbose=verbose)
        logger.info(f"Successfully parsed {len(papers)} papers")
        
        if not papers:
            logger.warning("No papers could be parsed, exiting pipeline")
            if log_file_path:
                deliver([log_file_path], config[deliver])
            return

        # 5&6&7. Rate papers (with embedder) + cache embedder ratings + select top-k papers
        if config["rate"].strategy in ["embedder","hybrid"]:
            logger.info("Rating papers with embedding model...")
            papers = select_papers_embed(papers, cacher, config["rate"], config["batch"], verbose=verbose)
            logger.info(f"Selected {len(papers)} papers after embedding rating")
        else:
            strategy = config["rate"].strategy
            logger.info(f"Skipping embedder rating (using strategy `{strategy}`)")

        # 8&9&10. Rate papers (with llm) + cache llm ratings + select max_selected papers to summarize
        if config["rate"].strategy in ["llm","hybrid"]:
            logger.info("Rating papers with LLM...")
            papers = select_papers_llm(papers, cacher, config["rate"], config["batch"], verbose=verbose)
            logger.info(f"Selected {len(papers)} papers after LLM rating")
        else: # need to select max_selected papers instead of top_k papers anyway
            logger.info("Skipping LLM rating (top_k <= 1)")
            papers = sorted(papers, key=lambda p: p.embed_score, reverse=True)
            papers = papers[:config["rate"].max_selected]
            logger.info(f"Selected top {len(papers)} papers by embed score")

        if not papers:
            logger.warning("No papers selected for summarization, exiting pipeline")
            if log_file_path:
                deliver([log_file_path], config[deliver])
            return

        # 11. Parse papers (fine)
        if config["parse"].enable_vlm:
            logger.info("Parsing papers (fine parsing with VLM)...")
            papers = parse_papers(papers, config["parse"], vlm=True, batch_config=config["batch"], verbose=verbose)
            logger.info(f"Successfully refined {len(papers)} papers")

        # 12&13. Summarize selected papers, track selected papers
        logger.info("Summarizing papers...")
        papers = summarize_paper(papers, cacher, config["summarize"], config["render"], config["batch"], verbose=verbose)
        logger.info(f"Successfully summarized {len(papers)} papers")

        if not papers:
            logger.warning("No papers could be summarized, exiting pipeline")
            if log_file_path:
                deliver([log_file_path], config[deliver])
            return

        # 14. Render
        logger.info("Rendering summaries...")
        summaries = [p.summary for p in papers]
        render_result = render(summaries, category, config["render"])
        logger.info(f"Rendered summaries to {len(render_result)} formats")

        # 15. Deliver
        paths = [r.path for r in render_result]
        if log_file_path:
            paths.append(log_file_path)
        logger.info("Pipeline completed successfully")
        # Explicitly flush all logging handlers
        for handler in logging.getLogger().handlers:
            handler.flush()
        logger.info("Delivering results...")
        summarizer_model = config["summarize"].model
        deliver(paths, config["deliver"], f"ArXiv Summary for {category}", summarizer_model)
        logger.info("Deliver completed")

        # Explicitly flush all logging handlers
        for handler in logging.getLogger().handlers:
            handler.flush()
        
    except Exception as e:
        if 'logger' in locals():
            logger.error(f"Pipeline failed with error: {e}", exc_info=True) # always log exc_info when something went wrong
            if log_file_path and config.get("send_log"):
                try:
                    logger.info(f"Attempting to deliver error log: {log_file_path}")
                    for handler in logging.getLogger().handlers:
                        handler.flush()
                    deliver([log_file_path],config["deliver"],"[ERROR] in ArXiv Summary Pipeline")
                except Exception as deliver_e:
                    logger.error(f"Failed to deliver error log: {deliver_e}", exc_info=verbose)
            raise
        else:
            raise
    finally:
        # Clean up tmp directory
        tmp_dir = config["parse"].tmp_dir
        if os.path.exists(tmp_dir) and os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except Exception as cleanup_e:
                logger.warning(f"Failed to cleanup temp directory {tmp_dir}: {cleanup_e}", exc_info=True)
        logging.shutdown()



if __name__ == "__main__":
    config_path = "config.yaml"
    run_pipeline(config_path)