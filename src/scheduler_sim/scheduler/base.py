from dataclasses import dataclass


@dataclass(slots=True)
class RunnableNode:
    node_id: str
    source: str
    criticality: str
    predicted_latency_us: int = 0
    timestamp_us: int = 0


@dataclass(slots=True)
class SchedulerObservation:
    runnable_nodes: list[RunnableNode]
    timestamp_us: int = 0


@dataclass(slots=True)
class SchedulerDecision:
    selected_nodes: list[RunnableNode]
    timestamp_us: int = 0


class Scheduler:
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        raise NotImplementedError
