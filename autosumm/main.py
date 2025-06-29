"""
Complete ArXiv-AutoSumm summarization workflow:
0. Load and check configuration
1. Determine category according to day of the year and MainConfig.RunConfig.categories
2. Fetch papers, get FetchResult with fetch(category: str, config: FetcherConfig) -> List[FetchResult]. FetchResult contains 'pdf_url' field
3. Get cached paper ratings (if any)
4. Parse papers coarsely, get ParseResult with parse_fast(pdf_urls: List[str], config: ParserConfig) -> List[ParseResult]. ParseResult contains 'content' field
5. Rate papers using embedder, get embedding similarity using rate_embed(parsed_contents: List[str], config: RaterConfig) -> List[RateResult]. RateResult contains 'score' field
6. Cache embedder ratings
7. Select papers with top_k similarity
8. Rate selected papers using llm, get score using rate_llm(parsed_contents: List[str], config: RateConfig, batch_config) -> List[RateResult].
9. Cache llm ratings
10. Get final max_results selected papers with highest score
11. We should know the pdf_urls of these selected papers, use parse_vlm(pdf_urls: List[str], config: ParserConfig, batch_config) -> List[ParseResult] to parse these papers again
12. Summarize these papers with summarize(parsed_contents: List[str], config: SummarizerConfig, batch_config) -> List[SummaryResult]. SummaryResult contain 'content' field
13. Render these summaries using render(summaries: List[str], category: str, config: RendererConfig) -> List[RenderResult]. RenderResult contain 'path' field
14. Track these rendered papers
15. Deliver these rendered files with deliver(file_paths: List[str], config: DelivererConfig, subject: Optional[str]=None) -> DeliveryResult
"""

import os
from datetime import datetime, timedelta, date
from pathlib import Path

from pipeline import (
    Cacher, CacherConfig
)

from config import MainConfig

def main():
    """Main pipeline of ArXiv AutoSumm"""
    # 0. Load and check configuration change
    config = MainConfig.from_yaml("config.yaml").get_pipeline_configs()
    cacher = Cacher(config["cache"])
    cacher.detect_and_handle_config_changes(config)

    # 1. Determine category to fetch
    today = date.today()
    categories = config["categories"]
    category = categories[int(today.strftime('%j')) % len(categories)]
    print(category)
    
    


if __name__ == "__main__":
    main()