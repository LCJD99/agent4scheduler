from dataclasses import dataclass


@dataclass(slots=True)
class ResourceVector:
    cpu_cores: float = 0.0
    memory_mb: int = 0
    gpu_vram_mb: int = 0
    network_mbps: float = 0.0
