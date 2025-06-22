"""
Rate fetched papers with a coarse-to-fine strategy.
"""

import asyncio
import numpy as np
import tiktoken
import requests
import json
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Union, Tuple, Any
from abc import ABC, abstractmethod
from pathlib import Path
from json_repair import repair_json

try:
    from client import BaseClient, BatchConfig, count_tokens, truncate_to_tokens
except:
    from .client import BaseClient, BatchConfig, count_tokens, truncate_to_tokens

@dataclass
class EmbedderConfig:
    provider: str
    api_key: Optional[str]
    base_url: str
    model: str
    query_template: str
    user_interests: str
    context_length: Optional[int]=None

@dataclass
class LLMConfig:
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
class RateConfig:
    top_k: int
    embedder: EmbedderConfig
    llm: Optional[LLMConfig]

@dataclass
class RateResult:
    score: float
    success: bool
    error: Optional[str]
    method: str="embed"
    metadata: Optional[Dict]=None # LLM justifications

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
    def __init__(self, config: EmbedderConfig):
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
    
class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        
        prompt_tokens = 0
        if config.system_prompt:
            prompt_tokens += count_tokens(config.system_prompt)
        if config.user_prompt_template:
            prompt_tokens += count_tokens(config.user_prompt_template)
        output_tokens = config.completion_options.get('max_tokens',256)
        
        base_context = config.context_length or 65536
        self.available_length = base_context - prompt_tokens - output_tokens

    def _create_rating_prompt(self, parsed_content: str) -> str:
        """Create prompt for rating a paper based on configured criteria"""
        criteria_descriptions = []
        for criterion, details in self.config.criteria.items():
            criteria_descriptions.append(f"- {criterion}: {details['description']}")

        criteria_text = "\n".join(criteria_descriptions)

        user_prompt = self.config.user_prompt_template.format(criteria_text=criteria_text,paper_text=parsed_content)
    
        return user_prompt
    
    def _make_request(self, user_prompt: str) -> str:
        """Make rating request to LLM API"""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        if "ollama" in self.config.provider.lower():
            endpoint = f"{self.config.base_url.rstrip('/')}/api/chat"
            options = self.config.completion_options.copy()
            if 'max_tokens' in options:
                options['num_predict'] = options.pop('max_tokens')
            payload = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": self.config.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "options": options,
                "stream": False
            }
        else:
            endpoint = f"{self.config.base_url.rstrip('/')}/chat/completions"
            payload = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": self.config.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            }
            payload.update(self.config.completion_options)

        response = requests.post(endpoint, headers=headers,json=payload)
        response.raise_for_status()

        result = response.json()

        if "ollama" in self.config.provider:
            return result["message"]["content"]
        else:
            return result["choices"][0]["message"]["content"]
        
    def rate_paper(self, parsed_content: str) -> Tuple[float, Optional[Dict]]:
        """Rate a single paper and return weighted score."""
        token_count = count_tokens(parsed_content)
        if token_count > self.available_context:
            parsed_content = truncate_to_tokens(parsed_content, self.available_context)

        user_prompt = self._create_rating_prompt(parsed_content)

        response = self._make_request(user_prompt)

        response = repair_json(response)
        
        # Clean up response (remove code blocks, etc.)
        response = response.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON response
        ratings_data = json.loads(response)
        
        # Validate required keys
        required_keys = {"ratings", "justifications"}
        if not all(key in ratings_data for key in required_keys):
            return 0.0, {"error": "Missing keys in ratings data"}
        
        # Calculate weighted score
        weighted_sum = 0.0
        total_weight = 0.0
        
        for criterion, details in self.config.criteria.items():
            if criterion in ratings_data['ratings']:
                score = float(ratings_data['ratings'][criterion])
                weight = details['weight']
                weighted_sum += weight * score
                total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            final_score = weighted_sum / total_weight
        else:
            final_score = 0.0
        
        return final_score, ratings_data
            
        """except json.JSONDecodeError as e:
            return 0.0, {"error": f"Invalid JSON format: {str(e)}"}
        except Exception as e:
            return 0.0, {"error": f"Rating failed: {str(e)}"}"""

def rate_embed(parsed_contents: List[str], config: RateConfig) -> List[RateResult]:
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

def rate_llm(parsed_content: str, config: RateConfig) -> RateResult:
    """Rate paper using LLM with structured criteria"""
    if config.llm is None:
        return RateResult(
            score=0.0,
            success=False,
            error="LLM config not provided",
            method="llm"
        )
    
    
    llm_client = LLMClient(config.llm)
    weighted_score, ratings_data = llm_client.rate_paper(parsed_content)
    
    # Check if rating failed (score 0.0 with error in metadata)
    if weighted_score == 0.0 and isinstance(ratings_data, dict) and "error" in ratings_data:
        return RateResult(
            score=0.0,
            success=False,
            error=ratings_data["error"],
            method="llm"
        )
    
    return RateResult(
        score=weighted_score,
        success=True,
        method="llm",
        error="",
        metadata=ratings_data
    )
        
    """except Exception as e:
        return RateResult(
            score=0.0,
            success=False,
            error=str(e),
            method="llm"
        )"""

if __name__ == "__main__":
    import os
    embedder_config = EmbedderConfig(
        provider="ollama",
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        base_url="http://localhost:11434",
        model="dengcao/Qwen3-Embedding-8B:Q5_K_M",
        query_template="Hight-quality {user_interests} research paper with novel contributions, rigorous methodology, clear presentation, and significant impact",
        user_interests="AI, machine learning or astronomy",
    )

    llm_config = LLMConfig(
        provider="ollama",
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        base_url="http://localhost:11434",
        model="qwen3:8b",
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

Provide your response as a JSON object with "ratings" and "justifications" fields.""",
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

    rate_config = RateConfig(
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
    llm_result = rate_llm(parsed_content, rate_config)
    print(f"\nLLM weighted score: {llm_result.score:.3f}")
    print(f"Success: {llm_result.success}")
    print(f"Error: {llm_result.error}")

