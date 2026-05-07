import json
from pathlib import Path
from typing import Any


REQUIRED_TRACE_FILES = [
    "experiment_meta.json",
    "workload_events.jsonl",
    "task_definitions.jsonl",
    "task_outcomes.jsonl",
    "scheduler_observation.jsonl",
    "scheduler_decision.jsonl",
    "runtime_execution.jsonl",
    "trace_summary.json",
]


def validate_trace_run(trace_run: Path) -> None:
    missing = [name for name in REQUIRED_TRACE_FILES if not (trace_run / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing trace files in {trace_run}: {missing}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSONL row {path}:{line_number}") from error
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
