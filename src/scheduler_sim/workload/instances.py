from dataclasses import dataclass, field

from scheduler_sim.domain.resources import ResourceVector


@dataclass(slots=True)
class WorkloadRelease:
    node_id: str
    tool_name: str
    node_instance_id: str
    task_instance_id: str
    source: str
    criticality: str
    predicted_latency_us: int
    timestamp_us: int
    resource_demand: ResourceVector
    period_us: int | None = None
    predecessor_instance_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CriticalTaskSpec:
    node_id: str
    tool_name: str
    period_us: int
    criticality: str
    predicted_latency_us: int
    resource_demand: ResourceVector
    task_instance_id: str | None = None


@dataclass(slots=True)
class AgentArrivalSpec:
    request_id: str
    user_request: str
    arrival_time_us: int
    criticality: str


@dataclass(slots=True)
class ToolExecutionSpec:
    predicted_latency_us: int
    resource_demand: ResourceVector
