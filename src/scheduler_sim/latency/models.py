from dataclasses import dataclass


@dataclass(slots=True)
class ProgressSlice:
    predicted_latency_us: int
    progress_us: float
    penalty_multiplier: float
