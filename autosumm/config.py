"""Pydantic models with basic validations"""

from pydantic import BaseModel, field_validator, ConfigDict, model_validator
from typing import Optional, Dict, Any, Union, List
import yaml
from dotenv import main
import os
import re

from .pipeline import (
    FetcherConfig as FetcherConfig_,
    ParserConfig as ParserConfig_,
    ParserVLMConfig as ParserVLMConfig_,
    RaterConfig as RaterConfig_,
    RaterEmbedderConfig as RaterEmbedderConfig_,
    RaterLLMConfig as RaterLLMConfig_,
    SummarizerConfig as SummarizerConfig_,
    CacherConfig as CacherConfig_,
    BatchConfig as BatchConfig_,
    DelivererConfig as DelivererConfig_,
    RendererConfig as RendererConfig_,
    MarkdownRendererConfig as MarkdownRendererConfig_,
    PDFRendererConfig as PDFRendererConfig_,
    HTMLRendererConfig as HTMLRendererConfig_,
    AZW3RendererConfig as AZW3RendererConfig_
)

arxiv_categories = ["cs.AI","cs.AR","cs.CC","cs.CE","cs.CG","cs.CL","cs.CR","cs.CV","cs.CY","cs.DB","cs.DL",
                    "cs.DM","cs.DS","cs.ET","cs.FL","cs.GL","cs.GR","cs.GT","cs.HC","cs.IR","cs.IT","cs.LG",
                    "cs.LO","cs.MA","cs.MM","cs.MS","cs.NA","cs.NE","cs.NI","cs.OH","cs.OS","cs.PF","cs.PL",
                    "cs.RO","cs.SC","cs.SD","cs.SE","cs.SI","cs.SY","econ.EM","econ.GN","econ.TH","eess.AS",
                    "eess.IV","eess.SP","eess.SY","math.AC","math.AG","math.AP","math.AT","math.CA","math.CO",
                    "math.CT","math.CV","math.DG","math.DS","math.FA","math.GM","math.GN","math.GR","math.GT",
                    "math.HO","math.IT","math.KT","math.LO","math.MG","math.MP","math.NA","math.NT","math.OA",
                    "math.OC","math.PR","math.QA","math.RA","math.RT","math.SG","math.SP","math.ST","astro-ph.CO",
                    "astro-ph.EP","astro-ph.GA","astro-ph.HE","astro-ph.IM","astro-ph.SR","cond-mat.dis-nn",
                    "cond-mat.mtrl-sci","cond-mat.other","cond-mat.quant-gas","cond-mat.soft","cond-mat.stat-mech",
                    "cond-mat.str-el","cond-mat.supr-con","gr-qc","hep-ex","hep-lat","hep-ph","hep-th","math-ph",
                    "nlin.AO","nlin.CD","nlin.CG","nlin.PS","nlin.SI","nucl-ex","nucl-th","physics.acc-ph",
                    "physics.app-ph","physics.atm-clus","physics.atom-ph","physics.bio-ph","physics.chem-ph",
                    "physics.class-ph","physics.comp-ph","physics.data-an","physics.ed-ph","physics.gen-ph",
                    "physics.geo-ph","physics.hist-ph","physics.ins-det","physics.med-ph","physics-optics",
                    "physics.plasm-ph","physics.pop-ph","physics.soc-ph","physics.space-ph","quant-ph","q-bio.BM",
                    "q-bio.CB","q-bio.GN","q-bio.MN","q-bio.NC","q-bio.OT","q-bio.QM","q-bio.SC","q-bio.TO",
                    "q-fin.CP","q-fin.EC","q-fin.GN","q-fin.MF","q-fin.PM","q-fin.PR","q-fin.RM","q-fin.ST",
                    "q-fin.TR","stat.AP","stat.CO","stat.ME","stat.ML","stat.OT","stat.TH"]

recognized_providers = {
    "anthrocic": {
        "base_url": "https://api.anthropic.com",
        "default_summarizer": "claude-opus-4-0",
        "default_rater": "claude-3-5-haiku-latest"
    },
    "cohere": {
        "base_url": "https://api.cohere.ai/v1",
        "default_summarizer": "command-r-plus",
        "default_rater": "command-r"
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_summarizer": "qwen-plus",
        "default_rater": "qwen-turbo"
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_summarizer": "deepseek-reasoner",
        "default_rater": "deepseek-chat"
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_summarizer": "gemini-2.5-pro",
        "default_rater": "gemini-2.5-flash"
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_summarizer": "llama-3.1-70b-versatile",
        "default_rater": "llama-3.1-8b-instant"
    },
    "minimax": {
        "base_url": "https://api.minimax.chat/v1",
        "default_summarizer": "MiniMax-M1",
        "default_rater": "MiniMax-Text-01"
    },
    "modelscope": {
        "base_url": "https://api-inference.modelscope.cn/v1",
        "default_summarizer": "Qwen/Qwen3-235B-A22B-Thinking-2507",
        "default_rater": "Qwen/Qwen2.5-7B-Instruct"
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "default_summarizer": "kimi-k2-0711-preview",
        "default_rater": "kimi-latest"
    },
    "ollama": {
        "base_url": "https://localhost:11434",
        "default_summarizer": "qwen3:32b",
        "default_rater": "llama3.1:8b"
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_summarizer": "gpt-4o",
        "default_rater": "gpt-4o-mini"
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_summarizer": "google/gemini-2.5-pro",
        "default_rater": "google/gemini-2.5-flash-lite"
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "default_summarizer": "deepseek-ai/DeepSeek-R1",
        "default_rater": "THUDM/glm-4-9b-chat"
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "default_summarizer": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "default_rater": "meta-llama/Meta-Llama-3.1-8B-Instruct"
    },
    "volcengine": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_summarizer": "doubao-seed-1-6-thinking-250715",
        "default_rater": "doubao-seed-1-6-flash-250715"
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_summarizer": "glm-4.5",
        "default_rater": "glm-4.5-flash"
    }
}

valid_options = {
    "frequency_penalty": (-2.0,2.0),
    "max_tokens": (1,None),
    "presence_penalty": (-2,2),
    "stop": (None, None), # No validation for stop
    "temperature": (0.0,2.0),
    "top_p": (0.0,1.0),
    "top_k": (1,None),
    "top_logprobs": (0,5)
}

def validate_api_config(provider: Optional[str], base_url: Optional[str], api_key: Optional[str]) -> tuple[str, str, Optional[str]]:
    """
    Reusable API configuration validation function (most basic one, do not check connectivity).
    
    Returns:
        tuple: (provider, base_url, api_key) - all properly validated
    """
    
    # Normalize inputs
    provider = provider.lower() if provider else None
    base_url = base_url.strip() if base_url else None
    api_key = api_key.strip() if api_key else None
    
    # Rule 1: Auto-fill base_url from recognized providers if not provided
    if not base_url:
        if provider and provider in recognized_providers:
            base_url = recognized_providers[provider]["base_url"]
        elif not provider:
            # If neither provider nor base_url is given, this is an error
            raise ValueError("Either provider or base_url must be provided")
    
    # Rule 2: If base_url is provided but provider is not, use a placeholder
    if not provider and base_url:
        # Try to infer provider from base_url
        for known_provider, meta in recognized_providers.items():
            known_url = meta["base_url"]
            if base_url.rstrip('/') == known_url.rstrip('/'):
                provider = known_provider
                break
        else:
            provider = "custom"
    
    # Rule 3: Check if api_key is required
    is_local = (provider == "ollama" or 
                (base_url and base_url.startswith("http://localhost")) or
                (base_url and "localhost" in base_url))
    
    if not is_local and not api_key:
        raise ValueError(f"API key is required for provider '{provider}' with base_url '{base_url}'")
    
    # Ensure we have valid strings for provider and base_url
    if not provider:
        provider = "unknown"
    if not base_url:
        raise ValueError("Base URL cannot be empty after processing")
    
    return provider, base_url, api_key

class RunConfig(BaseModel):
    categories: List[str]
    send_log: bool=False
    log_dir: str="./logs"
    
    @field_validator('categories')
    @classmethod
    def validate_categories(cls, v) -> List[str]:
        if not v:
            raise ValueError("No category selected. Please select at least one category.")
        for category in v:
            if category not in arxiv_categories:
                raise ValueError(f"Invalid arXiv category: {category}")
        return v

class FetcherConfig(BaseModel):
    days: int=8
    max_results: int=1000
    max_retries: int=10

    @field_validator('days')
    @classmethod
    def validate_days(cls, v) -> int:
        return max(1,min(v,100))

    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v) -> int:
        return max(1,min(v,1000))
    
    @field_validator('max_retries')
    @classmethod
    def validate_max_retries(cls,v) -> int:
        return max(1,min(v,100))
    
    def to_pipeline_config(self) -> 'FetcherConfig_':
        return FetcherConfig_(
            days=self.days,
            max_results=self.max_results,
            max_retries=self.max_retries
        )

class SummarizerConfig(BaseModel):
    provider: Optional[str]=None
    api_key: Optional[str]=None
    base_url: Optional[str]=None
    model: str
    batch: bool=False
    system_prompt: Optional[str]=None
    user_prompt_template: str
    completion_options: Dict[str,Any]={"temperature": 0.6}
    context_length: int=98304

    @model_validator(mode='after')
    def validate_api_config(self) -> 'SummarizerConfig':
        """Validate API configuration using reusable function"""
        provider, base_url, api_key = validate_api_config(
            self.provider, self.base_url, self.api_key
        )
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key
        return self

    @field_validator('user_prompt_template')
    @classmethod
    def validate_user_prompt_template(cls, v) -> str:
        """must have {paper_content} placeholder"""
        if '{paper_content}' not in v:
            raise ValueError("user_prompt_template must contain '{paper_content}' placeholder")

        return v

    @field_validator('completion_options')
    @classmethod
    def validate_completion_options(cls, v) -> Dict[str,Any]:
        filtered = {}
        for key, value in v.items():
            if key in valid_options:
                min_val, max_val = valid_options[key]
                if min_val is not None and max_val is not None:
                    filtered[key] = max(min_val,min(value,max_val))
                else:
                    filtered[key] = value

        return filtered

    @field_validator('context_length')
    @classmethod
    def validate_context_length(cls, v) -> int:
        return max(3072,v)
    
    def to_pipeline_config(self) -> 'SummarizerConfig_':
        return SummarizerConfig_(
            provider=self.provider,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            batch=self.batch,
            system_prompt=self.system_prompt,
            user_prompt_template=self.user_prompt_template,
            completion_options=self.completion_options,
            context_length=self.context_length
        )
        
class RaterEmbedderConfig(BaseModel):
    provider: Optional[str]=None
    api_key: Optional[str]=None
    base_url: Optional[str]=None
    model: str
    query_template: str="High-quality {user_interests} research paper with novel contributions, rigorous methodology, clear presentation and significant impact."
    user_interests: Optional[str]=None
    context_length: int=2048

    @model_validator(mode='after')
    def validate_api_config(self) -> 'RaterEmbedderConfig':
        """Validate API configuration using reusable function"""
        provider, base_url, api_key = validate_api_config(
            self.provider, self.base_url, self.api_key
        )
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key
        return self

    @field_validator('query_template')
    @classmethod
    def validate_query_template(cls, v, info) -> int:
        if 'user_interests' not in info.data:
            return v
        if '{user_interests}' not in v:
            raise ValueError("Error initializing RaterEmbedderConfig: query_template must include '{user_interests}' placeholder if user_interests is given.")
        return v
    
    @field_validator('context_length')
    @classmethod
    def validate_context_length(cls, v) -> int:
        return max(512,v)
    
    def to_pipeline_config(self) -> 'RaterEmbedderConfig_':
        return RaterEmbedderConfig_(
            provider=self.provider,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            query_template=self.query_template,
            user_interests=self.user_interests,
            context_length=self.context_length
        )

class RaterLLMConfig(BaseModel):
    provider: Optional[str]=None
    api_key: Optional[str]=None
    base_url: Optional[str]=None
    model: str
    batch: bool=False
    system_prompt: Optional[str]=None
    user_prompt_template: str
    completion_options: Dict[str,Any]={"temperature": 0.2, "max_tokens": 1024}
    context_length: Optional[int]=65536
    criteria: Dict[str,Dict[str,Union[str,float]]]={"novelty": {"description": "How original and innovative are the contributions?", "weight": 0.3}, "clarity": {"description": "How well-written and understandable is the paper?", "weight": 0.2}}

    @model_validator(mode='after')
    def validate_api_config(self) -> 'RaterLLMConfig':
        """Validate API configuration using reusable function"""
        provider, base_url, api_key = validate_api_config(
            self.provider, self.base_url, self.api_key
        )
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key
        return self

    @field_validator('user_prompt_template')
    @classmethod
    def validate_user_prompt_template(cls, v) -> str:
        """
        if starts with 'file:', try to load from file;
        must contain '{paper_text}' and '{criteria_text}' placeholders
        """
        for placeholder in ['{paper_text}','{criteria_text}']:
            if placeholder not in v:
                raise ValueError(f"Error initializing RaterLLMConfig: user_prompt_template must contain '{placeholder}'")
        
        return v

    @field_validator('completion_options')
    @classmethod
    def validate_completion_options(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        filtered = {}
        for key, value in v.items():
            if key in valid_options:
                min_val, max_val = valid_options[key]
                if min_val is not None and max_val is not None:
                    filtered[key] = max(min_val, min(value, max_val))
                else:
                    filtered[key] = value
        return filtered

    @field_validator('context_length')
    @classmethod
    def validate_context_length(cls, v) -> int:
        return max(2048, v)
    
    def to_pipeline_config(self):
        return RaterLLMConfig_(
            provider=self.provider,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            batch=self.batch,
            system_prompt=self.system_prompt,
            user_prompt_template=self.user_prompt_template,
            completion_options=self.completion_options,
            context_length=self.context_length,
            criteria=self.criteria
        )

class RaterConfig(BaseModel):
    strategy: str="llm" # llm, embedder, hybrid
    top_k: int=0
    max_selected: int=8
    embedder: Optional[RaterEmbedderConfig]=None
    llm: Optional[RaterLLMConfig]=None
    """
    if top_k is 0, then RaterLLMConfig is not required; if top_k is 1000, then RaterEmbedderConfig is not required
    """

    @field_validator('strategy')
    @classmethod
    def validate_strategy(cls, v) -> str:
        if v not in ["llm", "embedder", "hybrid"]:
            return "llm"
        return v

    @field_validator('top_k')
    @classmethod
    def validate_top_k(cls, v) -> int:
        return max(0, min(v,1000))
    
    @field_validator('embedder')
    @classmethod
    def validate_embedder(cls, v, info):
        strategy = info.data.get('strategy', "llm")
        if strategy != "llm" and v is None:
            raise ValueError("embedder config required when using strategy 'embedder' or 'hybrid'. To use llm for rating entirely, set strategy to 'llm'")
        return v
    
    @field_validator('llm')
    @classmethod
    def validate_llm(cls, v, info):
        strategy = info.data.get('strategy',"llm")
        if strategy != "embedder" and v is None:
            raise ValueError("llm config required when using strategy 'llm' or 'hybrid'. To use embedder for rating entirely, set strategy to 'embedder'")
        return v
    
    def to_pipeline_config(self):
        return RaterConfig_(
            strategy=self.strategy,
            top_k=self.top_k,
            max_selected=self.max_selected,
            embedder=self.embedder.to_pipeline_config() if self.embedder else None,
            llm=self.llm.to_pipeline_config() if self.llm else None
        )

class ParserVLMConfig(BaseModel):
    provider: Optional[str]=None
    api_key: Optional[str]=None
    base_url: Optional[str]=None
    model: str
    batch: bool=False
    system_prompt: Optional[str]=None
    user_prompt: str
    completion_options: Dict[str,Any]={"temperature": 0.2}
    dpi: int=168
    
    @field_validator('completion_options')
    @classmethod
    def validate_completion_options(cls, v) -> Dict[str,Any]:
        filtered = {}
        for key, value in v.items():
            if key in valid_options:
                min_val, max_val = valid_options[key]
                if min_val is not None and max_val is not None:
                    filtered[key] = max(min_val,min(value,max_val))
                else:
                    filtered[key] = value

        return filtered

    @field_validator('dpi')
    @classmethod
    def validate_dpi(cls, v: int) -> int:
        return max(36, min(v, 400))
    
    @model_validator(mode='after')
    def validate_api_config(self) -> 'ParserVLMConfig':
        """Validate API configuration using reusable function"""
        provider, base_url, api_key = validate_api_config(
            self.provider, self.base_url, self.api_key
        )
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key
        return self
    
    def to_pipeline_config(self):
        return ParserVLMConfig_(
            provider=self.provider,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            batch=self.batch,
            system_prompt=self.system_prompt,
            user_prompt=self.user_prompt,
            completion_options=self.completion_options,
            dpi=self.dpi
        )

class ParserConfig(BaseModel):
    enable_vlm: bool=False
    tmp_dir: Optional[str]="./tmp"
    fast_parser_timeout_seconds: int=224
    vlm: Optional[ParserVLMConfig]=None
    """If enable_vlm is False, then ParserVLMConfig is not required"""

    @field_validator('fast_parser_timeout_seconds')
    @classmethod
    def validate_timeout(cls, v) -> int:
        return max(10,min(v,3600))

    @field_validator('vlm')
    @classmethod
    def validate_vlm_required(cls, v: Optional[ParserVLMConfig], info):
        enable_vlm = info.data.get('enable_vlm', False)
        if enable_vlm and v is None:
            raise ValueError("VLM configuration is required when enable_vlm is True. Please add the vlm section with provider, model, and API configuration under parse: in your config.yaml")
        return v
    
    def to_pipeline_config(self):
        return ParserConfig_(
            enable_vlm=self.enable_vlm,
            tmp_dir=self.tmp_dir,
            fast_parser_timeout_seconds=self.fast_parser_timeout_seconds,
            vlm=self.vlm.to_pipeline_config() if self.vlm else None
        )

class BatchConfig(BaseModel):
    tmp_dir: str="./tmp"
    max_wait_hours: int=24
    poll_interval_seconds: int=30
    fallback_on_error: bool=True

    def to_pipeline_config(self):
        return BatchConfig_(
            tmp_dir=self.tmp_dir,
            max_wait_hours=self.max_wait_hours,
            poll_intervall_seconds=self.poll_interval_seconds,
            fallback_on_error=self.fallback_on_error
        )

class CacherConfig(BaseModel):
    dir: str="./cache"
    ttl_days: int=16

    def to_pipeline_config(self):
        return CacherConfig_(
            dir=self.dir,
            ttl_days=self.ttl_days
        )

class MarkdownRendererConfig(BaseModel):
    include_pagebreaks: bool=True

    def to_pipeline_config(self):
        return MarkdownRendererConfig_(
            include_pagebreaks=self.include_pagebreaks
        )

class PDFRenderConfig(BaseModel):
    pdf_engine: str="xelatex"
    highlight_style: str="pygments"
    font_size: str="14pt"
    document_class: str="extarticle"
    margin: str="0.8in"
    colorlinks: bool=True
    link_color: str="RoyalBlue"
    line_stretch: float=1.10
    pandoc_input_format: str="markdown+raw_tex+yaml_metadata_block"
    pandoc_from_format: str="gfm"
    list_item_sep: str="0pt"
    list_par_sep: str="0pt"
    list_top_sep: str="6pt"

    def to_pipeline_config(self):
        return PDFRendererConfig_(
            pdf_engine=self.pdf_engine,
            highlight_style=self.highlight_style,
            font_size=self.font_size,
            document_class=self.document_class,
            margin=self.margin,
            colorlinks=self.colorlinks,
            link_color=self.link_color,
            line_stretch=self.line_stretch,
            pandoc_input_format=self.pandoc_input_format,
            pandoc_from_format=self.pandoc_from_format,
            list_item_sep=self.list_item_sep,
            list_par_sep=self.list_par_sep,
            list_top_sep=self.list_top_sep
        )

class HTMLRendererConfig(BaseModel):
    math_renderer: str="mathjax"
    mathjax_url: Optional[str]=None
    katex_url: Optional[str]=None
    include_toc: bool=True
    toc_depth: int=3
    number_sections: bool=False
    standalone: bool=True
    self_contained: bool=False
    css_file: Optional[str]=None
    css_inline: Optional[str]=None
    template_file: Optional[str]=None
    highlight_style: str="pygments"
    html5: bool=True

    def to_pipeline_config(self):
        return HTMLRendererConfig_(
            math_renderer=self.math_renderer,
            mathjax_url=self.mathjax_url,
            katex_url=self.katex_url,
            include_toc=self.include_toc,
            toc_depth=self.toc_depth,
            number_sections=self.number_sections,
            standalone=self.standalone,
            self_contained=self.self_contained,
            css_file=self.css_file,
            css_inline=self.css_inline,
            template_file=self.template_file,
            highlight_style=self.highlight_style,
            html5=self.html5
        )

class AZW3RendererConfig(BaseModel):
    calibre_path: Optional[str] = None  # Path to ebook-convert executable
    author: str = "ArXiv AutoSumm"
    title: Optional[str] = None
    language: str = "en"
    description: Optional[str] = None
    cover_image: Optional[str] = None
    
    def to_pipeline_config(self):
        return AZW3RendererConfig_(
            calibre_path=self.calibre_path,
            author=self.author,
            title=self.title,
            language=self.language,
            description=self.description,
            cover_image=self.cover_image
        )

class RendererConfig(BaseModel):
    formats: List[str]=["pdf","md"]
    output_dir: str
    base_filename: Optional[str]=None
    md: MarkdownRendererConfig=MarkdownRendererConfig()
    pdf: PDFRenderConfig=PDFRenderConfig()
    html: HTMLRendererConfig=HTMLRendererConfig()
    azw3: AZW3RendererConfig=AZW3RendererConfig()

    def to_pipeline_config(self):
        return RendererConfig_(
            formats=self.formats,
            output_dir=self.output_dir,
            base_filename=self.base_filename,
            md=self.md.to_pipeline_config() if self.md else MarkdownRendererConfig().to_pipeline_config(),
            pdf=self.pdf.to_pipeline_config() if self.pdf else PDFRenderConfig().to_pipeline_config(),
            html=self.html.to_pipeline_config() if self.html else HTMLRendererConfig().to_pipeline_config(),
            azw3=self.azw3.to_pipeline_config() if self.azw3 else AZW3RendererConfig().to_pipeline_config()
        )

class DelivererConfig(BaseModel):
    smtp_server: str
    sender: str
    recipient: str
    password: str
    port: int=465
    max_attachment_size_mb: float=25.0

    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("Port must be an integer between 1 and 65536.")
        return v
    
    @field_validator('sender','recipient')
    @classmethod
    def validate_email_addresses(cls, v: str) -> str:
        if '@' not in v or not re.match(r"[^@]+@[^@]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Email address format is invalid.")
        return v
    
    @field_validator('max_attachment_size_mb')
    @classmethod
    def validate_max_attachment_size_mb(cls, v: float) -> float:
        return max(0.1,v)
    
    def to_pipeline_config(self):
        return DelivererConfig_(
            smtp_server=self.smtp_server,
            port=self.port,
            sender=self.sender,
            recipient=self.recipient,
            password=self.password,
            max_attachment_size_mb=self.max_attachment_size_mb
        )


class MainConfig(BaseModel):
    model_config = ConfigDict(extra='forbid') # prevent unknown fields

    run: RunConfig
    fetch: FetcherConfig
    summarize: SummarizerConfig
    rate: RaterConfig
    parse: ParserConfig=ParserConfig()   
    batch: BatchConfig=BatchConfig()
    cache: CacherConfig=CacherConfig()
    render: RendererConfig
    deliver: DelivererConfig
    """If parse, batch or cache is not provided or is None, go with default settings."""

    @model_validator(mode="before")
    @classmethod
    def resolve_references(cls, data: Any) -> Any:
        """if isinstance(data, dict):
            try:
                return cls._resolve_references(data)
            except ValueError as e:
                # Wrap the low-level ValueError into a Pydantic ValidationError.
                # This allows the calling code to handle all configuration errors uniformly.
                raise ValidationError.from_exception_data(
                    title=cls.__name__,
                    line_errors=[
                        {
                            'type': 'value_error',
                            # The error message from _resolve_references now contains the
                            # full path, so we report it as a single, clear error message.
                            'loc': ('config',),
                            'msg': str(e) + " check if references ('env:', 'var:', '$', and 'file:') are correctly set",
                            'input': 'file: or env: reference',
                        }
                    ]
                )"""
        # Let ValueError bubble up naturally instead of trying to wrap it
        if isinstance(data, dict):
            return cls._resolve_references(data)
        return data

    @classmethod
    def from_yaml(cls, path: str) -> 'MainConfig':
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # model_validator is called automatically when the model is initialized
        #data = cls._resolve_references(data) 

        return cls(**data)

    @staticmethod
    def _resolve_references(data: Dict[str,Any]) -> Dict[str, Any]:
        """Recursively resolve 'file:path', 'env:variable', 'var:variable', and '$variable' references"""
        main.load_dotenv() # load .env file
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, str) and value.startswith('file:'):
                    filepath = value[5:]
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            result[key] = f.read()
                    except Exception as e:
                        raise ValueError(f"Failed to load file '{filepath}'. Reason: {e}")
                elif isinstance(value, str) and value.startswith('env:'):
                    envname = value[4:]
                    value = os.getenv(envname)
                    if value is None:
                        raise ValueError(f"Environment variable '{envname}' is not set or is empty. Please check your .env file or environment variables.")
                    else:
                        result[key] = value
                elif isinstance(value, str) and value.startswith('var:'):
                    # var: prefix for secrets (same as env: but semantically clearer for secrets)
                    envname = value[4:]
                    value = os.getenv(envname)
                    if value is None:
                        raise ValueError(f"Secret '{envname}' is not set or is empty. Please check your repository secrets or environment variables.")
                    else:
                        result[key] = value
                elif isinstance(value, str) and value.startswith('$'):
                    # $ prefix for bash-style environment variables
                    envname = value[1:]
                    value = os.getenv(envname)
                    if value is None:
                        raise ValueError(f"Environment variable '{envname}' is not set or is empty. Please check your .env file or environment variables.")
                    else:
                        result[key] = value
                else:
                    result[key] = MainConfig._resolve_references(value)
            return result
        elif isinstance(data, list):
            return [MainConfig._resolve_references(item) for item in data]
        else:
            return data
        
    def get_pipeline_configs(self) -> Dict[str, Any]:
        """Convert all configs to pipeline dataclasses"""
        return {
            "categories": self.run.categories,
            "send_log": self.run.send_log,
            "log_dir": self.run.log_dir,
            "fetch": self.fetch.to_pipeline_config(),
            "parse": self.parse.to_pipeline_config(),
            "rate": self.rate.to_pipeline_config(),
            "cache": self.cache.to_pipeline_config(),
            "summarize": self.summarize.to_pipeline_config(),
            "render": self.render.to_pipeline_config(),
            "deliver": self.deliver.to_pipeline_config(),
            "batch": self.batch.to_pipeline_config()
        }








    
