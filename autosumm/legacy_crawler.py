import requests
import arxiv
from arxiv2text import arxiv_to_md
import os
import re
import time
import tiktoken


class Crawler:
    def __init__(self, category: str, start_date: str, end_date: str, max_results: int=None, max_retries: int=None):
        self.category = category
        self.max_results = max_results if max_results else 1000
        self.start_date = start_date
        self.end_date = end_date
        self.max_retries = max_retries if max_retries else 10

    def fetch_arxiv_papers(self):
        """
        Fetches a list of paper metadata from arXiv based on the specified category and maximum number of results.
        """
        client = arxiv.Client()
        search = arxiv.Search(
            query = f'cat:{self.category} AND submittedDate:[{self.start_date} TO {self.end_date}]',
            max_results = self.max_results,
            sort_by = arxiv.SortCriterion.SubmittedDate
        )

        papers = []
        results = client.results(search)
        #print(results)

        for attempt in range(self.max_retries):
            try:
                for result in results:
                    author_names = [author.name for author in result.authors]
                    papers.append({
                        'title': result.title,
                        'pdf_url': result.pdf_url,
                        "authors": author_names,
                        "entry_id": result.entry_id,
                        "arxiv_id": result.entry_id.split('/')[-1],
                        "category": result.primary_category,
                        "citation": result.journal_ref if result.journal_ref else result.entry_id
                    })
                break
            except arxiv.UnexpectedEmptyPageError as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(5)
        else:
            print("Max retries reached. Failed to fetch papers.")

        return papers
    
    def extract_content(self, pdf_url: str, markdown_folder: str="/home/kaupane/development/scripts/autosumm/temp", download: bool=False):
        try:
            arxiv_to_md(pdf_url, markdown_folder)
        except Exception as e:
            print(f"Error extracting content from {pdf_url}: {e}")
            return None
        generated_files = [f for f in os.listdir(markdown_folder) if f.endswith('.md')]
        if not generated_files:
            raise ValueError("No markdown files found.")
        
        generated_files.sort(key=lambda f: os.path.getmtime(os.path.join(markdown_folder,f)), reverse=True)
        latest_file_path = os.path.join(markdown_folder, generated_files[0])
        with open(latest_file_path, 'r') as file:
            content = file.read()
        
        # Remove inappropriate line breaks within paragraphs
        content = re.sub(r'(?<!\n)\n(?!\n)',' ',content)

        # Remove content after "References" or "REFERENCES"
        match = re.search(r'\nReferences\n|\nREFERENCES\n',content)
        if match:
            content = content[:match.start()]
        
        if download:
            with open(latest_file_path,'w', encoding='utf-8') as file:
                file.write(content)
        else:
            os.remove(latest_file_path)

        return content
    
    def download_pdf(self, pdf_url: str, pdf_folder: str):
        if not os.path.exists(pdf_folder):
            os.makedirs(pdf_folder)
        
        pdf_filename = os.path.basename(pdf_url)
        pdf_path = os.path.join(pdf_folder, pdf_filename)

        response = requests.get(pdf_url, stream=True)
        response.raise_for_status()

        with open(pdf_path, 'wb') as pdf_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    pdf_file.write(chunk)
        
    def count_token(self, text: str, model: str="cl100k_base") -> int:
        encoding = tiktoken.get_encoding(model)
        try:
            tokens = encoding.encode(text,disallowed_special=())
            return len(tokens)
        except Exception as e:
            return e
        


def main():
    category = "cs.AI"
    crawler = Crawler(category,"20240201","20240205",2)
    papers = crawler.fetch_arxiv_papers()
    for paper in papers:
        print(paper['entry_id'])


if __name__ == "__main__":
    main()
    