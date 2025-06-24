"""Pydantic models with basic validations"""

from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, Union
import os

import pipeline

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
    "Dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "DeepSeek": "https://api.deepseek.com/v1",
    "Ollama": "http://localhost:11434",
    "OpenAI": "https://api.openai.com/v1",
    "MiniMax": "https://api.minimaxi.com/v1/text/chatcompletion_v2",
    "Moonshot": "https://api.moonshot.cn/v1",
    "SiliconFlow": "https://api.siliconflow.cn/v1",
    "VolcEngine": "https://ark.cn-beijing.volces.com/api/v3"
}

valid_options = {
    "frequency_penalty": (-2,2),
    "max_tokens": (1,None),
    "presence_penalty": (-2,2),
    "stop": (None, None), # No validation for stop
    "temperature": (0,2),
    "top_p": (0,1),
    "top_k": (0,1),
    "top_logprobs": (0,5)
}


class RuntimeConfig(BaseModel):
    texlive_root: str
    docker_mount_cache: str
    docker_mount_output: str

class RunConfig(BaseModel):
    schedule: str
    autostart: bool
    categories: Dict[str]

class FetcherConfig(BaseModel):
    category: str
    days: Optional[int]=8
    max_results: Optional[int]=1000
    max_retries: Optional[int]=10

    @field_validator('category')
    @classmethod
    def validate_category(cls, v) -> str:
        if v not in arxiv_categories:
            raise ValueError("category must be a valid arXiv category")
        return v

    @field_validator('days')
    @classmethod
    def validate_days(cls, v) -> int:
        return max(1,min(v,100)) if v is not None else 8

    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v) -> int:
        return max(1,min(v,1000)) if v is not None else 1000
    
    @field_validator('max_retries')
    @classmethod
    def validate_max_retries(cls,v) -> int:
        return max(1,min(v,100)) if v is not None else 5
    
    def to_pipeline_config(self) -> pipeline.FetcherConfig:
        return pipeline.FetcherConfig(
            category=self.category,
            days=self.days,
            max_results=self.max_results,
            max_retries=self.max_retries
        )

class SummarizerConfig(BaseModel):
    provider: Optional[str]
    api_key: Optional[str]
    base_url: Optional[str]
    model: str
    batch: Optional[bool]=False
    system_prompt: Optional[str]=None
    user_prompt_template: str
    completion_options: Optional[Dict[str,Any]]=None
    context_length: Optional[int]=65536

    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v, info) -> str:
        if not v and not info.data.get('base_url'):
            raise ValueError("Either provider of base_url must be specified")
        if v and not info.data.get('base_url') and v not in recognized_providers:
            raise ValueError(f"Provider must be one of: {list(recognized_providers.keys())} if base_url is not provided.")
        return v

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v, info) -> str:
        if v and v.startswith('env:'):
            env_var = v[4:]
            v = os.getenv(env_var)
            if not v:
                raise ValueError(f"Environment variable {env_var} not found")
        
        provider = info.data.get('provider')
        base_url = info.data.get('base_url')

        if not v and provider != 'Ollama' and not (base_url and base_url.startswith('http://localhost')):
            raise ValueError("api_key is required for non-local providers")
        
        return v

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v, info) -> str:
        """
        if provider is given and is in recognized_providers, then base_url is not required
        """
        provider = info.data.get('provider')
        if not v and provider not in recognized_providers:
            return recognized_providers[provider]
        return v
    
    @field_validator('system_prompt')
    @classmethod
    def validate_system_prompt(cls, v) -> str:
        if v is None:
            return ""
        if v.startswith("file:"):
            filepath = v[5:]
            try:
                with open(filepath, 'r') as f:
                    return f.read()
            except Exception as e:
                raise ValueError(f"Failed to load system prompt file in {filepath}: {e}")
        return v
    
    @field_validator('user_prompt_template')
    @classmethod
    def validate_user_prompt_template(cls, v) -> str:
        return cls.validate_system_prompt(v)

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
        return max(512,v)
    
    def to_pipeline_config(self) -> pipeline.SummarizerConfig:
        return pipeline.SummarizerConfig(
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
    provider: Optional[str]
    api_key: Optional[str]
    base_url: Optional[str]
    model: str
    query_template: str
    user_interests: Optional[str]=None
    context_length: Optional[int]=2048

    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v, info) -> str:
        if not v and not info.data.get('base_url'):
            raise ValueError("Either provider of base_url must be specified")
        if v and not info.data.get('base_url') and v not in recognized_providers:
            raise ValueError(f"Provider must be one of: {list(recognized_providers.keys())} if base_url is not provided.")
        return v

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v, info) -> str:
        if v and v.startswith('env:'):
            env_var = v[4:]
            v = os.getenv(env_var)
            if not v:
                raise ValueError(f"Environment variable {env_var} not found")
        
        provider = info.data.get('provider')
        base_url = info.data.get('base_url')

        if not v and provider != 'Ollama' and not (base_url and base_url.startswith('http://localhost')):
            raise ValueError("api_key is required for non-local providers")
        
        return v

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v, info) -> str:
        """
        if provider is given and is in recognized_providers, then base_url is not required
        """
        provider = info.data.get('provider')
        if not v and provider not in recognized_providers:
            return recognized_providers[provider]
        return v

    @field_validator('query_template')
    @classmethod
    def validate_query_template(cls, v):
        pass

class RaterLLMConfig(BaseModel):
    provider: Optional[str]
    api_key: Optional[str]
    base_url: Optional[str]
    model: str
    batch: Optional[bool]=False
    system_prompt: Optional[str]=None
    user_prompt_template: str
    completion_options: Optional[Dict[str,Any]]=None
    context_length: Optional[int]=65536
    criteria: Dict[str,Dict[str,Union[str,float]]]

class RaterConfig(BaseModel):
    top_k: Optional[int]=200
    embedder: Optional[RaterEmbedderConfig]
    llm: Optional[RaterLLMConfig]

class ParserVLMConfig(BaseModel):
    provider: Optional[str]
    api_key: Optional[str]
    base_url: Optional[str]
    model: str
    batch: Optional[bool]=False
    system_prompt: Optional[str]=None
    user_prompt: str
    dpi: Optional[int]=168

class ParserConfig(BaseModel):
    enable_vlm: Optional[bool]=False
    tmp_dir: Optional[str]="./tmp"
    vlm: Optional[ParserVLMConfig]

class BatchConfig(BaseModel):
    tmp_dir: Optional[str]="./tmp"
    max_wait_hours: Optional[int]=24
    poll_interval_seconds: Optional[int]=30
    fallback_on_error: Optional[bool]=True

class CacherConfig(BaseModel):
    dir: Optional[str]="~/.cache/arxiv-autosumm"
    ttl_days: Optional[int]=16

class RendererConfig:
    formats: str

class DelivererConfig:
    smtp_server: str
    port: int 
    sender: str
    recipient: str
    password: str

class MainConfig:
    runtime: RuntimeConfig
    run: RunConfig
    fetch: FetcherConfig
    summarize: SummarizerConfig
    rate: RaterConfig
    parse: ParserConfig
    batch: Optional[BatchConfig]
    cache: Optional[CacherConfig]
    render: RendererConfig
    deliver: DelivererConfig





    
