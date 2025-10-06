"""
PDF parsing functionalities with fast and high-quality modes.
"""

import os
import time
import zipfile
import io
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
import fitz
import base64
import logging
import requests

try:
    from client import BaseClient, BatchConfig, UsageInfo
except:
    from .client import BaseClient, BatchConfig, UsageInfo

logger = logging.getLogger(__name__)

@dataclass
class ParserVLMConfig:
    provider: Optional[str]
    api_key: Optional[str]
    base_url: Optional[str]
    model: str
    batch: bool
    system_prompt: str
    user_prompt: str
    completion_options: Dict[str,Any]
    dpi: int=168

@dataclass
class MistralOCRConfig:
    api_key: str
    model: str = "mistral-ocr-latest"

@dataclass
class MinerUConfig:
    api_token: str
    is_ocr: bool = False
    enable_formula: bool = True
    enable_table: bool = True
    model_version: str = "pipeline"
    poll_interval: int = 10
    max_poll_time: int = 300

@dataclass
class ParserConfig:
    method: str
    tmp_dir: str
    vlm: Optional[ParserVLMConfig]
    mistral: Optional[MistralOCRConfig]
    mineru: Optional[MinerUConfig]

@dataclass
class ImageData:
    """Internal data structure for tracking images in batch processing"""
    image_path: str
    pdf_index: int # which PDF this image came from
    page_number: int # page number within the PDF

@dataclass
class ParseResult:
    content: str
    success: bool
    error: Optional[str]=None
    method: str="fast"

def _pdf_to_images(cache_path: str, pdf_index: int, config: ParserVLMConfig, tmp_dir: str) -> List[ImageData]:
    """Convert a single PDF to images and return ImageData list"""
    image_data_list = []

    try:
        # Route based on cache_path content
        if cache_path is None:
            logger.error(f"No cache path provided for PDF {pdf_index+1}")
            return []
        # Use cached PDF file
        if not os.path.exists(cache_path):
            logger.error(f"Cached PDF file not found: {cache_path}")
            return []
        pdf_path = Path(cache_path)
        
        # Convert to images using PyMuPDF
        pdf_document = fitz.open(pdf_path)
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            mat = fitz.Matrix(config.dpi/72, config.dpi/72)
            pix = page.get_pixmap(matrix=mat)
            
            image_path = Path(tmp_dir) / f"pdf_{pdf_index}_page_{page_num+1}.png"
            pix.save(str(image_path))
            
            image_data_list.append(ImageData(
                image_path=str(image_path),
                pdf_index=pdf_index,
                page_number=page_num + 1
            ))
        
        pdf_document.close()
            
    except Exception as e:
        logger.error(f"Error converting PDF {pdf_index} to images: {e}",exc_info=True)
        return []
    
    return image_data_list

def _cleanup_images(image_data_list: List[ImageData]):
    for image_data in image_data_list:
        try:
            Path(image_data.image_path).unlink(missing_ok=True)
        except OSError as e:
            logger.warning(f"Could not clean up image {image_data.image_path}: {e}", exc_info=True)

def _reconstruct_results(vlm_results: List[Optional[str]], pdf_image_counts: List[int]) -> List[ParseResult]:
    """Reconstruct VLM results back to ParseResults per PDF"""
    results = []
    result_index = 0

    for pdf_index, image_count in enumerate(pdf_image_counts):
        if image_count == 0:
            results.append(ParseResult(
                content="",
                success=False,
                error="No pages extracted from PDF",
                method="vlm"
            ))
            continue

        pdf_vlm_results = vlm_results[result_index:result_index+image_count]
        result_index += image_count

        if any(result is None for result in pdf_vlm_results):
            results.append(ParseResult(
                content="",
                success=False,
                error="At least one page failed VLM processing",
                method="vlm"
            ))
            continue

        page_contents = [result for result in pdf_vlm_results if result]
        full_content = "\n\n".join(page_contents)

        results.append(ParseResult(
            content=full_content,
            success=True,
            error="",
            method="vlm"
        ))

    return results

class ParserVLMClient(BaseClient):
    def __init__(self, config: ParserVLMConfig, batch_config: Optional[BatchConfig]=None):
        super().__init__(config,batch_config)

    def _build_payload(self, image_data: ImageData) -> dict:
        """Build VLM API payload for a single image"""
        with open(image_data.image_path,'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        messages = [{"role": "system", "content": self.config.system_prompt}]
        
        messages.append({
            "role": "user",
            "content": [
                {"type": "text","text": self.config.user_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}","detail": "high"}}
            ]
        })

        base_payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False
        }

        if "ollama" in self.config.provider.lower():
            options = self.config.completion_options.copy()
            if 'max_tokens' in options:
                options['num_predict'] = options.pop('max_tokens')
            base_payload["options"] = options
        else:
            base_payload.update(self.config.completion_options)

        return base_payload
    
    def _parse_response(self, response_content: str) -> str:
        return response_content.strip()
    
    def _get_endpoint_url(self) -> str:
        if self.config.provider.lower() == "anthropic":
            return f"{self.config.base_url.rstrip('/')}/v1/messages"
        elif self.config.provider.lower() == "ollama":
            return f"{self.config.base_url.rstrip('/')}/v1/chat/completions"
        else:
            return f"{self.config.base_url.rstrip('/')}/chat/completions"
    
    def _handle_ollama_response(self, response, is_streaming):
        """Override because 'http://localhost:11434/v1/chat/completions' return openai-compatible response"""
        return super()._handle_openai_response(response, is_streaming)
        
def parse_vlm(cache_paths: List[str], config: ParserConfig, batch_config: Optional[BatchConfig]=None) -> List[ParseResult]:
    """
    Main interface function for VLM parsing of multiple PDFs.
    
    Orchestrates the complete workflow:
    1. PDF decomposition (URLs → ImageData)
    2. VLM processing via ParserVLMClient  
    3. Result reconstruction (VLM results → ParseResults)
    """
    if batch_config is None:
        batch_config = BatchConfig()

    all_image_data = []
    pdf_image_counts = []
    
    for pdf_index, cache_path in enumerate(cache_paths):
        logger.info(f"Processing PDF {pdf_index+1}/{len(cache_paths)}: {cache_path}")
        image_data_list = _pdf_to_images(cache_path,pdf_index,config.vlm,batch_config.tmp_dir)
        all_image_data.extend(image_data_list)
        pdf_image_counts.append(len(image_data_list))
        logger.info(f"Extracted {len(image_data_list)} pages from PDF {pdf_index+1}")
    
    if not all_image_data:
        logger.warning("No images extracted from any PDF")
        return [
            ParseResult(
                content="",
                success=False,
                error="No image extracted.",
                method="vlm"
            ) for _ in cache_paths
        ]

    vlm_client = ParserVLMClient(config.vlm, batch_config)
    logger.info(f"Processing {len(all_image_data)} images with VLM (batch={config.vlm.batch})")

    if config.vlm.batch:
        vlm_results = vlm_client.process_batch(all_image_data)
    else:
        vlm_results = []
        for image_data in all_image_data:
            result, usage_info = vlm_client._process_single_with_usage(image_data, sleep_time=3)
            if usage_info and (usage_info.prompt_tokens > 0 or usage_info.completion_tokens > 0):
                logger.info(f"Converted image with {usage_info}")
            else:
                logger.info(f"Converted image with {vlm_client.config.model} (usage info unavailable)")
            vlm_results.append(result)
    
    results = _reconstruct_results(vlm_results, pdf_image_counts)

    _cleanup_images(all_image_data)
    logger.info(f"VLM parsing completed: {len([r for r in results if r.success])} successful, {len([r for r in results if not r.success])} failed")

    return results

def _ocr_pdf(cache_path: str, config: ParserConfig):
    with open(cache_path, 'rb') as f:
        pdf_base64 = base64.b64encode(f.read()).decode('utf-8')

    payload = {
        "model": config.mistral.model,
        "document": {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{pdf_base64}"
        },
        "include_image_base64": True
    }

    response = requests.post(
        "https://api.mistral.ai/v1/ocr",
        headers={"Authorization": f"Bearer {config.mistral.api_key}"},
        json=payload,
        timeout=300
    )

    response.raise_for_status()  # Raise HTTP errors
    return response.json()

def _validate_mistral_response(response_data):
    """Validate Mistral OCR API response structure"""
    if not isinstance(response_data, dict):
        raise ValueError("Invalid API response: expected JSON object")

    if "pages" not in response_data:
        raise ValueError("Invalid API response: missing 'pages' field")

    if not isinstance(response_data["pages"], list):
        raise ValueError("Invalid API response: 'pages' must be a list")

    return response_data

def _construct_markdown_mistral(ocr_result: str):
    validated_result = _validate_mistral_response(ocr_result)

    markdown_content = "\n\n".join([
        page["markdown"]
        for page in validated_result["pages"] if page["markdown"].strip()
    ])
    return markdown_content

def parse_mistral(cache_paths: List[str], config: ParserConfig, batch_config: Optional[BatchConfig]=None) -> List[ParseResult]:
    """
    Parse PDFs using Mistral OCR API.

    Data flow:
    1. Read PDF → base64
    2. POST /v1/ocr → get pages with markdown
    3. Extract markdown from pages
    """

    results = []
    for cache_path in cache_paths:
        ocr_result = _ocr_pdf(cache_path, config)

        markdown_content = _construct_markdown_mistral(ocr_result)

        logger.debug(f"Successfully parsed {cache_path} with Mistral-OCR")

        results.append(ParseResult(
            content=markdown_content,
            success=bool(markdown_content),
            error="" if markdown_content else "No markdown content found",
            method="mistral-ocr"
        ))

    return results

def _request_upload_urls(cache_paths: List[str], config: ParserConfig):
    payload = {
        "enable_formula": config.mineru.enable_formula,
        "enable_table": config.mineru.enable_table,
        "language": "en",
        "model_version": config.mineru.model_version,
        "files": [
            {"name": Path(p).name, "is_ocr": config.mineru.is_ocr, "data_id": f"arxiv_{i}_{int(time.time())}"}
            for i, p in enumerate(cache_paths)
        ]
    }

    response = requests.post(
        "https://mineru.net/api/v4/file-urls/batch",
        headers={"Authorization": f"Bearer {config.mineru.api_token}"},
        json=payload
    )

    data = response.json()
    return data["data"]["batch_id"], data["data"]["file_urls"]

def _upload_files(cache_paths: List[str], upload_urls: List[str]):
    for cache_path, upload_url in zip(cache_paths, upload_urls):
        with open(cache_path, 'rb') as f:
            requests.put(upload_url, data=f)

def _poll_results(config: ParserConfig, batch_id):
    start_time = time.time()
    while time.time() - start_time < config.mineru.max_poll_time:
        response = requests.get(
            f"https://mineru.net/api/v4/extract-results/batch/{batch_id}",
            headers={"Authorization": f"Bearer {config.mineru.api_token}"}
        )

        response.raise_for_status()  # Raise HTTP errors
        results = response.json()["data"]["extract_result"]
        if all(r["state"] in ["done", "failed"] for r in results):
            return results

        time.sleep(config.mineru.poll_interval)

    raise TimeoutError(f"MinerU processing timeout after {config.mineru.max_poll_time} seconds")

def _construct_markdown_mineru(zip_url):
    """Construct markdown from MinerU content_list.json with proper heading levels"""
    import json
    import re

    response = requests.get(zip_url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        # Find content_list.json file
        content_files = [f for f in zf.namelist() if f.endswith('_content_list.json')]
        if not content_files:
            # Fallback to full.md if content_list.json not found
            return zf.read("full.md").decode('utf-8')

        content_file = content_files[0]
        content_data = json.loads(zf.read(content_file).decode('utf-8'))

    markdown_lines = []

    for item in content_data:
        if item["type"] == "text":
            text = item["text"].strip()

            # Handle headings based on text_level and text content
            if "text_level" in item and item["text_level"] == 1:
                # Count dots in heading text to determine markdown level
                dot_count = text.count('.')

                # Special cases for appendix sections like "D.2"
                if re.match(r'^[A-Z]\.\d+', text):
                    dot_count = text.count('.') + 1

                # Determine markdown heading level (1-6)
                # No dots = level 1, 1 dot = level 2, etc.
                heading_level = min(dot_count + 1, 6)
                markdown_lines.append(f"{'#' * heading_level} {text}")
            else:
                # Regular text
                markdown_lines.append(text)

        elif item["type"] == "image":
            # Handle images - for now just include captions
            # Future: Add image captioner integration here
            if "image_caption" in item and item["image_caption"]:
                caption_text = " ".join(item["image_caption"])
                markdown_lines.append(f"\n![Image]({item['img_path']})\n\n{caption_text}\n")

    return "\n\n".join(markdown_lines)

def parse_mineru(cache_paths: List[str], config: ParserConfig, batch_config: Optional[BatchConfig]=None) -> List[ParseResult]:
    """
    Parse PDFs using MinerU API batch upload.

    Data flow:
    1. POST /file-urls/batch → get batch_id, upload_urls
    2. PUT files to upload_urls
    3. GET /extract-results/batch/{batch_id} → get extract_results
    4. Download ZIPs, construct markdown
    """

    # Execute workflow
    batch_id, upload_urls = _request_upload_urls(cache_paths, config)
    _upload_files(cache_paths, upload_urls)
    results = _poll_results(config, batch_id)

    # Build ParseResults
    parse_results = []
    for cache_path in cache_paths:
        filename = Path(cache_path).name

        result = next((r for r in results if r["file_name"] == filename), None)
        if not result:
            parse_results.append(ParseResult("", False, "File not found in results", "mineru"))
            continue

        if result["state"] == "failed":
            parse_results.append(ParseResult("", False, result["err_msg"], "mineru"))
        else:
            # Construct markdown content
            content = _construct_markdown_mineru(result["full_zip_url"])

            logger.debug(f"Successfully parsed {cache_path} with MinerU")

            parse_results.append(ParseResult(content, True, "", "mineru"))

    return parse_results


