from scheduler_sim.app import main


def test_end_to_end_scenario_runs_and_emits_trace(tmp_path):
    code = main(
        [
            "--scenario",
            "configs/scenarios/home_eqa_scenario_001.yaml",
            "--trace-output",
            str(tmp_path),
        ]
    )

    assert code == 0
    assert (tmp_path / "experiment_meta.json").exists()
    assert (tmp_path / "workload_events.jsonl").exists()
    assert (tmp_path / "scheduler_observation.jsonl").exists()
    assert (tmp_path / "scheduler_decision.jsonl").exists()
    assert (tmp_path / "runtime_execution.jsonl").exists()
    assert (tmp_path / "runtime_execution.jsonl").read_text(encoding="utf-8").strip()
