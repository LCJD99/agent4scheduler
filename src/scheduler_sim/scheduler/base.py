from dataclasses import dataclass, field

from scheduler_sim.domain.resources import ResourceVector


@dataclass(slots=True)
class RunnableNode:
    node_id: str
    node_instance_id: str
    task_instance_id: str
    tool_name: str
    source: str
    criticality: str
    predicted_latency_us: int = 0
    timestamp_us: int = 0
    resource_demand: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class RunningNode(RunnableNode):
    started_at_us: int = 0
    allocated_resources: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class ScheduledNodeAllocation:
    node: RunnableNode
    allocated_resources: ResourceVector


@dataclass(slots=True)
class SchedulerObservation:
    runnable_nodes: list[RunnableNode]
    running_nodes: list[RunningNode] = field(default_factory=list)
    timestamp_us: int = 0
    available_resources: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class SchedulerDecision:
    allocations: list[ScheduledNodeAllocation]
    timestamp_us: int = 0

    @property
    def selected_nodes(self) -> list[RunnableNode]:
        return [allocation.node for allocation in self.allocations]


class Scheduler:
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        raise NotImplementedError
