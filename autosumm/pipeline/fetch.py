"""
Fetch papers from arXiv based on specified category and time range.
Handles only paper fetching and pdf downloading.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import requests
import arxiv
import time

@dataclass
class PaperMetadata:
    title: str
    pdf_url: str
    authors: List[str]
    entry_id: str
    arxiv_id: str
    categories: List[str]
    citation: Optional[str]
    submitted_date: datetime

@dataclass
class FetchConfig:
    categories: List[str]
    start_date: str # format: YYYYMMDD
    end_date: str # format: YYYYMMDD
    max_results: int=1000
    max_retires: int=10
    output_dir: str="./downloads"

@dataclass
class DownloadResult:
    paper: PaperMetadata
    file_path: Optional[str]
    success: bool
    error: Optional[str]

def fetch_paper_metadata(config: FetchConfig) -> List[PaperMetadata]:
    """
    Fetch paper metadata from arXiv based on categories and date range.
    """
    client = arxiv.Client()

    category_queries = [f'cat:{cat}' for cat in config.categories]
    category_query = ' OR '.join(category_queries)
    date_query = f'submittedDate:[{config.start_date} TO {config.end_date}]'
    full_query = f'{category_query} AND {date_query}'

    search = arxiv.Search(
        query=full_query,
        max_results=config.max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    papers = []
    results = client.results(search)

    for attempt in range(config.max_retires):
        try:
            for result in results:
                papers.append(PaperMetadata(
                    title=result.title,
                    pdf_url=result.pdf_url,
                    authors=[author.name for author in result.authors],
                    entry_id=result.entry_id,
                    arxiv_id=result.entry_id.split('/')[-1],
                    categories=result.categories,
                    citation=result.journal_ref if result.journal_ref else result.entry_id,
                    submitted_date=result.published
                ))
            break
        except arxiv.UnexpectedEmptyPageError as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(5)
    else:
        print("Max retries reached. Failed to fetch papers.")
        raise RuntimeError("Failed to fetch papers after maximum retries.")
    
    return papers

def download_paper_pdfs(papers: List[PaperMetadata], config: FetchConfig) -> List[DownloadResult]:
    """
    Download PDF files for a list of papers aynchronously.
    """
    output_path = Path(config.output_dir)
    output_path.mkdir(parents=True,exist_ok=True)

    results = []

    for paper in papers:
        try:
            filename = f"{paper.arxiv_id}.pdf"
            file_path = output_path / filename

            response = requests.get(paper.pdf_url,stream=True)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            results.append(DownloadResult(
                paper=paper,
                file_path=str(file_path),
                success=True,
                error=""
            ))

        except Exception as e:
            results.append(DownloadResult(
                paper=paper,
                file_path=None,
                success=False,
                error=str(e)
            ))

    return results

def fetch_and_download(config: FetchConfig) -> List[DownloadResult]:
    """
    Wrapper function.
    """
    papers = fetch_paper_metadata(config)
    print(len(papers))
    results = download_paper_pdfs(papers,config)
    return results

if __name__ == "__main__":
    config = FetchConfig(
        categories=["cs.AI"],
        start_date="20250601",
        end_date="20250602",
        max_results=2
    )

    results = fetch_and_download(config)

    for result in results:
        if result.success:
            print(f"Downloaded: {result.paper.title} -> {result.file_path}")
        else:
            print(f"Failed: {result.paper.title} - {result.error}")
        print(result.paper.pdf_url)