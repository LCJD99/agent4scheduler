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
