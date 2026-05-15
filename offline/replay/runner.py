import json
from pathlib import Path
from typing import Any


def scheduler_app_main(argv: list[str]) -> int:
    from scheduler_sim.app import main

    return main(argv)


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
        scheduler_code_path = candidate_output / "scheduler_candidate.py"
        candidate_output.mkdir(parents=True, exist_ok=True)
        params_path.write_text(
            json.dumps(candidate.get("parameters", {}), sort_keys=True),
            encoding="utf-8",
        )
        argv = [
            "--scenario",
            scenario_path,
            "--trace-output",
            str(candidate_output),
            "--scheduler-params",
            str(params_path),
        ]
        if candidate.get("scheduler_source"):
            scheduler_code_path.write_text(
                str(candidate["scheduler_source"]),
                encoding="utf-8",
            )
            argv.extend(["--scheduler-code", str(scheduler_code_path)])
        code = scheduler_app_main(argv)
        trace_dirs = sorted(
            path
            for path in candidate_output.iterdir()
            if path.is_dir() and (path / "trace_summary.json").exists()
        )
        result = {
            "candidate_id": candidate_id,
            "exit_code": code,
            "trace_run": str(trace_dirs[-1]) if trace_dirs else "",
        }
        if scheduler_code_path.exists():
            result["scheduler_code"] = str(scheduler_code_path)
        return result
