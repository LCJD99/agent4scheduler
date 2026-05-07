import os
import re
import subprocess
import sys
from pathlib import Path

from scheduler_sim.app import main


def test_main_returns_zero_for_help_mode():
    assert main(["--help"]) == 0


def test_module_cli_emits_trace_directory(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root / "src")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scheduler_sim.app",
            "--scenario",
            "configs/scenarios/home_eqa_scenario_001.yaml",
            "--trace-output",
            str(tmp_path),
        ],
        cwd=repo_root,
        env=env,
        check=False,
    )

    assert completed.returncode == 0
    trace_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(trace_dirs) == 1
    assert re.fullmatch(r"\d{8}-\d{6}", trace_dirs[0].name)
    assert (trace_dirs[0] / "experiment_meta.json").exists()
