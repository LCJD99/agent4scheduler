from dataclasses import dataclass

from scheduler_sim.domain.resources import ResourceVector


@dataclass(slots=True)
class Metadata:
    name: str


@dataclass(slots=True)
class AgentRequestSpec:
    request_id: str
    user_request: str
    arrival_time_us: int
    criticality: str


@dataclass(slots=True)
class CriticalNodeSpec:
    node_id: str
    tool_name: str
    period_us: int
    criticality: str
    predicted_latency_us: int
    resource_demand: ResourceVector


@dataclass(slots=True)
class ToolSpec:
    metadata: Metadata
    default_predicted_latency_us: int
    default_resource_demand: ResourceVector


@dataclass(slots=True)
class TaskSpec:
    metadata: Metadata
    tool_refs: list[str]
    critical_nodes: list[CriticalNodeSpec]


@dataclass(slots=True)
class ScenarioSpec:
    metadata: Metadata
    task_refs: list[str]
    scene_complexity: str
    tick_us: int
    duration_us: int
    system_capacity: ResourceVector
    agent_requests: list[AgentRequestSpec]


@dataclass(slots=True)
class ScenarioBundle:
    scenario: ScenarioSpec
    tools: dict[str, ToolSpec]
    tasks: dict[str, TaskSpec]
