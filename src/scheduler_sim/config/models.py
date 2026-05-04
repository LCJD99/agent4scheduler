from dataclasses import dataclass


@dataclass(slots=True)
class Metadata:
    name: str


@dataclass(slots=True)
class AgentRequestSpec:
    node_id: str
    arrival_time_us: int
    criticality: str
    predicted_latency_us: int


@dataclass(slots=True)
class CriticalNodeSpec:
    node_id: str
    period_us: int
    criticality: str
    predicted_latency_us: int


@dataclass(slots=True)
class ToolSpec:
    metadata: Metadata


@dataclass(slots=True)
class TaskSpec:
    metadata: Metadata
    tool_refs: list[str]
    critical_nodes: list[CriticalNodeSpec]


@dataclass(slots=True)
class ScenarioSpec:
    metadata: Metadata
    task_refs: list[str]
    tick_us: int
    duration_us: int
    agent_requests: list[AgentRequestSpec]


@dataclass(slots=True)
class ScenarioBundle:
    scenario: ScenarioSpec
    tools: dict[str, ToolSpec]
    tasks: dict[str, TaskSpec]
