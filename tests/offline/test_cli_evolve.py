import json

from offline.cli import main as offline_main
from scheduler_sim.app import main as app_main


def test_offline_cli_evolves_trace_run_and_persists_replay_result(tmp_path):
    baseline_root = tmp_path / "baseline"
    replay_root = tmp_path / "replays"
    memory_path = tmp_path / "offline.db"

    assert (
        app_main(
            [
                "--scenario",
                "configs/scenarios/home_eqa_scenario_001.yaml",
                "--trace-output",
                str(baseline_root),
            ]
        )
        == 0
    )
    trace_run = next(path for path in baseline_root.iterdir() if path.is_dir())

    code = offline_main(
        [
            "evolve",
            "--trace-run",
            str(trace_run),
            "--memory",
            str(memory_path),
            "--replay-output",
            str(replay_root),
            "--max-candidates",
            "2",
        ]
    )

    result_path = replay_root / "offline_evolution_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert code == 0
    assert result["trace_findings"]
    assert len(result["advice_branches"]) >= 2
    assert len(result["candidate_schedulers"]) == 2
    assert result["replay_results"]
    assert result["selected_candidate"] is not None
    assert memory_path.exists()
