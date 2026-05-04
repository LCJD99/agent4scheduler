from pathlib import Path
from typing import Any

import yaml

from scheduler_sim.config.models import Metadata, ScenarioBundle, ScenarioSpec, TaskSpec, ToolSpec


REPO_ROOT = Path(__file__).resolve().parents[3]


def load_scenario_bundle(path: str) -> ScenarioBundle:
    scenario_path = _resolve_repo_path(path)
    scenario_data = _load_yaml(scenario_path)
    scenario = _build_scenario_spec(scenario_data)

    tasks: dict[str, TaskSpec] = {}
    tools: dict[str, ToolSpec] = {}

    for task_ref in scenario.task_refs:
        task_path = _resolve_from_ref(task_ref, scenario_path.parent)
        task = _build_task_spec(_load_yaml(task_path))
        tasks[task.metadata.name] = task

        for tool_ref in task.tool_refs:
            tool_path = _resolve_from_ref(tool_ref, task_path.parent)
            tool = _build_tool_spec(_load_yaml(tool_path))
            tools[tool.metadata.name] = tool

    return ScenarioBundle(scenario=scenario, tools=tools, tasks=tasks)


def _resolve_repo_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def _resolve_from_ref(ref: str, base_dir: Path) -> Path:
    candidate = Path(ref)
    if candidate.is_absolute():
        return candidate
    if candidate.parts and candidate.parts[0] == "configs":
        return REPO_ROOT / candidate
    return (base_dir / candidate).resolve()


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping YAML in {path}")

    return data


def _build_tool_spec(data: dict[str, Any]) -> ToolSpec:
    return ToolSpec(metadata=_build_metadata(data))


def _build_task_spec(data: dict[str, Any]) -> TaskSpec:
    return TaskSpec(
        metadata=_build_metadata(data),
        tool_refs=list(data.get("tools", [])),
    )


def _build_scenario_spec(data: dict[str, Any]) -> ScenarioSpec:
    return ScenarioSpec(
        metadata=_build_metadata(data),
        task_refs=list(data.get("tasks", [])),
    )


def _build_metadata(data: dict[str, Any]) -> Metadata:
    metadata = data.get("metadata", {})
    name = metadata.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("Config metadata.name is required")
    return Metadata(name=name)
