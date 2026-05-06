from dataclasses import dataclass


@dataclass(slots=True)
class ResourceVector:
    cpu_cores: float = 0.0
    memory_mb: int = 0
    gpu_vram_mb: int = 0
    network_mbps: float = 0.0

    @classmethod
    def zero(cls) -> "ResourceVector":
        return cls()

    def fits_within(self, other: "ResourceVector") -> bool:
        return (
            self.cpu_cores <= other.cpu_cores
            and self.memory_mb <= other.memory_mb
            and self.gpu_vram_mb <= other.gpu_vram_mb
            and self.network_mbps <= other.network_mbps
        )

    def __add__(self, other: "ResourceVector") -> "ResourceVector":
        return ResourceVector(
            cpu_cores=self.cpu_cores + other.cpu_cores,
            memory_mb=self.memory_mb + other.memory_mb,
            gpu_vram_mb=self.gpu_vram_mb + other.gpu_vram_mb,
            network_mbps=self.network_mbps + other.network_mbps,
        )

    def __sub__(self, other: "ResourceVector") -> "ResourceVector":
        return ResourceVector(
            cpu_cores=self.cpu_cores - other.cpu_cores,
            memory_mb=self.memory_mb - other.memory_mb,
            gpu_vram_mb=self.gpu_vram_mb - other.gpu_vram_mb,
            network_mbps=self.network_mbps - other.network_mbps,
        )

    def to_dict(self) -> dict[str, float | int]:
        return {
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "gpu_vram_mb": self.gpu_vram_mb,
            "network_mbps": self.network_mbps,
        }
