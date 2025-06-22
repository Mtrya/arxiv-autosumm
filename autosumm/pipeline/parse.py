"""
PDF parsing functionalities with fast and high-quality modes.
"""

import os
import re
import requests
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import fitz
from arxiv2text import arxiv_to_md

@dataclass
class VLMConfig:
    provider: str="ollama"
    api_key: Optional[str]=None
    base_url: str="http://localhost:11434"
    model: str="benhaotang/Nanonets-OCR-s:latest"
    batch: bool=False
    prompt: str="""Extract the text from the above document as if you were reading it naturally. Return the tables in html format. Return the equations in LaTeX representation. If there is an image in the document and image caption is not present, add a small description of the image inside the <img></img> tag; otherwise, add the image caption inside <img></img>. Watermarks should be wrapped in brackets. Ex: <watermark>OFFICIAL COPY</watermark>. Page numbers should be wrapped in brackets. Ex: <page_number>14</page_number> or <page_number>9/22</page_number>. Prefer using ☐ and ☑ for check boxes."""
    dpi: int=200

@dataclass
class ParseConfig:
    enable_vlm: bool=True
    tmp_dir: str="./tmp"
    vlm: Optional[VLMConfig]=field(default_factory=VLMConfig)

@dataclass
class ParseResult:
    content: str
    success: bool
    error: Optional[str]=None
    method: str="fast"

def parse_fast(pdf_url: str, config: ParseConfig) -> ParseResult:
    """
    Fast parsing using arxiv2text for rating phase.
    """
    try:
        # Use arxiv2text to convert PDF to markdown
        arxiv_to_md(pdf_url, config.tmp_dir)
        
        # Find the generated markdown file
        generated_files = [f for f in os.listdir(config.tmp_dir) if f.endswith('.md')]
        if not generated_files:
            raise ValueError("No markdown files found.")
        
        # Get the most recent file
        generated_files.sort(key=lambda f: os.path.getmtime(os.path.join(config.tmp_dir, f)), reverse=True)
        latest_file_path = os.path.join(config.tmp_dir, generated_files[0])
        
        # Read and clean the content
        with open(latest_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Remove inappropriate line breaks within paragraphs
        content = re.sub(r'(?<!\n)\n(?!\n)', ' ', content)
        
        # Remove content after "References" or "REFERENCES"
        match = re.search(r'\nReferences\n|\nREFERENCES\n', content)
        if match:
            content = content[:match.start()]
        
        # Clean up the temporary markdown file
        os.remove(latest_file_path)
        
        return ParseResult(
            content=content,
            success=True,
            method="fast"
        )
        
    except Exception as e:
        return ParseResult(
            content="",
            success=False,
            error=str(e),
            method="fast"
        )
    
def parse_vlm(pdf_url: str, config: ParseConfig) -> ParseResult:
    """
    High-quality VLM parsing.
    """
    try:
        image_dir = Path(config.tmp_dir)
        image_dir.mkdir(parents=True,exist_ok=True)

        if pdf_url.startswith(('http://','https://')):
            response = requests.get(pdf_url)
            response.raise_for_status()

            pdf_path = Path(config.tmp_dir) / "temp.pdf"
            with open(pdf_path,'wb') as f:
                f.write(response.content)
        else:
            pdf_path = Path(pdf_url)

        pdf_document = fitz.open(pdf_path)
        image_paths = []

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            mat = fitz.Matrix(config.vlm.dpi/72, config.vlm.dpi/72)
            pix = page.get_pixmap(matrix=mat)

            image_path = image_dir/f"page_{page_num+1}.png"
            pix.save(str(image_path))
            image_paths.append(str(image_path))

        pdf_document.close()

        page_contents = []

        for i, image_path in enumerate(image_paths):
            try:
                page_content = _process_image_with_vlm(image_path, config.vlm)
                page_contents.append(page_content)

            except Exception as e:
                print(f"VLM failed on page {i+1}: {e}")
                page_contents.append(f"[Page {i+1} processing failed]")
        
        full_content = "\n\n".join(page_contents)

        for image_path in image_paths:
            try:
                os.remove(image_path)
            except:
                pass
        
        if pdf_url.startswith(('http://','https://')):
            pdf_path.unlink(missing_ok=True)
    
        return ParseResult(
            content=full_content,
            success=True,
            method="vlm"
        )
    except Exception as e:
        print(f"VLM parsing failed: {e}")
        print(f"Falling back to fast parsing...")
        return parse_fast(pdf_url,config)
    
def _process_image_with_vlm(image_path: str, config: VLMConfig) -> str:
    """
    Process a single image with a VLM using OpenAI-compatible API.
    """
    import base64

    with open(image_path, 'rb') as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')

    # Construct endpoint URL
    endpoint = f"{config.base_url}/v1/chat/completions"
    
    # Prepare headers with API key if provided
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    # OpenAI-compatible payload
    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": config.prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 4000
    }
    
    response = requests.post(endpoint, headers=headers, json=payload)
    response.raise_for_status()
    
    result = response.json()
    return result['choices'][0]['message']['content']



if __name__ == "__main__":
    config = ParseConfig()

    pdf_url = "http://arxiv.org/pdf/1706.03762"
    result = parse_vlm(pdf_url, config)

    print(f"VLM parsing success: {result.success}")
    print(f"Content:\n{result.content}")