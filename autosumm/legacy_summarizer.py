import subprocess
from openai import OpenAI
from config import *
from prompts import *
import re
from pathlib import Path
from datetime import datetime, timedelta
import time
from crawler import Crawler
import json
import random
from typing import List
import os

class Summarizer:
    def __init__(self, client_summ, client_rate, model_summ: str, model_rate: str, 
                 api_type_summ: str, api_type_rate: str, max_results: int, workload: bool):
        self.max_results = max_results
        self.workload = workload
        # Datetime
        now = datetime.now()
        iso_calender = now.isocalendar()
        current_year = iso_calender.year
        current_week_number = iso_calender.week
        self.category = CATEGORIES[now.weekday()]
        self.path = (
            f"{ARXIV_PATH}/{current_year}/"
            f"{self.category.replace('.', '')}/"
            f"summary_{self.category.replace('.', '')}_"
            f"{current_year-2000:02d}{current_week_number:02d}"
        )
        print(f"Summarization task of year {current_year}, week {current_week_number}, category {self.category} now begins, workload={workload}.")

        # Calculate start_date and end_date for crawler
        last_sunday = now - timedelta(days=now.weekday() + 10)
        last_saturday = last_sunday + timedelta(days=6)
        start_date = last_sunday.strftime('%Y%m%d')
        end_date = last_saturday.strftime('%Y%m%d')

        self.crawler = Crawler(self.category,start_date,end_date)
        self.client_summ = client_summ
        self.client_rate = client_rate
        self.model_summ = model_summ
        self.model_rate = model_rate
        self.api_type_summ = api_type_summ
        self.api_type_rate = api_type_rate

    def _summarize(self, text: str) -> str:
        response = self.client_summ.chat.completions.create(
            model = self.model_summ,
            messages = [
                {
                    "role": "system",
                    "content": SYS_PROMPT_SUMM,
                },
                {
                    "role": "user",
                    "content": f"{PROMPT_SUMM}{text}\n\nSummary:\n"
                }
            ],
            temperature = 0.4,
            max_tokens = 4096,
            stream = True
        )
        full_response = ""
        for chunk in response:
            if self.api_type_summ == "openai":
                if chunk.choices and chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
            elif self.api_type_summ == "ollama":
                if chunk.get('choices') and chunk['choices'][0]['delta']['content']:
                    full_response += chunk['choices'][0]['delta']['content']
        return full_response.strip()
    
    def _rate(self, text: str) -> float:
        response = self.client_rate.chat.completions.create(
            model = self.model_rate,
            messages = [
                {"role":"user","content":f"{text}\n{PROMPT_EVAL}"}
            ],
            temperature = 0.2,
            top_p = 0.8,
            max_tokens = 768,
            stream = False
        )
        
        if self.api_type_rate == "openai":
            result = response.choices[0].message.content.strip()
        elif self.api_type_rate == "ollama":
            result = response['choices'][0]['message']['content'].strip()
        result = result.replace('```json','').replace('```','')
        result = result.strip()
        
        try:
            ratings_data = json.loads(result)
            required_keys = {"ratings","justifications"}
            if not all(key in ratings_data for  key in required_keys):
                return "Missing keys in ratings data"
            weighted_sum = sum(
                WEIGHTS[criterion] * int(ratings_data['ratings'][criterion])
                for criterion in WEIGHTS
                if criterion in ratings_data['ratings']
            )
            return weighted_sum
        except json.JSONDecodeError:
            return "Invalid JSON format"

    def _select_and_filter(self, papers):
        if len(papers) < self.max_results*2:
            print("Not enough papers to filter, return all.")
            return papers
        elif self.workload:
            print("Machine under workload, return random samples.")
            return random.sample(papers, self.max_results*2)
        else:
            print("Filtering papers based on ratings.")
            if len(papers) > 384:
                print(f"Too many papers to rate ({len(papers)}), incorporate ramdom sampling.")
                papers = random.sample(papers, 384)
            rated_papers = []
            for paper in papers:
                pdf_url = paper['pdf_url']
                # Text Extraction
                info = f"Title: {paper['title']}\nAuthors: {paper['authors']}\n\n"
                text = self.crawler.extract_content(pdf_url)
                if not text:
                    #print(f"Empty content, skip <{paper['title']}>")
                    continue
                # Count token
                token_count = self.crawler.count_token(text)
                if isinstance(token_count,int) and token_count > 45056: # to prevent context window truncation
                    #print(f"Token limit ({token_count}), skip <{paper['title']}>")
                    continue
                elif (isinstance(token_count,int) and token_count <= 0) or not isinstance(token_count,int) :
                    #print(f"Token count error ({token_count}), skip <{paper['title']}>.")
                    continue
                # Rate
                text = info + text
                rating_result = self._rate(text)
                if self.api_type_rate == "openai":
                    time.sleep(5) # bypass TPM limit
                if isinstance(rating_result,str):
                    #print(f"JSON error ({rating_result}), skip <{paper['title']}>.")
                    continue
                elif isinstance(rating_result,float) and rating_result > 0:
                    rated_papers.append({
                        'paper': paper,
                        'rating': rating_result
                    })
            
            sorted_papers = sorted(rated_papers,key=lambda x: x['rating'], reverse=True)
            selected_papers = [item['paper'] for item in sorted_papers[:self.max_results*2]]
            return selected_papers

    def _write_pdf(self, designated_path: str=None):
        path = designated_path if designated_path else self.path
        cmd = [
            "pandoc",
            f"{path}.md",
            "-f", "gfm",
            "-t", "pdf",
            "--pdf-engine=xelatex",
            "-o", f"{path}.pdf",
            "--highlight-style=pygments",  # Better code highlighting
            "--variable", "classoption=14pt",
            "--variable", "documentclass=extarticle",
            "--variable", "geometry:margin=0.8in", # Tighter margins
            "--variable", "colorlinks=true", # Colored links instead of boxes
            "--variable", "linkcolor=RoyalBlue",
            "--variable", "linestretch=1.15", # Slightly tighter line spacing
            "--from", "markdown+raw_tex+yaml_metadata_block"
        ]

        try:
            subprocess.run(cmd, check=True)
            print(f"Successfully wrote pdf file: {path}.pdf")
        except subprocess.CalledProcessError as e:
            print(f"PDF conversion failed: {e}")
            raise RuntimeError(f"PDF conversion failed: {e}") from e
        except Exception as e:
            print(f"Unexpected error in PDF conversion: {e}")
            raise

    def _test_conversion(self, text: str, paper, markdown_folder: str="/home/kaupane/development/scripts/autosumm/temp") -> bool:
        """
        Test if generated summary for a single paper can be properly converted.
        """
        temp_path = f"{markdown_folder}/{paper['arxiv_id']}_doc"
        markdown_path = Path(f"{temp_path}.md")
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(text)
        
        cmd = [
            "pandoc",
            f"{temp_path}.md",
            "-f", "gfm",
            "-t", "pdf",
            "--pdf-engine=xelatex",
            "-o", f"{temp_path}.pdf",
            "--highlight-style=pygments",  # Better code highlighting
            "--variable", "classoption=14pt",
            "--variable", "documentclass=extarticle",
            "--variable", "geometry:margin=0.8in", # Tighter margins
            "--variable", "colorlinks=true", # Colored links instead of boxes
            "--variable", "linkcolor=RoyalBlue",
            "--variable", "linestretch=1.15", # Slightly tighter line spacing
            "--from", "markdown+raw_tex+yaml_metadata_block"
        ]

        try:
            subprocess.run(cmd, check=True)
            os.remove(f"{temp_path}.md")
            os.remove(f"{temp_path}.pdf")
            return True
        except Exception as e:
            print(f"Conversion test failed, skip <{paper['title']}>.")
            return False

    def _process_summary(self,summary: str) -> str:
        summary = re.sub(r'<think>.*?</think>','',summary,flags=re.DOTALL) # Remove <think> tags 
        result_str = ""
        i = 0
        in_equation = False
        in_bold = False
        in_italics = False

        while i < len(summary):
            if summary[i:i+2] == "$$": 
                if in_equation:
                    result_str += '$$'
                else:
                    result_str += '$$'
                in_equation = not in_equation
                i += 2
            elif summary[i] == '$' and not in_equation:
                result_str += ' $'
                i += 1
                # Skip first and last space inside equation to prevent render error
                while i < len(summary) and summary[i] != '$':
                    if summary[i]==' ' and summary[i-1]=='$':
                        i += 1
                    elif summary[i]==' ' and (i+1>=len(summary) or summary[i+1]=='$'):
                        i += 1
                    else:
                        result_str += summary[i]
                        i += 1
                if i < len(summary):
                    result_str += '$ '
                    i += 1
            elif summary[i:i+2] == '**':
                in_bold = not in_bold
                result_str += '**'
                i += 2
            elif summary[i] == '*':
                in_italics = not in_italics
                result_str += '*'
                i += 1
            elif summary[i:i+2] == '- ' and not in_equation and (i<2 or summary[i-1]=='\n' or summary[i-2:i]=='  '):
                result_str += '**>>** '
                i += 2
            elif re.match(r'(\d+)\.\s?', summary[i:]) and not in_equation and (i<2 or summary[i-1]=='\n' or summary[i-2:i]=='  '):
                match = re.match(r'(\d+)\.\s?', summary[i:])
                number = match.group(1)
                if not in_bold: 
                    result_str += f'**{number},** '
                else:
                    result_str += f'{number}, '
                i += len(match.group(0))
            else:
                result_str += summary[i]
                i += 1

        return result_str

    def compile(self) -> str:
        papers = self.crawler.fetch_arxiv_papers()
        print(f"Number of papers fetched: {len(papers)}")
        papers = self._select_and_filter(papers)
        print(f"Number of papers selected: {len(papers)}")
        summaries = []
        for paper in papers:
            # Extract and filter
            pdf_url = paper['pdf_url']
            text = self.crawler.extract_content(pdf_url) # No need to check text here, there's already a filter in _select_and_filter()
            # Title and authors
            summary = f"## Title: {paper['title']}\n##### Authors: "
            for author in paper['authors']:
                summary += f"{author}, "
            summary += f"\n##### Link: {paper['entry_id']}\n"
            # Summarize with LLM
            text = self._summarize(text)
            if text:
                summary += text
            else:
                print(f"Error: Empty return from _summarize(), title: {paper['title']}.")
                continue
            if self.api_type_summ == "openai":
                time.sleep(300) # To bypass potential TPM limit
            summary = self._process_summary(summary)
            if self._test_conversion(summary,paper):
                summaries.append(summary)
                if len(summaries) >= self.max_results:
                    break
        
        if len(summaries) == 0:
            raise RuntimeError(f"All {len(papers)} summaries failed to convert.")
        separator = "\n\n\\pagebreak\n\n"
        content = separator.join(summaries)
        content = re.sub(r'\\\((.*?)\\\)', r'$\1$', content)
        content = re.sub(r'\n{3,}',r'\n\n',content)

        markdown_path = Path(f"{self.path}.md")
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(content)
        print(f"Successfully wrote markdown file: {self.path}.md")

        self._write_pdf(self.path)

        return content
    
    def _rate_batch(self, texts: List[str]) -> List[float]:
        pass

    def _summarize_batch(self, texts: List[str], jsonl_folder: str="/home/kaupane/development/scripts/autosumm/temp") -> List[str]:
        input_path = Path(f"{jsonl_folder}/texts_input.jsonl")
        output_path = f"{jsonl_folder}/summaries_output.jsonl"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        # Create JSONL input file
        try:
            with open(input_path, "w", encoding="utf-8") as f:
                for i,text in enumerate(texts):
                    request = {
                        "custom_id": f"request_{i}",
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body":{
                            "model": self.model_summ,
                            "messages": [
                                {"role": "system", "content": SYS_PROMPT_SUMM},
                                {"role": "user", "content": f"{PROMPT_SUMM}{text}\n\nSummary:\n"}
                            ],
                            "temperature": 0.4,
                            "max_tokens": 4096
                        }
                    }
                    f.write(json.dumps(request) + "\n")
            print("JSONL file created successfully.")
        except Exception as e:
            raise RuntimeError("Failed to create JSONL file.")
        # Batch Inference
        try:
            # Upload file and create batch job
            file_object = self.client_summ.files.create(file=input_path,purpose="batch")
            input_file_id = file_object.id
            print("JSONL file uploaded.")
            batch = self.client_summ.batches.create(input_file_id=input_file_id,endpoint="/v1/chat/completions",completion_window="3h")
            batch_id = batch.id
            print("Batch job created.")
            # Wait for job completion
            while True:
                status = self.client_summ.batches.retrieve(batch_id).status
                if status in ["completed","failed","expired","cancelled"]:
                    break
                time.sleep(10)
            if status != "completed":
                print(f"Batch job failed with status: {status}")
                return [None] * len(texts)
            print(f"Batch job completed.")
            batch = self.client_summ.batches.retrieve(batch_id=batch_id)
            # Download results
            output_file_id = batch.output_file_id
            if output_file_id:
                content = self.client_summt.files.content(output_file_id)
                content.write_to_file(output_path)
            else:
                print("No output_file_id.")
                return [None] * len(texts)
            # Parse results
            summaries = []
            for line in content.splitlines():
                try:
                    data = json.loads(line)
                    if "response" in data and "body" in data["response"]:
                        body = data["response"]["body"]
                        if "choices" in body:
                            for choice in body["choices"]:
                                if "message" in choice and "content" in choice["message"]:
                                    summaries.append(choice["message"]["content"])
                except Exception as e:
                    print(f"Failed to parse line. Error: {e}")
                    return [None] * len(texts)
            # Pad if output length mismatch
            summaries += [None] * (len(texts) - len(summaries))
            return summaries
        except Exception as e:
            print(f"Batch processing error: {str(e)}")
            return [None] * len(texts)
        
    def compile_batch(self) -> str:
        papers = self.crawler.fetch_arxiv_papers()
        print(f"Number of papers fetched: {len(papers)}")
        papers = self._select_and_filter(papers)
        print(f"Number of papers selected: {len(papers)}")
        summaries = []
        texts = []
        for paper in papers[:self.max_results]:
            pdf_url = paper['pdf_url']
            text = self.crawler.extract_content(pdf_url)
            texts.append(text)
        texts = self._summarize_batch(texts)

        for text,paper in zip(texts,papers[:self.max_results]):
            summary = f"## Title: {paper['title']}\n##### Authors: "
            for author in paper['authors']:
                summary += f"{author}, "
            summary += f"\n##### Link: {paper['entry_id']}\n"
            if text:
                summary += text
            else:
                print(f"Error: Empty return from _summarize_batch(), title: {paper['title']}.")
                continue
            summary = self._process_summary(summary)
            if self._test_conversion(summary,paper):
                summaries.append(summary)
        
        if len(summaries) <= 4:
            raise RuntimeError("Summary generation failed.")

        for i in range(self.max_results,len(papers)):
            if len(summaries) >= self.max_results:
                break
            paper = papers[i]
            pdf_url = paper['pdf_url']
            text = self.crawler.extract_content(pdf_url)
            summary = f"## Title: {paper['title']}\n##### Authors: "
            for author in paper['authors']:
                summary += f"{author}, "
            summary += f"\n##### Link: {paper['entry_id']}\n"
            text = self._summarize(text)
            if text:
                summary += text
            else:
                print(f"Error: Empty return from _summarize(), title: {paper['title']}.")
                continue
            if self.api_type_summ == "openai":
                time.sleep(30) # To bypass TPM limit
            summary = self._process_summary(summary)
            if self._test_conversion(summary,paper):
                summaries.append(summary)

        separator = "\n\n\\pagebreak\n\n"
        content = separator.join(summaries)
        content = re.sub(r'\\\((.*?)\\\)', r'$\1$', content)
        content = re.sub(r'\n{3,}',r'\n\n',content)

        markdown_path = Path(f"{self.path}.md")
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(content)
        print(f"Successfully wrote markdown file: {self.path}.md")

        self._write_pdf(self.path)

        return content  

class OllamaWrapper:
    def __init__(self):
        import ollama
        self.client = ollama
        self.chat = self.Chat(self)

    class Chat:
        def __init__(self, parent):
            self.parent = parent
            self.completions = self.Completions(self.parent)

        class Completions:
            def __init__(self, parent):
                self.parent = parent

            def create(self, model: str, messages: list, temperature: float = 0.2, top_p: float = 0.8,
                    max_tokens: int = 2048, stream: bool = True):
                prompt = ""
                for message in messages:
                    if message["role"] == "user":
                        prompt += f"User: {message['content']}\n"
                    elif message["role"] == "assistant":
                        prompt += f"Assistant: {message['content']}\n"
                    elif message["role"] == "system":
                        prompt += f"System: {message['content']}\n"
                
                response = self.parent.client.chat(
                    model = model,
                    messages = [{"role": "user", "content": prompt}],
                    options = {
                        'temperature': temperature,
                        'top_p': top_p,
                        'num_predict': max_tokens,
                        'num_ctx': 65536,
                        'reset': True
                    },
                    stream = stream
                )

                if stream:
                    return self._stream_response(response)
                else:
                    return self._format_response(response)
                
            def _stream_response(self, response):
                for chunk in response:
                    if chunk.get('message') and chunk['message'].get('content'):
                        yield {"choices": [{"delta": {"content": chunk['message']['content']}}]}

            def _format_response(self, response):
                return {"choices": [{"message": {"content": response['message']['content']}}]}

class GoogleWrapper:
    def __init__(self):
        from google import genai
        # TBD

class ZhipuWrapper:
    def __init__(self):
        from zhipuai import ZhipuAI
        # TBD

def main():
    client_summ = OpenAI(api_key=ALIYUN_API_KEY,base_url=ALIYUN_BASE_URL)
    client_rate = OpenAI(api_key=SILICONFLOW_API_KEY,base_url=SILICONFLOW_BASE_URL)
    model_summ = "deepseek-r1"
    model_rate = "THUDM/glm-4-9b-instruct"
    api_type_summ = "openai"
    api_type_rate = "openai"
    max_results = 8
    summarizer = Summarizer(client_summ,client_rate,model_summ,model_rate,api_type_summ,api_type_rate,max_results,False)
    summarizer._write_pdf()

if __name__ == "__main__":
    main()