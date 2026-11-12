from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CpuSpecs:
    model: str
    physical_cores: int
    logical_cores: int
    has_avx2: bool
    has_avx512: bool


@dataclass
class MemorySpecs:
    total_bytes: int
    total_gb: float
    available_gb: float


@dataclass
class GpuSpecs:
    name: str
    vram_total_gb: float
    vram_free_gb: float
    backend: str
    is_supported: bool


@dataclass
class HardwareProfile:
    tier: str
    cpu: CpuSpecs
    memory: MemorySpecs
    gpu: Optional[GpuSpecs]
    recommended_parallel: int
    recommended_context: int
    recommended_max_tokens: int
    recommended_loaded_models: int
    recommended_flash_attention: bool
    recommended_threads: int


@dataclass
class OllamaRuntimeConfig:
    num_parallel: int = 2
    num_ctx: int = 8192
    num_predict: int = 4096
    max_loaded_models: int = 2
    flash_attention: bool = True
    keep_alive: str = "24h"
    cpu_weight: int = 100
    nice: int = 0
    num_thread: int = 4
    max_queue: int = 512
    mode: str = "auto"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OllamaRuntimeConfig":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class OllamaDaemonStatus:
    online: bool
    version: str
    active_models: List[str] = field(default_factory=list)
    host: str = "127.0.0.1:11434"
    config: Optional[OllamaRuntimeConfig] = None
    hardware: Optional[HardwareProfile] = None


@dataclass
class BenchmarkResult:
    model: str
    prompt_tokens: int
    generated_tokens: int
    total_duration_ms: float
    eval_duration_ms: float
    tokens_per_second: float
    time_to_first_token_ms: float
