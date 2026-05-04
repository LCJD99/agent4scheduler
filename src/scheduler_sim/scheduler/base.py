from dataclasses import dataclass, field

from scheduler_sim.domain.resources import ResourceVector


@dataclass(slots=True)
class RunnableNode:
    node_id: str
    node_instance_id: str
    task_instance_id: str
    source: str
    criticality: str
    predicted_latency_us: int = 0
    timestamp_us: int = 0
    resource_demand: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class SchedulerObservation:
    runnable_nodes: list[RunnableNode]
    timestamp_us: int = 0
    available_resources: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class SchedulerDecision:
    selected_nodes: list[RunnableNode]
    timestamp_us: int = 0


class Scheduler:
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        raise NotImplementedError
