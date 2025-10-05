"""
Fetch papers from arXiv based on specified category and time range.
Handles only paper fetching and pdf downloading.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging
import arxiv
import time
import fitz
import os
import requests
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class FetcherConfig:
    days: int=8
    max_results: int=1000
    max_retries: int=3
    download_timeout_seconds: int=224

@dataclass
class FetchResult:
    title: str
    pdf_url: str
    cache_path: Optional[str]
    authors: List[str]
    entry_id: str
    arxiv_id: str
    categories: List[str]
    citation: Optional[str]
    submitted_date: datetime

def fetch_metadata(category: str, config: FetcherConfig) -> List[FetchResult]:
    """
    Fetch paper metadata from arXiv based on categories and date range.
    """
    client = arxiv.Client()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=config.days)
    start_date_str = start_date.strftime("%Y%m%d") 
    end_date_str = end_date.strftime("%Y%m%d")

    date_query = f'submittedDate:[{start_date_str} TO {end_date_str}]'
    full_query = f'{category} AND {date_query}'

    logger.info(f"Fetching papers for category: {category}, days: {config.days}, max: {config.max_results}")
    search = arxiv.Search(
        query=full_query,
        max_results=config.max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    papers = []
    results = client.results(search)

    for attempt in range(config.max_retries):
        try:
            for result in results:
                papers.append(FetchResult(
                    title=result.title,
                    pdf_url=result.pdf_url,
                    cache_path=None,  # will be set later during download phase
                    authors=[author.name for author in result.authors],
                    entry_id=result.entry_id,
                    arxiv_id=result.entry_id.split('/')[-1],
                    categories=result.categories,
                    citation=result.journal_ref if result.journal_ref else result.entry_id,
                    submitted_date=result.published
                ))
            logger.info(f"Fetched {len(papers)} papers successfully")
            break
        except arxiv.UnexpectedEmptyPageError as e:
            logger.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(5)
    else:
        logger.error("Max retries reached. Failed to fetch papers.",exc_info=True)
        raise RuntimeError("Failed to fetch papers after maximum retries.")
    
    return papers

def _validate_pdf_file(pdf_path: str) -> bool:
    """Validate that downloaded file is a proper PDF"""
    try:
        with open(pdf_path, 'rb') as f:
            header = f.read(5)
            if not header.startswith(b'%PDF-'):
                return False

            # Try to read with PyMuPDF for basic validation
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            return page_count > 0
    except Exception as e:
        logger.debug(f"PDF validation failed for {pdf_path}: {e}")
        return False

def fetch_pdf(pdf_urls: List[str], cache_dir: str, config: FetcherConfig) -> List[Optional[str]]:
    """
    Download multiple PDFs with timeout and validation.
    Handles file existence checking, downloading, and validation internally.
    Returns list of downloaded paths matching input order.
    """
    os.makedirs(cache_dir, exist_ok=True)
    downloaded_paths = []

    logger.info(f"Processing {len(pdf_urls)} PDFs")

    for pdf_url in pdf_urls:
        # Use hash of URL as filename to avoid URL parsing issues
        url_hash = hashlib.md5(pdf_url.encode()).hexdigest()
        pdf_filename = f"{url_hash}.pdf"
        local_path = Path(cache_dir) / pdf_filename

        # Check if file already exists and is valid
        if local_path.exists() and _validate_pdf_file(str(local_path)):
            logger.debug(f"Cache hit, using existing valid PDF: {local_path}")
            downloaded_paths.append(str(local_path))
            continue

        logger.debug(f"Downloading PDF: {pdf_url}")

        # Download file with retries
        downloaded_successfully = False
        for attempt in range(config.max_retries):
            try:
                response = requests.get(pdf_url, timeout=config.download_timeout_seconds)
                response.raise_for_status()

                # Write to temporary file first
                temp_path = local_path.with_suffix('.tmp')
                with open(temp_path, 'wb') as f:
                    f.write(response.content)

                # Validate the downloaded file
                if _validate_pdf_file(str(temp_path)):
                    temp_path.rename(local_path)
                    logger.debug(f"Successfully downloaded PDF to {local_path}")
                    downloaded_paths.append(str(local_path))
                    downloaded_successfully = True
                else:
                    temp_path.unlink(missing_ok=True)
                    logger.warning(f"Downloaded file failed validation: {pdf_url}")

                break  # Success or validation failure - exit retry loop

            except requests.exceptions.RequestException as e:
                logger.warning(f"Download attempt {attempt+1} failed for {pdf_url}: {e}")
                if attempt < config.max_retries - 1:
                    time.sleep(5)

        # If all attempts failed, append None
        if not downloaded_successfully:
            logger.warning(f"Failed to download PDF {pdf_url} after {config.max_retries} attempts")
            downloaded_paths.append(None)

    successful_count = sum(1 for path in downloaded_paths if path is not None)
    logger.info(f"Successfully processed {successful_count} out of {len(pdf_urls)} PDFs")
    return downloaded_paths

if __name__ == "__main__":
    config = FetcherConfig(
        category="cs.AI",
        days=8,
        max_results=10,
        max_retries=2
    )

    results = fetch_metadata(config.category, config)

    for result in results:
        logger.info(result)