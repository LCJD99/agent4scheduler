import json
from pathlib import Path
from typing import Any

from scheduler_sim.app import main as scheduler_app_main


class ReplayRunner:
    def run(
        self,
        *,
        candidate: dict[str, Any],
        scenario_path: str,
        replay_output: str | Path,
    ) -> dict[str, Any]:
        candidate_id = candidate["candidate_id"]
        candidate_output = Path(replay_output) / candidate_id
        params_path = candidate_output / "scheduler_params.json"
        candidate_output.mkdir(parents=True, exist_ok=True)
        params_path.write_text(
            json.dumps(candidate.get("parameters", {}), sort_keys=True),
            encoding="utf-8",
        )
        code = scheduler_app_main(
            [
                "--scenario",
                scenario_path,
                "--trace-output",
                str(candidate_output),
                "--scheduler-params",
                str(params_path),
            ]
        )
        trace_dirs = sorted(path for path in candidate_output.iterdir() if path.is_dir())
        return {
            "candidate_id": candidate_id,
            "exit_code": code,
            "trace_run": str(trace_dirs[-1]) if trace_dirs else "",
        }
