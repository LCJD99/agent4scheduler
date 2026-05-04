from dataclasses import dataclass

from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.latency.models import ProgressSlice


@dataclass(slots=True)
class RunningNode:
    node_id: str
    node_instance_id: str
    task_instance_id: str
    source: str
    criticality: str
    predicted_latency_us: int
    started_at_us: int
    remaining_work_us: float
    progress: ProgressSlice
    tick_progress_us: float
    resource_demand: ResourceVector
