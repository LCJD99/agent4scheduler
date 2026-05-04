from dataclasses import dataclass


@dataclass(slots=True)
class Metadata:
    name: str


@dataclass(slots=True)
class ToolSpec:
    metadata: Metadata


@dataclass(slots=True)
class TaskSpec:
    metadata: Metadata
    tool_refs: list[str]


@dataclass(slots=True)
class ScenarioSpec:
    metadata: Metadata
    task_refs: list[str]


@dataclass(slots=True)
class ScenarioBundle:
    scenario: ScenarioSpec
    tools: dict[str, ToolSpec]
    tasks: dict[str, TaskSpec]
