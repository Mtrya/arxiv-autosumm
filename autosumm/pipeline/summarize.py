"""
Summarize parsed papers using LLM
"""

from dataclasses import dataclass
import time
from typing import Optional, Dict, Any, List

try:
    from client import BaseClient, BatchConfig, count_tokens, truncate_to_tokens
except:
    from .client import BaseClient, BatchConfig, count_tokens, truncate_to_tokens

@dataclass
class SummarizerConfig:
    provider: str
    api_key: Optional[str]
    base_url: str
    model: str
    batch: bool
    system_prompt: Optional[str]
    user_prompt_template: Optional[str]
    completion_options: Dict[str,Any]
    context_length: Optional[int]

@dataclass
class SummaryResult:
    content: str
    success: bool
    error: Optional[str]=None

class SummarizerClient(BaseClient):
    def __init__(self, config: SummarizerConfig, batch_config: Optional[BatchConfig]=None):
        super().__init__(config, batch_config)
        # estimate available context
        prompt_tokens = 0
        if config.system_prompt:
            prompt_tokens += count_tokens(config.system_prompt)
        if config.user_prompt_template:
            prompt_tokens += count_tokens(config.user_prompt_template)
        safety_margin = 128
        output_tokens = config.completion_options.get('max_tokens', 8192)
        base_context = config.context_length or 65536
        self.available_context = base_context - prompt_tokens - output_tokens - safety_margin
    
    def _build_payload(self, parsed_content: str) -> dict:
        """Build API payload for summarization request."""
        # Truncate content if needed
        token_count = count_tokens(parsed_content)
        if token_count > self.available_context:
            parsed_content = truncate_to_tokens(parsed_content, self.available_context)
        
        messages = self._create_messages(parsed_content)
        
        base_payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": True  # Hardcoded streaming for non-batch
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
        if "ollama" in self.config.provider.lower():
            return f"{self.config.base_url.rstrip('/')}/api/chat"
        else:
            return f"{self.config.base_url.rstrip('/')}/chat/completions"
        
    def _create_messages(self, parsed_content: str) -> list:
        """Create message list."""
        messages = []
        
        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})
        
        if self.config.user_prompt_template:
            user_content = self.config.user_prompt_template.format(paper_content=parsed_content)
        else:
            user_content = parsed_content
            
        messages.append({"role": "user", "content": user_content})
        return messages

def summarize(parsed_contents: List[str], config: SummarizerConfig, batch_config: Optional[BatchConfig] = None) -> List[SummaryResult]:
    """Summarize multiple papers using batch processing when possible."""
    if not getattr(config, 'batch', False):
        # If batch is disabled, process sequentially
        client = SummarizerClient(config, batch_config)
        results = [client.process_single(content) for content in parsed_contents]
        return [
            SummaryResult(
                content=result or "",
                success=result is not None,
                error=None if result is not None else "Single processing failed for this item"
            ) for result in results
        ]
    
    try:
        client = SummarizerClient(config, batch_config)
        results = client.process_batch(parsed_contents)
        
        return [
            SummaryResult(
                content=result or "",
                success=result is not None,
                error=None if result is not None else "Batch processing failed for this item",
            ) for result in results
        ]
        
    except Exception as e:
        return [
            SummaryResult(
                content="",
                success=False,
                error=str(e),
            )
            for _ in parsed_contents
        ]
        
if __name__ == "__main__":
    # Example usage with default prompts
    default_system_prompt = """You are an expert research assistant specializing in academic paper analysis. Your task is to create concise, comprehensive summaries of research papers that capture the key contributions, methodology, and significance while remaining accessible to researchers in related fields."""

    default_user_template = """Please provide a structured summary of the following research paper. Focus on:

1. **Main Contribution**: What is the primary novel contribution or finding?
2. **Methodology**: What approach or techniques were used?
3. **Key Results**: What are the most important results or findings?
4. **Significance**: Why is this work important and what are its implications?

Keep the summary concise but comprehensive, suitable for researchers who want to quickly understand the paper's value and relevance.

Paper content:
{paper_content}

Summary:"""
    import os
    config = SummarizerConfig(
        provider="siliconflow",
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        #base_url="http://localhost:11434",
        base_url="https://api.siliconflow.cn/v1",
        #model="qwen3:8b",
        model="THUDM/GLM-4-9B-0414",
        batch=True,
        system_prompt=default_system_prompt,
        user_prompt_template=default_user_template,
        completion_options={
            "temperature": 0.6,
            "max_tokens": 4096,
            "top_p": 0.9
        },
        context_length=32768
    )

    batch_config = BatchConfig()

    # Test with sample content
    sample_content = """This is a sample research paper about machine learning. The paper introduces a new neural network architecture that achieves state-of-the-art results on image classification tasks. The methodology involves a novel attention mechanism that improves feature extraction. Experiments on ImageNet show 2% improvement over previous best results."""

    result = summarize([sample_content], config,batch_config)[0]
    
    if result.success:
        print("Summary generated successfully:")
        print(result.content)
    else:
        print(f"Summary failed: {result.error}")