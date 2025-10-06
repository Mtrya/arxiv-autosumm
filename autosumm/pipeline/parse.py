"""
PDF parsing functionalities with fast and high-quality modes.
"""

import os
import subprocess
import shutil
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
import fitz
import base64
import logging
import requests

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
class MistralOCRConfig:
    api_key: str
    model: str = "mistral-ocr-latest"

@dataclass
class MinerUConfig:
    method: str = "auto"
    backend: str = "pipeline"
    url: Optional[str] = None
    device: str = "cpu"
    formula: bool = True
    table: bool = True
    vram: Optional[int] = None
    source: str = "huggingface"

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

def parse_mineru(cache_paths: List[str], config: ParserConfig, batch_config: Optional[BatchConfig]=None) -> List[ParseResult]:
    """
    Main interface function for MinerU parsing of multiple PDFs.

    Orchestrates the complete workflow:
    1. Create temporary output directories for each PDF
    2. Execute MinerU CLI with subprocess
    3. Read generated markdown content
    4. Clean up temporary files
    5. Return ParseResults with markdown content
    """
    if not config.mineru:
        logger.error("MinerU configuration is missing")
        return [
            ParseResult(
                content="",
                success=False,
                error="MinerU configuration is missing",
                method="mineru"
            ) for _ in cache_paths
        ]

    results = []

    for pdf_index, cache_path in enumerate(cache_paths):
        logger.info(f"Processing PDF {pdf_index+1}/{len(cache_paths)} with MinerU: {cache_path}")

        # Create temporary output directory
        temp_dir = None
        try:
            temp_dir = Path(batch_config.tmp_dir) / f"mineru_temp_{pdf_index}_{int(time.time())}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Validate PDF file exists
            if not os.path.exists(cache_path):
                logger.error(f"PDF file not found: {cache_path}")
                results.append(ParseResult(
                    content="",
                    success=False,
                    error=f"PDF file not found: {cache_path}",
                    method="mineru"
                ))
                continue

            # Build MinerU CLI command
            cmd = [
                "mineru",
                "-p", cache_path,
                "-o", str(temp_dir),
                "-m", config.mineru.method,
                "-b", config.mineru.backend,
                "--lang", "en",  # Hardcoded for arXiv papers
                "--formula", str(config.mineru.formula).lower(),
                "--table", str(config.mineru.table).lower(),
                "--device", config.mineru.device,
                "--source", config.mineru.source
            ]

            # Add optional URL if specified (for http-client backend)
            if config.mineru.url:
                cmd.extend(["--url", config.mineru.url])

            # Add optional VRAM limit if specified
            if config.mineru.vram:
                cmd.extend(["--vram", str(config.mineru.vram)])

            logger.info(f"Executing MinerU CLI: {' '.join(cmd)}")

            # Execute MinerU CLI
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout for large PDFs
            )

            if result.returncode != 0:
                error_msg = f"MinerU CLI failed with return code {result.returncode}: {result.stderr}"
                logger.error(error_msg)
                results.append(ParseResult(
                    content="",
                    success=False,
                    error=error_msg,
                    method="mineru"
                ))
                continue

            # Look for generated markdown file
            pdf_name = Path(cache_path).stem
            # MinerU creates nested structure: temp_dir/pdf_name/method/pdf_name.md
            md_file = temp_dir / pdf_name / config.mineru.method / f"{pdf_name}.md"

            if not md_file.exists():
                error_msg = f"MinerU did not generate expected markdown file: {md_file}"
                logger.error(error_msg)
                results.append(ParseResult(
                    content="",
                    success=False,
                    error=error_msg,
                    method="mineru"
                ))
                continue

            # Read markdown content
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                error_msg = f"Generated markdown file is empty: {md_file}"
                logger.error(error_msg)
                results.append(ParseResult(
                    content="",
                    success=False,
                    error=error_msg,
                    method="mineru"
                ))
                continue

            logger.info(f"Successfully processed PDF {pdf_index+1} with MinerU, content length: {len(content)}")
            results.append(ParseResult(
                content=content,
                success=True,
                error="",
                method="mineru"
            ))

        except subprocess.TimeoutExpired:
            error_msg = f"MinerU processing timed out for PDF {pdf_index+1} after 30 minutes"
            logger.error(error_msg)
            results.append(ParseResult(
                content="",
                success=False,
                error=error_msg,
                method="mineru"
            ))
        except Exception as e:
            error_msg = f"Error processing PDF {pdf_index+1} with MinerU: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results.append(ParseResult(
                content="",
                success=False,
                error=error_msg,
                method="mineru"
            ))
        finally:
            # Clean up temporary directory
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")

    logger.info(f"MinerU parsing completed: {len([r for r in results if r.success])} successful, {len([r for r in results if not r.success])} failed")
    return results

def parse_mistral(cache_paths: List[str], config: ParserConfig, batch_config: Optional[BatchConfig]=None) -> List[ParseResult]:
    """
    Main interface function for Mistral-OCR parsing of multiple PDFs.

    Orchestrates the complete workflow:
    1. Direct PDF processing via Mistral OCR API
    2. Response parsing and content extraction
    3. Result reconstruction (OCR results -> ParseResults)
    """
    if not config.mistral:
        logger.error("Mistral OCR configuration is missing")
        return [
            ParseResult(
                content="",
                success=False,
                error="Mistral OCR configuration is missing",
                method="mistral-ocr"
            ) for _ in cache_paths
        ]

    results = []

    for pdf_index, cache_path in enumerate(cache_paths):
        logger.info(f"Processing PDF {pdf_index+1}/{len(cache_paths)} with Mistral OCR: {cache_path}")

        try:
            # Validate PDF file exists
            if not os.path.exists(cache_path):
                logger.error(f"PDF file not found: {cache_path}")
                results.append(ParseResult(
                    content="",
                    success=False,
                    error=f"PDF file not found: {cache_path}",
                    method="mistral-ocr"
                ))
                continue

            # Read and encode PDF
            with open(cache_path, 'rb') as f:
                pdf_base64 = base64.b64encode(f.read()).decode('utf-8')

            # Prepare Mistral OCR API request
            api_url = "https://api.mistral.ai/v1/ocr"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.mistral.api_key}"
            }

            payload = {
                "model": config.mistral.model,
                "document": {
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{pdf_base64}"
                },
                "include_image_base64": True
            }

            logger.info(f"Sending PDF {pdf_index+1} to Mistral OCR API")

            # Make API request
            response = requests.post(api_url, headers=headers, json=payload, timeout=300)

            if response.status_code == 200:
                ocr_result = response.json()

                # Extract markdown content from all pages
                if "pages" in ocr_result and ocr_result["pages"]:
                    page_contents = []
                    for page in ocr_result["pages"]:
                        if "markdown" in page and page["markdown"].strip():
                            page_contents.append(page["markdown"].strip())

                    if page_contents:
                        full_content = "\n\n".join(page_contents)
                        logger.info(f"Successfully extracted {len(page_contents)} pages from PDF {pdf_index+1}")

                        results.append(ParseResult(
                            content=full_content,
                            success=True,
                            error="",
                            method="mistral-ocr"
                        ))
                    else:
                        logger.warning(f"No markdown content extracted from PDF {pdf_index+1}")
                        results.append(ParseResult(
                            content="",
                            success=False,
                            error="No markdown content extracted from OCR response",
                            method="mistral-ocr"
                        ))
                else:
                    logger.error(f"Invalid OCR response format for PDF {pdf_index+1}")
                    results.append(ParseResult(
                        content="",
                        success=False,
                        error="Invalid OCR response format: missing pages",
                        method="mistral-ocr"
                    ))
            else:
                error_msg = f"Mistral OCR API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                results.append(ParseResult(
                    content="",
                    success=False,
                    error=error_msg,
                    method="mistral-ocr"
                ))

        except requests.exceptions.Timeout:
            error_msg = f"Timeout processing PDF {pdf_index+1} with Mistral OCR"
            logger.error(error_msg)
            results.append(ParseResult(
                content="",
                success=False,
                error=error_msg,
                method="mistral-ocr"
            ))
        except Exception as e:
            error_msg = f"Error processing PDF {pdf_index+1} with Mistral OCR: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results.append(ParseResult(
                content="",
                success=False,
                error=error_msg,
                method="mistral-ocr"
            ))

    logger.info(f"Mistral OCR parsing completed: {len([r for r in results if r.success])} successful, {len([r for r in results if not r.success])} failed")
    return results


if __name__ == "__main__":
    def save_parse_result(result: ParseResult, output_path: str):
        """Save ParseResult to a markdown file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Parse Result\n\n")
                f.write(f"**Method:** {result.method}\n")
                f.write(f"**Success:** {result.success}\n")
                if result.error:
                    f.write(f"**Error:** {result.error}\n")
                f.write(f"\n---\n\n")
                f.write(result.content)
            print(f"Parse result saved to: {output_path}")
        except Exception as e:
            print(f"Error saving parse result: {e}")
            
    # Test Mistral OCR
    mistral_config = MistralOCRConfig(
        model="mistral-ocr-latest",
        api_key=os.getenv("MISTRAL_API_KEY", "")
    )

    config = ParserConfig(
        method="mistral-ocr",
        tmp_dir="./tmp",
        vlm=None,
        mistral=mistral_config,
        mineru=None
    )

    batch_config = BatchConfig(
        tmp_dir="./tmp",
        max_wait_hours=24,
        poll_interval_seconds=30,
        fallback_on_error=True
    )

    # Test with a sample PDF - replace with an actual PDF path you have
    cache_path = "/home/whititera/Developments/arxiv-autosumm/test.pdf"  # Replace with actual PDF path

    """print("Testing Mistral OCR parsing...")
    if os.path.exists(cache_path):
        result = parse_mistral([cache_path], config, batch_config)[0]

        print(f"Mistral OCR parsing success: {result.success}")
        if result.error:
            print(f"Error: {result.error}")

        # Save result to markdown file
        output_path = "mistral_ocr_result.md"
        save_parse_result(result, output_path)

        # Print first 500 characters of content
        if result.content:
            print(f"Content preview:\n{result.content[:500]}...")
    else:
        print(f"PDF file not found: {cache_path}")
        print("Please update cache_path with a valid PDF file path to test Mistral OCR")

    print("\n" + "="*50)
    print("Testing MinerU parsing...")"""

    # Test MinerU
    mineru_config = MinerUConfig(
        backend="pipeline",
        method="auto",
        device="cpu",
        formula=True,
        table=True,
        source="huggingface"
    )

    config_mineru = ParserConfig(
        method="mineru",
        tmp_dir="./tmp",
        vlm=None,
        mistral=None,
        mineru=mineru_config
    )

    # Test with a sample PDF - replace with an actual PDF path you have
    cache_path_mineru = "/home/whititera/Developments/arxiv-autosumm/test.pdf"  # Replace with actual PDF path

    print("Testing MinerU parsing...")
    if os.path.exists(cache_path_mineru):
        result_mineru = parse_mineru([cache_path_mineru], config_mineru, batch_config)[0]

        print(f"MinerU parsing success: {result_mineru.success}")
        if result_mineru.error:
            print(f"Error: {result_mineru.error}")

        # Save result to markdown file
        output_path_mineru = "mineru_result.md"
        save_parse_result(result_mineru, output_path_mineru)

        # Print first 500 characters of content
        if result_mineru.content:
            print(f"Content preview:\n{result_mineru.content[:500]}...")
    else:
        print(f"PDF file not found: {cache_path_mineru}")
        print("Please update cache_path_mineru with a valid PDF file path to test MinerU")