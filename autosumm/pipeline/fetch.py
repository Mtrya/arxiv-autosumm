"""
Fetch papers from arXiv based on specified category and time range.
Handles only paper fetching, pdf downloading and text extraction.
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
import re
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams

logger = logging.getLogger(__name__)

@dataclass
class FetcherConfig:
    days: int=8
    max_results: int=1000
    max_retries: int=3
    operation_timeout_seconds: int=224

@dataclass
class FetchResult:
    title: str
    pdf_url: str
    authors: List[str]
    entry_id: str
    arxiv_id: str
    categories: List[str]
    citation: Optional[str]
    submitted_date: datetime
    cache_path: Optional[str]
    extracted_text: Optional[str]
    extraction_success: bool = False
    extraction_error: Optional[str] = None

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
                    authors=[author.name for author in result.authors],
                    entry_id=result.entry_id,
                    arxiv_id=result.entry_id.split('/')[-1],
                    categories=result.categories,
                    citation=result.journal_ref if result.journal_ref else result.entry_id,
                    submitted_date=result.published,
                    cache_path=None,  # will be set later during download phase
                    extracted_text=None
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
        logger.warning(f"PDF validation failed for {pdf_path}: {e}")
        return False

def _get_cache_path(pdf_url: str, cache_dir: str) -> Path:
    """Generate cache file path from PDF URL."""
    url_hash = hashlib.md5(pdf_url.encode()).hexdigest()
    return Path(cache_dir) / f"{url_hash}.pdf"

def _extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes in-memory."""
    with io.BytesIO(pdf_bytes) as pdf_stream:
        content = extract_text(pdf_stream, laparams=LAParams())

    # Remove inappropriate line breaks within paragraphs to form coherent sentences
    content = re.sub(r'(?<!\n)\n(?!\n)', ' ', content)
    return content.strip()

def _extract_from_cached_file(cache_path: Path, pdf_url: str, index: int) -> FetchResult:
    """Extract text from already cached PDF file."""
    try:
        logger.info(f"Cache hit for PDF {index+1}: {cache_path}")

        # Read and extract text from cached file
        with open(cache_path, 'rb') as pdf_file:
            pdf_bytes = pdf_file.read()

        content = _extract_text_from_bytes(pdf_bytes)

        logger.debug(f"Successfully extracted text from cached PDF {index+1} ({pdf_url})")

        return FetchResult(
            title="", pdf_url=pdf_url, authors=[], entry_id="", arxiv_id="",
            categories=[], citation=None, submitted_date=datetime.now(),
            cache_path=str(cache_path),
            extracted_text=content,
            extraction_success=True,
            extraction_error=None
        )

    except Exception as extraction_error:
        logger.error(f"Error extracting text from cached PDF {index+1} ({cache_path}): {extraction_error}")
        return FetchResult(
            title="", pdf_url=pdf_url, authors=[], entry_id="", arxiv_id="",
            categories=[], citation=None, submitted_date=datetime.now(),
            cache_path=str(cache_path) if cache_path.exists() else None,
            extracted_text=None,
            extraction_success=False,
            extraction_error=f"Text extraction failed: {extraction_error}"
        )

def _download_extract_and_cache(pdf_url: str, cache_path: Path, config: FetcherConfig, index: int) -> FetchResult:
    """Download PDF, extract text in-memory, then save to cache."""
    logger.debug(f"Downloading PDF {index+1}: {pdf_url}")

    downloaded_successfully = False
    pdf_bytes = None

    # Download PDF with retries
    for attempt in range(config.max_retries):
        try:
            response = requests.get(pdf_url, timeout=config.operation_timeout_seconds)
            response.raise_for_status()

            pdf_bytes = response.content
            downloaded_successfully = True
            break

        except requests.exceptions.RequestException as e:
            logger.warning(f"Download attempt {attempt+1} failed for {pdf_url}: {e}")
            if attempt < config.max_retries - 1:
                time.sleep(5)

    if not downloaded_successfully:
        logger.warning(f"Failed to download PDF {pdf_url} after {config.max_retries} attempts")
        return FetchResult(
            title="", pdf_url=pdf_url, authors=[], entry_id="", arxiv_id="",
            categories=[], citation=None, submitted_date=datetime.now(),
            cache_path=None, extracted_text=None, extraction_success=False,
            extraction_error=f"Failed to download after {config.max_retries} attempts"
        )

    # Extract text from downloaded bytes (optimal: no disk I/O yet)
    try:
        content = _extract_text_from_bytes(pdf_bytes)
        logger.debug(f"Successfully extracted text from downloaded PDF {index+1} ({pdf_url})")

        # Validate and save to cache after successful text extraction
        if pdf_bytes.startswith(b'%PDF-'):
            # Write to temporary file first, then rename
            temp_path = cache_path.with_suffix('.tmp')
            temp_path.write_bytes(pdf_bytes)

            # Additional validation with PyMuPDF
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                if len(doc) > 0:
                    doc.close()
                    temp_path.rename(cache_path)
                    logger.info(f"Successfully saved PDF {index+1} to cache: {cache_path}")
                else:
                    temp_path.unlink(missing_ok=True)
                    logger.warning(f"Downloaded PDF has no pages: {pdf_url}")
                    return FetchResult(
                        title="", pdf_url=pdf_url, authors=[], entry_id="", arxiv_id="",
                        categories=[], citation=None, submitted_date=datetime.now(),
                        cache_path=None, extracted_text=content, extraction_success=True,
                        extraction_error="PDF saved to memory only (validation failed)"
                    )
            except Exception as validation_error:
                temp_path.unlink(missing_ok=True)
                logger.warning(f"PDF validation failed, keeping memory-only result: {pdf_url} - {validation_error}")
                return FetchResult(
                    title="", pdf_url=pdf_url, authors=[], entry_id="", arxiv_id="",
                    categories=[], citation=None, submitted_date=datetime.now(),
                    cache_path=None, extracted_text=content, extraction_success=True,
                    extraction_error="PDF saved to memory only (validation failed)"
                )
        else:
            logger.warning(f"Downloaded file is not a valid PDF: {pdf_url}")
            return FetchResult(
                title="", pdf_url=pdf_url, authors=[], entry_id="", arxiv_id="",
                categories=[], citation=None, submitted_date=datetime.now(),
                cache_path=None, extracted_text=content, extraction_success=True,
                extraction_error="PDF saved to memory only (invalid PDF format)"
            )

        return FetchResult(
            title="", pdf_url=pdf_url, authors=[], entry_id="", arxiv_id="",
            categories=[], citation=None, submitted_date=datetime.now(),
            cache_path=str(cache_path),
            extracted_text=content,
            extraction_success=True,
            extraction_error=None
        )

    except Exception as extraction_error:
        logger.error(f"Error extracting text from downloaded PDF {index+1} ({pdf_url}): {extraction_error}")

        # Still try to save the raw PDF to cache for potential manual inspection
        try:
            temp_path = cache_path.with_suffix('.tmp')
            temp_path.write_bytes(pdf_bytes)
            temp_path.rename(cache_path)
            logger.debug(f"Saved problematic PDF to cache despite extraction failure: {cache_path}")
        except Exception as save_error:
            logger.error(f"Failed to save problematic PDF: {save_error}")

        return FetchResult(
            title="", pdf_url=pdf_url, authors=[], entry_id="", arxiv_id="",
            categories=[], citation=None, submitted_date=datetime.now(),
            cache_path=str(cache_path) if cache_path.exists() else None,
            extracted_text=None,
            extraction_success=False,
            extraction_error=f"Text extraction failed: {extraction_error}"
        )

def _download_and_extract_single(pdf_url: str, cache_dir: str, config: FetcherConfig, index: int) -> FetchResult:
    """
    Download a single PDF and extract text with optimized data flow.
    - Cache hit: Read from disk and parse
    - Cache miss: Download → Parse in-memory → Save to disk
    """
    try:
        logger.debug(f"Processing PDF {index+1} ({pdf_url}) in worker {os.getpid()}")

        cache_path = _get_cache_path(pdf_url, cache_dir)

        # Check if file already exists and is valid (cache hit)
        """
        Performace optimization: Download and extract text in parallel
        - Cache hit: Read from disk (O(1) disk access)
        - Cache miss: Download -> Extract in-memory -> Save to disk
        Eliminates redundant disk I/O for cache misses.
        """
        if cache_path.exists() and _validate_pdf_file(str(cache_path)):
            return _extract_from_cached_file(cache_path, pdf_url, index)
        else:
            # Cache miss: download, extract in-memory, then save to cache
            return _download_extract_and_cache(pdf_url, cache_path, config, index)

    except Exception as e:
        logger.error(f"Unexpected error processing PDF {index+1} ({pdf_url}): {e}")
        return FetchResult(
            title="", pdf_url=pdf_url, authors=[], entry_id="", arxiv_id="",
            categories=[], citation=None, submitted_date=datetime.now(),
            cache_path=None, extracted_text=None, extraction_success=False,
            extraction_error=f"Unexpected error: {e}"
        )

def fetch_pdf(pdf_urls: List[str], cache_dir: str, config: FetcherConfig) -> List[FetchResult]:
    """
    Download PDFs and extract text in parallel.
    Results are returned in the same order as the input pdf_urls.
    """
    logger.debug(f"Starting download & text extraction for {len(pdf_urls)} PDFs using multithreading")

    os.makedirs(cache_dir, exist_ok=True)
    results = [None] * len(pdf_urls)

    # Use up to 4 workers for good parallelism without overwhelming the system
    max_workers = min(4, len(pdf_urls))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all download+text extraction jobs
        future_to_index = {
            executor.submit(_download_and_extract_single, url, cache_dir, config, i): i
            for i, url in enumerate(pdf_urls)
        }

        # Collect results as they complete and place them in the correct spot
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            pdf_url = pdf_urls[index]
            try:
                result = future.result(timeout=config.operation_timeout_seconds)  # download + text extraction time
                results[index] = result
            except TimeoutError:
                logger.warning(f"Download timed out for PDF: {pdf_url}")
                results[index] = FetchResult(
                    title="", pdf_url=pdf_url, authors=[], entry_id="", arxiv_id="",
                    categories=[], citation=None, submitted_date=datetime.now(),
                    cache_path=None, extracted_text=None, extraction_success=False,
                    extraction_error=f"Download timed out"
                )
            except Exception as e:
                logger.error(f"An unexpected error occurred while processing PDF {pdf_url}: {e}")
                results[index] = FetchResult(
                    title="", pdf_url=pdf_url, authors=[], entry_id="", arxiv_id="",
                    categories=[], citation=None, submitted_date=datetime.now(),
                    cache_path=None, extracted_text=None, extraction_success=False,
                    extraction_error=f"Unexpected error: {e}"
                )

    successful_count = sum(1 for r in results if r and r.extraction_success)
    failed_count = len(results) - successful_count
    logger.info(f"Fetch+text extraction completed: {successful_count} successful, {failed_count} failed")

    return results

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