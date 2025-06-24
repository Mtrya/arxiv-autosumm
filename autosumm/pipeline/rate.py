"""
Rate fetched papers with a coarse-to-fine strategy.
"""

import numpy as np
import requests
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Union, Tuple, Any
from pathlib import Path
from json_repair import repair_json

try:
    from client import BaseClient, BatchConfig, count_tokens, truncate_to_tokens
except:
    from .client import BaseClient, BatchConfig, count_tokens, truncate_to_tokens

@dataclass
class RaterEmbedderConfig:
    provider: str
    api_key: Optional[str]
    base_url: str
    model: str
    query_template: str
    user_interests: str
    context_length: Optional[int]=None

@dataclass
class RaterLLMConfig:
    provider: str
    api_key: Optional[str]
    base_url: str
    model: str
    batch: bool
    system_prompt: str
    user_prompt_template: str
    completion_options: Dict[str,Any]
    context_length: Optional[int]
    criteria: Dict[str,Dict[str,Union[str,float]]]

@dataclass
class RaterConfig:
    top_k: int
    embedder: RaterEmbedderConfig
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

class EmbedderClient:
    """OpenAI-compatible embedding client with context length management."""
    def __init__(self, config: RaterEmbedderConfig):
        self.config = config
        self.context_length = config.context_length or 32768
        self.query_embedding = self.create_query_embedding()

    def _chunk_text(self, text: str) -> List[Tuple[str,int]]:
        """Split text into chunks that fit within embedder's token limit"""
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = count_tokens(sentence)

            if sentence_tokens > self.context_length: # single sentence exceeds limit? truncate it
                truncated = truncate_to_tokens(sentence, self.context_length)
                if current_chunk:
                    chunks.append((current_chunk.strip(), current_tokens))
                chunks.append((truncated, self.context_length))
                current_chunk = ""
                current_tokens = 0
                continue

            if current_tokens + sentence_tokens > self.context_length: # if add this sentence would exceed limit, start a new chunk
                if current_chunk:
                    chunks.append((current_chunk.strip(),current_tokens))
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                current_chunk += (". " if current_chunk else "") + sentence
                current_tokens += sentence_tokens

        if current_chunk:
            chunks.append((current_chunk.strip(), current_tokens))

        return chunks
    
    def _make_request(self, texts: List[str]) -> List[List[float]]:
        """Make embedding request to API."""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        if "ollama" in self.config.provider.lower():
            endpoint = f"{self.config.base_url.rstrip('/')}/api/embeddings"
            payload = {
                "model": self.config.model,
                "prompt": texts[0] if len(texts) == 1 else texts
            }
        else:
            endpoint = f"{self.config.base_url.rstrip('/')}/embeddings"
            payload = {
                "model": self.config.model,
                "input": texts
            }

        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()

        if "ollama" in self.config.provider.lower():
            if isinstance(result.get("embedding"),list):
                return [result["embedding"]]
            else:
                return result.get("embeddings",[])
        else:
            return [item["embedding"] for item in result["data"]]
        
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for texts, handling chunking when needed"""
        embeddings = []
        
        for text in texts:
            embedding = self._make_request([text])[0]
            embeddings.append(embedding)

        return embeddings
    
    def create_query_embedding(self) -> List[float]:
        query = self.config.query_template.format(user_interests=self.config.user_interests)
        return self.get_embeddings([query])[0]
    
    def get_cosine_similarity(self, text: str) -> float:
        """
        Get cosine similarity while handling text processing for different context length.
        """
        chunks = self._chunk_text(text)
        texts = [chunk[0] for chunk in chunks]
        lengths = [chunk[1] for chunk in chunks]
        embeddings = self.get_embeddings(texts)
        similarity = sum([len*cosine_similarity(emb, self.query_embedding) for len,emb in zip(lengths,embeddings)])
        return similarity/sum(lengths)
    
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
        if "ollama" in self.config.provider.lower():
            return f"{self.config.base_url.rstrip('/')}/api/chat"
        else:
            return f"{self.config.base_url.rstrip('/')}/chat/completions"
        
    def _parse_response(self, response_content) -> float:
        response = repair_json(response_content)
        response = response.replace('```jons','').replace('```','').strip()
        ratings_data = json.loads(response)

        required_keys = {"ratings", "justifications"}
        if not all(key in ratings_data for key in required_keys):
            return 0.0
        
        weighted_sum = 0.0
        total_weight = 0.0

        for criterion, details in self.config.criteria.items():
            if criterion in ratings_data['ratings']:
                score = float(ratings_data['ratings'][criterion])
                weight = details['weight']
                weighted_sum += weight*score
                total_weight += weight

        if total_weight > 0:
            final_score = weighted_sum / total_weight
        else:
            final_score = 0.0
        
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

        
def rate_embed(parsed_contents: List[str], config: RaterConfig) -> List[RateResult]:
    """Rate paper using embedding similarity"""
    
    embedder_client = EmbedderClient(config.embedder)
    results = []

    for content in parsed_contents:
        try:
            similarity_score = embedder_client.get_cosine_similarity(content)

            results.append(RateResult(
                score=similarity_score,
                success=True,
                error="",
                method="embed"
            ))
        except Exception as e:
            results.append(RateResult(
                score=0.0,
                success=False,
                error=str(e),
                method="embed"
            ))

    return results

def rate_llm(parsed_contents: List[str], config: RaterConfig, batch_config: Optional[BatchConfig]=None) -> List[RateResult]:
    """Rate multiple papers using batch processing when configured"""
    if not getattr(config, 'batch', False):
        client = RaterLLMClient(config.llm,batch_config)
        results = [client.process_single(content) for content in parsed_contents]
        return [
            RateResult(
                score=result or 0.0,
                success=result is not None,
                error=None if result is not None else "Single processing failed for this item.",
                method="llm_single"
            ) for result in results
        ]

    try:
        client = RaterLLMClient(config.llm, batch_config)
        results = client.process_batch(parsed_contents)

        return [
            RateResult(
                score=result or 0.0,
                success=result is not None,
                error=None if result is not None else "Batch processing failed for this item.",
                method="llm_batch"
            ) for result in results
        ]

    except Exception as e:
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
    embedder_config = RaterEmbedderConfig(
        provider="ollama",
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        base_url="http://localhost:11434",
        model="dengcao/Qwen3-Embedding-8B:Q5_K_M",
        query_template="Hight-quality {user_interests} research paper with novel contributions, rigorous methodology, clear presentation, and significant impact",
        user_interests="AI, machine learning or astronomy",
    )

    llm_config = RaterLLMConfig(
        provider="ollama",
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        base_url="http://localhost:11434",
        model="qwen2.5:3b",
        batch=False,
        system_prompt="""You are an expert research paper reviewer with deep knowledge in computer science, AI, and machine learning. Your task is to evaluate research papers based on multiple criteria and provide structured ratings.

You must respond with a valid JSON object containing:
1. "ratings": A dictionary with numerical scores (1-10) for each criterion
2. "justifications": A dictionary with brief explanations for each rating

Be objective, concise, and focus on the paper's technical merit. Consider the paper's contributions within its specific domain.""",
        user_prompt_template="""Please evaluate this research paper based on the following criteria:

{criteria_text}

Rate each criterion on a scale of 1-10 where:
- 1-3: Poor/Below average
- 4-6: Average/Adequate  
- 7-8: Good/Above average
- 9-10: Excellent/Outstanding

Paper content:
{paper_text}

Provide your response as a JSON object with "ratings" and "justifications" fields where "ratings" field include rating from each criterion and "justification" field include corresponding justification.""",
    completion_options={
        "temperature": 0.2,
        "max_tokens": 1024
    },
    context_length=32768,
    criteria={
        "novelty": {
            "description": "How original and innovative are the contributions?",
            "weight": 0.3
        },
        "methodology": {
            "description": "How rigorous is the experimental design and evaluation?",
            "weight": 0.25
        },
        "clarity": {
            "description": "How well-written and understandable is the paper?",
            "weight": 0.2
        },
        "impact": {
            "description": "How significant are the potential applications and impact?",
            "weight": 0.15
        },
        "relevance": {
            "description": "How well does this paper match the user's research interests of AI, machine learning and astronomy?",
            "weight": 0.1
        }
    }
    )

    rate_config = RaterConfig(
        top_k=200,
        embedder=embedder_config,
        llm=llm_config
    )

    from parse import parse_fast, ParseConfig
    config = ParseConfig()

    pdf_url = "http://arxiv.org/pdf/1706.03762"
    parsed_content = parse_fast(pdf_url, config).content
    
    embed_result = rate_embed([parsed_content], rate_config)[0]
    print(f"Embedding similarity score: {embed_result.score:.3f}")
    print(f"Success: {embed_result.success}")
    if not embed_result.success:
        print(f"Error: {embed_result.error}")

    # Rate using LLM
    llm_result = rate_llm([parsed_content], rate_config)[0]
    print(f"\nLLM weighted score: {llm_result.score:.3f}")
    print(f"Success: {llm_result.success}")
    print(f"Error: {llm_result.error}")

