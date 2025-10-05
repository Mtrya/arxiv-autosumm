"""
PDF parsing functionalities with fast and high-quality modes.
"""

import os
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
import fitz
import base64
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams
import logging

try:
    from client import BaseClient, BatchConfig
except:
    from .client import BaseClient, BatchConfig

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
class ParserConfig:
    method: str
    tmp_dir: str
    vlm: Optional[ParserVLMConfig]

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

def parse_mineru(cache_paths: List[str], config: ParserConfig, batch_config: Optional[BatchConfig]=None) -> List[ParseResult]:
    """
    Main interface function for MinerU parsing of multiple PDFs.
    """

if __name__ == "__main__":
    vlm_config = ParserVLMConfig(
        provider="openrouter",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="amazon/nova-lite-v1",
        batch=False,
        system_prompt="""You are an AI specialized in recognizing and extracting text. 
Your **sole** mission is to analyze the image document and return it in **markdown** format, use markdown syntax to preserve the title level of the original document.""",
        user_prompt="""Extract the text from the above document image as if you were reading it naturally. Return the equations in LaTeX representation. If there is an image in the document and image caption is not present, add a brief description of the image. If there is a table in the document and table caption is not present, add a brief description of the table without reproducing it with html. Do not include page numbers for better readability.""",
        completion_options={"temperature":0.2}
    )
    batch_config = BatchConfig(
        tmp_dir="./tmp",
        max_wait_hours=24,
        poll_interval_seconds=30,
        fallback_on_error=True
    )
    config = ParserConfig(
        enable_vlm=True,
        tmp_dir="./tmp",
        fast_parser_timeout_seconds=300,
        vlm=vlm_config
    )


    pdf_url = "http://arxiv.org/pdf/1706.03762"
    result = parse_vlm([pdf_url], config, batch_config)[0]

    print(f"VLM parsing success: {result.success}")
    print(f"Content:\n{result.content}")