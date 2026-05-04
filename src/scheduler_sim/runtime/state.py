from dataclasses import dataclass

from scheduler_sim.latency.models import ProgressSlice


@dataclass(slots=True)
class RunningNode:
    node_id: str
    source: str
    criticality: str
    predicted_latency_us: int
    started_at_us: int
    remaining_work_us: float
    progress: ProgressSlice
