from dataclasses import dataclass


@dataclass(slots=True)
class RunnableNode:
    node_id: str
    source: str
    criticality: str


@dataclass(slots=True)
class SchedulerObservation:
    runnable_nodes: list[RunnableNode]


@dataclass(slots=True)
class SchedulerDecision:
    selected_nodes: list[RunnableNode]


class Scheduler:
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        raise NotImplementedError
