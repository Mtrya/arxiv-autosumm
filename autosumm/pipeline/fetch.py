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

logger = logging.getLogger(__name__)

@dataclass
class FetcherConfig:
    days: int=8
    max_results: int=1000
    max_retries: int=10

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

def fetch(category: str, config: FetcherConfig) -> List[FetchResult]:
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
                    submitted_date=result.published
                ))
            logger.info(f"Fetched {len(papers)} papers successfully")
            break
        except arxiv.UnexpectedEmptyPageError as e:
            logger.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(5)
    else:
        logger.error("Max retries reached. Failed to fetch papers.")
        raise RuntimeError("Failed to fetch papers after maximum retries.")
    
    return papers


if __name__ == "__main__":
    config = FetcherConfig(
        category="cs.AI",
        days=8,
        max_results=10,
        max_retries=10
    )

    results = fetch(config)

    for result in results:
        print(result)