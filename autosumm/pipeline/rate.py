"""
Rate fetched papers with a coarse-to-fine strategy.
"""

import numpy as np
import requests
import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Union, Tuple, Any
from json_repair import repair_json
import logging

try:
    from client import BaseClient, BatchConfig, UsageInfo, count_tokens, truncate_to_tokens
except:
    from .client import BaseClient, BatchConfig, UsageInfo, count_tokens, truncate_to_tokens

logger = logging.getLogger(__name__)

@dataclass
class RaterEmbedderConfig:
    provider: Optional[str]
    api_key: Optional[str]
    base_url: Optional[str]
    model: str
    query_template: str="High-quality {user_interests} research paper with novel contributions, rigorous methodology, clear presentation and significant impact."
    user_interests: Optional[str]=None
    context_length: int=2048

@dataclass
class RaterLLMConfig:
    provider: Optional[str]
    api_key: Optional[str]
    base_url: Optional[str]
    model: str
    batch: bool
    system_prompt: Optional[str]
    user_prompt_template: str
    completion_options: Dict[str,Any]
    context_length: Optional[int]
    criteria: Dict[str,Dict[str,Union[str,float]]]

@dataclass
class RaterConfig:
    strategy: str
    top_k: int
    max_selected: int
    embedder: Optional[RaterEmbedderConfig]
    llm: Optional[RaterLLMConfig]

@dataclass
class RateResult:
    score: float
    success: bool
    error: Optional[str]
    method: str="embed"

def cosine_similarity(a: List[float], b: List[float]) -> float:
    a = np.array(a)
    b = np.array(b)

    dot_product = np.dot(a,b)
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)

    if a_norm == 0 or b_norm == 0:
        return 0.0
    
    return dot_product / (a_norm * b_norm)

def chunk_text(text: str, max_tokens: int) -> List[Tuple[str, int]]:
    """Split text into chunks that fit within token limit."""
    sentences = text.split('. ')
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)
        
        # If single sentence exceeds limit, truncate it
        if sentence_tokens > max_tokens:
            truncated = truncate_to_tokens(sentence, max_tokens)
            if current_chunk:
                chunks.append((current_chunk.strip(), current_tokens))
            chunks.append((truncated, max_tokens))
            current_chunk = ""
            current_tokens = 0
            continue
        
        # If adding this sentence would exceed limit, start new chunk
        if current_tokens + sentence_tokens > max_tokens:
            if current_chunk:
                chunks.append((current_chunk.strip(), current_tokens))
            current_chunk = sentence
            current_tokens = sentence_tokens
        else:
            current_chunk += (". " if current_chunk else "") + sentence
            current_tokens += sentence_tokens
    
    # Add final chunk
    if current_chunk:
        chunks.append((current_chunk.strip(), current_tokens))
    
    return chunks

class RaterEmbedderClient(BaseClient):
    def __init__(self, config: RaterEmbedderConfig, batch_config: Optional[BatchConfig]=None):
        super().__init__(config, batch_config)
        self.context_length = config.context_length or 32768
        self.query_embedding = self._compute_query_embedding()

    def _compute_query_embedding(self) -> List[float]:
        query = self.config.query_template.format(user_interests=self.config.user_interests)

        headers = self._get_headers()
        endpoint = self._get_endpoint_url()

        if "ollama" in self.config.provider.lower():
            payload = {
                "model": self.config.model,
                "prompt": query
            }
        else:
            payload = {
                "model": self.config.model,
                "input": query
            }
        
        response = requests.post(endpoint, headers=headers,json=payload)
        response.raise_for_status()
        result = response.json()

        if "ollama" in self.config.provider.lower():
            return result.get("embedding",[])
        else:
            return result["data"][0]["embedding"]

    def _build_payload(self, text_chunk: str):
        if "ollama" in self.config.provider.lower() or self.config.base_url.startswith("http://localhost"):
            payload = {
                "model": self.config.model,
                "prompt": text_chunk
            }
        else:
            payload = {
                "model": self.config.model,
                "input": [text_chunk]
            }
        return payload
    
    def _get_endpoint_url(self):
        if "ollama" in self.config.provider.lower() or self.config.base_url.startswith("http://localhost"):
            endpoint = f"{self.config.base_url.rstrip('/')}/api/embeddings"
        else:
            endpoint = f"{self.config.base_url.rstrip('/')}/embeddings"
        return endpoint
    
    def _parse_response(self, response):
        result = json.loads(response)

        if "ollama" in self.config.provider.lower():
            doc_embedding = result.get("embedding",[])
        else:
            doc_embedding = result["data"][0]["embedding"]

        return cosine_similarity(self.query_embedding, doc_embedding)

    def _make_sync_request(self, payload) -> tuple[str, Optional[UsageInfo]]:
        """Override to handle embedding response with usage tracking"""
        payload.pop('stream',None)

        headers = self._get_headers()
        endpoint = self._get_endpoint_url()

        response = requests.post(endpoint, headers=headers,json=payload)
        response.raise_for_status()

        result = response.json()

        # Extract usage information if available
        usage_info = UsageInfo(provider=self.config.provider, model=self.config.model)
        if "usage" in result:
            usage_data = result["usage"]
            usage_info.prompt_tokens = usage_data.get("prompt_tokens", 0)
            usage_info.completion_tokens = usage_data.get("completion_tokens", 0)
            usage_info.update_total()

        return json.dumps(result), usage_info
    
    def process_single(self, input_data, sleep_time = 0.0, return_usage=False):
        """Process single input, raising exception on failure."""
        result, usage_info = super().process_single(input_data, sleep_time, return_usage=True)
        if return_usage:
            if result is None: # error from base client
                return None, usage_info
            return result, usage_info
        else:
            if result is None: # error from base client
                return None
            return result
              
class RaterLLMClient(BaseClient):
    def __init__(self, config: RaterLLMConfig, batch_config: Optional[BatchConfig]=None):
        super().__init__(config, batch_config)
        # estimate available context
        prompt_tokens = 0
        if config.system_prompt:
            prompt_tokens += count_tokens(config.system_prompt)
        if config.user_prompt_template:
            prompt_tokens += count_tokens(config.user_prompt_template)
        safety_margin = 512
        output_tokens = config.completion_options.get('max_tokens', 1024)
        base_context = config.context_length or 65536
        self.available_context = base_context - prompt_tokens - output_tokens - safety_margin

    def _build_payload(self, parsed_content: str) -> dict:
        """Build API payload for rating request."""
        token_count = count_tokens(parsed_content)
        if token_count > self.available_context:
            logger.warning(f"Content too long ({token_count} tokens), truncated to {self.available_context} tokens.")
            parsed_content = truncate_to_tokens(parsed_content, self.available_context)
        
        messages = self._create_messages(parsed_content)

        base_payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": True
        }

        if "ollama" in self.config.provider.lower():
            options = self.config.completion_options.copy()
            if 'max_tokens' in options:
                options['num_predict'] = options.pop('max_tokens')
            base_payload["options"] = options
        else:
            base_payload.update(self.config.completion_options)

        return base_payload
    
    def _get_endpoint_url(self) -> str:
        if self.config.provider.lower() == "anthropic":
            return f"{self.config.base_url.rstrip('/')}/v1/messages"
        elif self.config.provider.lower() == "ollama":
            return f"{self.config.base_url.rstrip('/')}/api/chat"
        else:
            return f"{self.config.base_url.rstrip('/')}/chat/completions"
        
    def _parse_response(self, response_content) -> float:
        try:
            response = repair_json(response_content)
            response = response.replace('```jons','').replace('```','').strip()
            ratings_data = json.loads(response)
            
            weighted_sum = 0.0
            total_weight = 0.0

            for criterion, details in self.config.criteria.items():
                if criterion in ratings_data and 'score' in ratings_data[criterion]:
                    score = float(ratings_data[criterion]['score'])
                    weight = details['weight']
                    weighted_sum += weight*score
                    total_weight += weight

            if total_weight > 0:
                final_score = weighted_sum / total_weight
            else:
                final_score = 0.0
                
        except Exception as e:
            #print(f"error parsing response {response}: {e}")
            return None
        
        return final_score

    def _create_messages(self, parsed_content) -> list:
        """Create message list."""
        messages = []

        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})
        
        # Make user prompt
        criteria_descriptions = []
        for criterion, details in self.config.criteria.items():
            criteria_descriptions.append(f"- {criterion}: {details['description']}")

        criteria_text = "\n".join(criteria_descriptions)

        user_content = self.config.user_prompt_template.format(criteria_text=criteria_text,paper_text=parsed_content)
        messages.append({"role": "user", "content": user_content})
        return messages

    def process_single(self, input_data, sleep_time = 2.5, return_usage=False):
        """Process single input, raising exception on failure."""
        result, usage_info = super().process_single(input_data, sleep_time, return_usage=True)
        if return_usage:
            if result is None:  # Add missing null check
                return None, usage_info
            return result, usage_info
        else:
            return result

def rate_embed(parsed_contents: List[str], config: RaterConfig, batch_config: Optional[BatchConfig]=None) -> List[RateResult]:
    """Rate papers using embedding similarity with text chunking."""
    embedder_client = RaterEmbedderClient(config.embedder, batch_config)
    results = []
    
    logger.info(f"Starting embedding-based rating for {len(parsed_contents)} papers")
    for content in parsed_contents:
        try:
            # Handle text chunking here
            token_count = count_tokens(content)
            
            if token_count <= embedder_client.context_length:
                # Text fits, get similarity directly
                similarity_score, usage_info = embedder_client._process_single_with_usage(content)
                if usage_info and (usage_info.prompt_tokens > 0 or usage_info.completion_tokens > 0):
                    logger.info(f"Rated paper with embedder {usage_info}")
                else:
                    logger.info(f"Rated paper with embedder {embedder_client.config.model} (usage info unavailable)")
            else:
                # Text too long, chunk and get weighted average
                chunks = chunk_text(content, embedder_client.context_length)
                chunk_texts = [chunk[0] for chunk in chunks]
                chunk_weights = [chunk[1] for chunk in chunks]
                
                # Get similarities for all chunks (could use batch processing here)
                chunk_similarities = [embedder_client._process_single_with_usage(chunk_text)[0] for chunk_text in chunk_texts]

                # Calculate weighted average, filtering out None values (failed API calls)
                valid_pairs = [(sim, weight) for sim, weight in zip(chunk_similarities, chunk_weights) if sim is not None]

                if valid_pairs:
                    total_weight = sum(weight for _, weight in valid_pairs)
                    if total_weight > 0:
                        weighted_similarity = sum(sim * weight for sim, weight in valid_pairs) / total_weight
                    else:
                        weighted_similarity = 0.0
                else:
                    # All chunks failed - this is a complete failure
                    weighted_similarity = None
                
                similarity_score = weighted_similarity
                logger.info(f"Rated paper with embedder {embedder_client.config.model} ({len(chunks)} chunks)")
            
            results.append(RateResult(
                score=similarity_score if similarity_score is not None else 0.0,
                success=similarity_score is not None,
                error=None if similarity_score is not None else "Embedding failed",
                method="embed"
            ))
            
        except Exception as e:
            logger.error(f"Embedding rating failed: {e}",exc_info=True)
            results.append(RateResult(
                score=0.0,
                success=False,
                error=str(e),
                method="embed"
            ))
    logger.info(f"Embedding rating completed: {len([r for r in results if r.success])} successful, {len([r for r in results if not r.success])} failed")
    
    return results

def rate_llm(parsed_contents: List[str], config: RaterConfig, batch_config: Optional[BatchConfig]=None) -> List[RateResult]:
    """Rate multiple papers using batch processing when configured"""
    logger.info(f"Starting LLM-based rating for {len(parsed_contents)} papers (batch={getattr(config.llm, 'batch', False)})")
    if not getattr(config.llm, 'batch', False):
        client = RaterLLMClient(config.llm,batch_config)
        final_results = []
        for content in parsed_contents:
            token_count = count_tokens(content)
            result, usage_info = client._process_single_with_usage(content)
            final_results.append(
                RateResult(
                    score=result if result is not None else 0.0,
                    success=result is not None,
                    error=None if result is not None else "Single processing failed for this item.",
                    method="llm_single"
                )
            )
            if usage_info and (usage_info.prompt_tokens > 0 or usage_info.completion_tokens > 0):
                logger.info(f"Rated paper with {usage_info}")
            else:
                logger.info(f"Rated paper with {client.config.model} (usage info unavailable)")
        logger.info(f"LLM rating completed: {len([r for r in final_results if r.success])} successful")
        return final_results

    try:
        client = RaterLLMClient(config.llm, batch_config)
        results = client.process_batch(parsed_contents)

        final_results = [
            RateResult(
                score=result if result is not None else 0.0,
                success=result is not None,
                error=None if result is not None else "Batch processing failed for this item.",
                method="llm_batch"
            ) for result in results
        ]
        logger.info(f"LLM rating completed: {len([r for r in final_results if r.success])} successful")
        return final_results

    except Exception as e:
        logger.error(f"LLM rating failed: {e}")
        return [
            RateResult(
                score=0.0,
                success=False,
                error=str(e),
                method="llm_batch"
            )
        ]

if __name__ == "__main__":
    import os
    llm_config = RaterLLMConfig(
            provider="siliconflow",
            api_key=os.getenv("SILICONFLOW_API_KEY"),
            base_url="https://api.siliconflow.cn/v1",
            model="THUDM/GLM-4-9B-0414",
            batch=False,
            system_prompt="You are an expert research paper evaluator.",
            user_prompt_template="""Please evaluate this research paper based on the following criteria:

{criteria_text}

Rate each criterion on a scale of 1-10 where:
- 1-3: Poor/Below average
- 4-6: Average/Adequate  
- 7-8: Good/Above average
- 9-10: Excellent/Outstanding

Paper content:
{paper_text}

Provide your response as a single JSON object. The keys of the object should be the criteria names. For each criterion, provide a nested JSON object with "score" (a numerical rating from 1-10) and "justification" (a brief explanation for the score).
For example:
{
  "novelty": {
    "score": 8,
    "justification": "The use of self-attention mechanism was novel for translation tasks."
  },
  "clarity": {
    "score": 9,
    "justification": "The paper is exceptionally well-written and easy to follow."
  }
}""",
            completion_options={},
            context_length=32768,
            criteria={
                "novelty": 
                {"description": "How original and innovative are the contributions?", "weight": 0.6},
                "clarity": 
                {"description": "How well-written and understandable is the paper?", "weight": 0.4}
            }
        )
    batch_config = BatchConfig(
        tmp_dir="./tmp",
        max_wait_hours=24,
        poll_interval_seconds=24,
        fallback_on_error=True
    )
    client = RaterLLMClient(llm_config, batch_config)

    #score = client._parse_response(response_content)
    #print(score)
