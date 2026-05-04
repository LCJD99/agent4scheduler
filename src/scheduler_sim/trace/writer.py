import json
from pathlib import Path

from scheduler_sim.trace.events import TracePayload


class TraceWriter:
    def __init__(self, *, output_dir: Path) -> None:
        self.output_dir = output_dir

    def write_experiment_meta(self, payload: TracePayload) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "experiment_meta.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def write_workload_event(self, payload: TracePayload) -> None:
        self._append_jsonl("workload_events.jsonl", payload)

    def write_task_definition(self, payload: TracePayload) -> None:
        self._append_jsonl("task_definitions.jsonl", payload)

    def write_task_outcome(self, payload: TracePayload) -> None:
        self._append_jsonl("task_outcomes.jsonl", payload)

    def write_scheduler_observation(self, payload: TracePayload) -> None:
        self._append_jsonl("scheduler_observation.jsonl", payload)

    def write_scheduler_decision(self, payload: TracePayload) -> None:
        self._append_jsonl("scheduler_decision.jsonl", payload)

    def write_runtime_execution(self, payload: TracePayload) -> None:
        self._append_jsonl("runtime_execution.jsonl", payload)

    def _append_jsonl(self, file_name: str, payload: TracePayload) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with (self.output_dir / file_name).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload))
            handle.write("\n")
