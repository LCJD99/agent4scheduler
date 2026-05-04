from dataclasses import dataclass

from scheduler_sim.latency.models import ProgressSlice


@dataclass(slots=True)
class RunningNode:
    node_id: str
    remaining_work_us: float
    progress: ProgressSlice
