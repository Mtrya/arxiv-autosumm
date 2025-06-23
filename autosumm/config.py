from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, Union

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

class RuntimeConfig(BaseModel):
    texlive_root: str
    docker_mount_cache: str
    docker_mount_output: str

class RunConfig(BaseModel):
    schedule: str
    autostart: bool
    categories: Dict[str]

class FetchConfig(BaseModel):
    category: str
    days: int
    max_results: int
    max_retries: int

    @field_validator('category')
    @classmethod
    def validate_category(cls, v) -> str:
        if not isinstance(v, str):
            raise ValueError("category must be a string")
        if v not in arxiv_categories:
            raise ValueError("category must be a valid arXiv category")
        return v

    @field_validator('days')
    @classmethod
    def validate_days(cls, v) -> int:
        if not isinstance(v, int):
            raise ValueError("days must be an integer")
        if v <= 0:
            raise ValueError("days must be greater than 0")
        if v > 100:
            raise ValueError("days must be less than or equal to 100")
        return v

    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v) -> int:
        if not isinstance(v, int):
            raise ValueError("max_results must be an integer")
        if v <= 0:
            raise ValueError("max_results must be greater than 0")
        if v > 1000:
            raise ValueError("max_results must be less than or equal to 1000")
        return v
    
    @field_validator('max_retries')
    @classmethod
    def validate_max_retries(cls,v) -> int:
        if not isinstance(v, int):
            raise ValueError("max_retries must be an integer")
        if v <= 0:
            return 0
        return v

class SummarizerConfig(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str
    batch: bool
    system_prompt: str
    user_prompt_template: str
    completion_options: Dict[str,Any]
    context_length: int

class RaterEmbedderConfig(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str
    query_template: str
    user_interests: str
    context_length: int

class RaterLLMConfig(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str
    batch: bool
    system_prompt: str
    user_prompt_template: str
    completion_options: Dict[str,Any]
    context_length: int
    criteria: Dict[str,Dict[str,Union[str,float]]]

class RaterConfig(BaseModel):
    top_k: int
    embedder: RaterEmbedderConfig
    llm: RaterLLMConfig

class ParserVLMConfig(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str
    batch: bool
    system_prompt: str
    user_prompt: str
    dpi: int

class ParserConfig(BaseModel):
    enable_vlm: bool
    tmp_dir: str
    vlm: ParserVLMConfig

class BatchConfig(BaseModel):
    tmp_dir: str
    max_wait_hours: int
    poll_interval_seconds: int
    fallback_on_error: bool

class CacheConfig(BaseModel):
    dir: str
    ttl_days: int

class RenderConfig:
    formats: str

class DeliverConfig:
    smtp_server: str
    port: int 
    sender: str
    recipient: str
    password: str

class MainConfig:
    runtime: RuntimeConfig
    run: RunConfig
    fetch: FetchConfig
    summarizer: SummarizerConfig
    rater: RaterConfig
    parser: ParserConfig
    batch: BatchConfig
    cache: CacheConfig
    render: RenderConfig
    deliver: DeliverConfig





    
