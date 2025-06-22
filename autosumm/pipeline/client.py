"""
Reusable base client object for ParserVLMClient, RaterLLMClient and SummarizerLLMClient.
"""

import json
import time
import requests
import tiktoken
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class BatchConfig:
    tmp_dir: str="./tmp"
    max_wait_hours: int=24
    poll_intervall_seconds: int=30
    fallback_on_error: bool=True

class BaseClient(ABC):
    def __init__(self, config, batch_config: Optional[BatchConfig]=None):
        self.config = config
        self.batch_config = batch_config or BatchConfig()

    @abstractmethod
    def _build_payload(self, input_data: Any) -> dict:
        """Build API payload for a single request. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _parse_response(self, response_content: str) -> str:
        """Parse API response content. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _get_endpoint_url(self) -> str:
        """Get the appropriate endpoint URL for the provider."""
        pass

    def _get_headers(self) -> dict:
        """Get common headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers
    
    def _make_sync_request(self, payload: dict) -> str:
        """Make a synchronous API request."""
        headers = self._get_headers()
        endpoint = self._get_endpoint_url()

        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()

        if "ollama" in self.config.provider.lower():
            return self._handle_ollama_response(response, payload.get("stream", False))
        else:
            return self._handle_openai_response(response, payload.get("stream", False))
        
    def _handle_ollam_response(self, response, is_streaming: bool) -> str:
        """Handle Ollama API response format."""
        if is_streaming:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        if chunk.get('message', {}).get('content'):
                            full_response += chunk['message']['content']
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
            return full_response.strip()
        else:
            result = response.json()
            return result['message']['content']
        
    def _handle_openai_response(self, response, is_streaming: bool) -> str:
        """Handle OpenAI-compatible API response format."""
        if is_streaming:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        if line.strip() == 'data: [DONE]':
                            break
                        try:
                            chunk = json.loads(line[6:])  # Remove 'data: ' prefix
                            if chunk.get('choices', [{}])[0].get('delta', {}).get('content'):
                                full_response += chunk['choices'][0]['delta']['content']
                        except json.JSONDecodeError:
                            continue
            return full_response.strip()
        else:
            result = response.json()
            return result['choices'][0]['message']['content']
        
    def _create_batch_jsonl(self, input_data_list: List[Any], jsonl_path: str):
        """Create JSONL file for batch processing"""
        Path(jsonl_path).parent.mkdir(parents=True,exist_ok=True)

        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for i, input_data in enumerate(input_data_list):
                payload = self._build_payload(input_data)
                # Remove streaming for batch processing
                payload.pop('stream', None)
                
                request = {
                    "custom_id": f"request_{i}",
                    "method": "POST",
                    "url": self._get_batch_endpoint_path(),
                    "body": payload
                }
                f.write(json.dumps(request) + "\n")

    def _get_batch_endpoint_path(self) -> str:
        """Get the endpoint path for batch requests (without base URL)"""
        return "/v1/chat/completions"
    
    def _submit_batch_job(self, jsonl_path: str) -> str:
        """Upload file and create batch job. Returns batch_id"""
        headers = self._get_headers()
        
        # Upload file
        files_endpoint = f"{self.config.base_url.rstrip('/')}/files"
        with open(jsonl_path, 'rb') as f:
            files_response = requests.post(
                files_endpoint,
                headers={"Authorization": headers.get("Authorization", "")},
                files={"file": f},
                data={"purpose": "batch"}
            )
        files_response.raise_for_status()
        file_id = files_response.json()["id"]
        
        # Create batch job
        batch_endpoint = f"{self.config.base_url.rstrip('/')}/batches"
        batch_payload = {
            "input_file_id": file_id,
            "endpoint": self._get_batch_endpoint_path(),
            "completion_window": "24h"
        }
        
        batch_response = requests.post(batch_endpoint, headers=headers, json=batch_payload)
        batch_response.raise_for_status()
        
        return batch_response.json()["id"]

    def _wait_for_batch(self, batch_id: str) -> Dict[str,Any]:
        """Wait for batch job completion and return batch info"""
        headers = self._get_headers()
        batch_endpoint = f"{self.config.base_url.rstrip('/')}/batches/{batch_id}"
        
        max_polls = (self.batch_config.max_wait_hours * 3600) // self.batch_config.poll_interval_seconds
        
        for _ in range(max_polls):
            response = requests.get(batch_endpoint, headers=headers)
            response.raise_for_status()
            batch_info = response.json()
            
            status = batch_info["status"]
            if status in ["completed", "failed", "expired", "cancelled"]:
                return batch_info
                
            time.sleep(self.batch_config.poll_interval_seconds)
        
        raise TimeoutError(f"Batch job {batch_id} did not complete within {self.batch_config.max_wait_hours} hours")
    
    def _download_batch_results(self, batch_info: Dict[str,Any], output_path: str) -> List[str]:
        """Download and parse batch results"""
        if batch_info["status"] != "completed":
            raise RuntimeError(f"Batch job failed with status: {batch_info['status']}")
        
        output_file_id = batch_info.get("output_file_id")
        if not output_file_id:
            raise RuntimeError("No output file available")
        
        # Download results file
        headers = self._get_headers()
        download_endpoint = f"{self.config.base_url.rstrip('/')}/files/{output_file_id}/content"
        
        response = requests.get(download_endpoint, headers=headers)
        response.raise_for_status()
        
        # Save to file
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        # Parse results
        results = {}  # custom_id -> response content
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    result_item = json.loads(line.strip())
                    custom_id = result_item["custom_id"]
                    
                    if "error" in result_item:
                        results[custom_id] = None
                    else:
                        response_body = result_item["response"]["body"]
                        if "error" in response_body:
                            print(f"Batch item {custom_id} API error: {response_body['error']}")
                            results[custom_id] = None
                        else:
                            content = response_body["choices"][0]["message"]["content"]
                            results[custom_id] = content
                        
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Failed to parse result line: {e}")
                    continue
        
        # Return results in original order
        ordered_results = []
        for i in range(len(results)):
            custom_id = f"request_{i}"
            ordered_results.append(results.get(custom_id))
        
        return ordered_results
    
    def _retry_failed_items(self, input_data_list: List[Any], batch_results: List[Optional[str]]) -> List[Optional[str]]:
        """Retry failed batch items individually"""
        if not self.batch_config.fallback_on_error:
            return batch_results

        final_results = batch_results.copy()
        failed_indices = [i for i,result in enumerate(batch_results) if result is None]

        if not failed_indices:
            return final_results
        
        print(f"Retrying {len(failed_indices)} failed items individually...")

        for idx in failed_indices:
            try:
                individual_result = self.process_single(input_data_list[idx])
                final_results[idx] = individual_result
                if individual_result is not None:
                    print(f"Successfully recovered item {idx} via individual processing")
            except Exception as e:
                print(f"Individual retry failed for item {idx}: {e}")

        return final_results
    
    def process_batch(self, input_data_list: List[Any]) -> List[Optional[str]]:
        """
        Process multiple inputs using batch API.
        Returns list of results in same order as inputs.
        """
        if "ollama in self.config.provider.lower()":
            if self.batch_config.fallback_on_error:
                return [self.process_single(input_data) for input_data in input_data_list]
            else:
                raise ValueError("Batch processing not supported for Ollama provider")
            
        try:
            tmp_dir = Path(self.batch_config.tmp_dir)
            tmp_dir.mkdir(parents=True,exist_ok=True)

            jsonl_path = tmp_dir/f"batch_input_{int(time.time())}.jsonl"
            output_path = tmp_dir/f"batch_output_{int(time.time())}.jsonl"

            # Create batch job
            self._create_batch_jsonl(input_data_list,str(jsonl_path))
            batch_id = self._submit_batch_job(str(jsonl_path))

            # Wait for completion and download results
            batch_info = self._wait_for_batch(batch_id)
            batch_results = self._download_batch_results(batch_info,str(output_path))

            # Retry failed items individually
            final_results = self._retry_failed_items(input_data_list,batch_results)

            # Cleanup
            jsonl_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)

            return final_results
        
        except Exception as e:
            print(f"Batch processing failed: {e}")
            if self.batch_config.fallback_on_error:
                print("Falling back to sequential processing...")
                return [self.process_single(input_data) for input_data in input_data_list]
            else:
                raise

    def process_single(self, input_data: Any) -> Optional[str]:
        """Process single input synchronously"""
        try:
            payload = self._build_payload(input_data)
            response_content = self._make_sync_request(payload)
            return self._parse_response(response_content)
        except Exception as e:
            print(f"Single processing failed: {e}")
            return None


def count_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text,disallowed_special=()))

def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text"""
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text, disallowed_special=())
    if len(tokens) <= max_tokens:
        return text
    
    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)