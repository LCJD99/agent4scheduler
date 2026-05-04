import json

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
    assert (tmp_path / "task_definitions.jsonl").exists()
    assert (tmp_path / "task_outcomes.jsonl").exists()
    assert (tmp_path / "scheduler_observation.jsonl").exists()
    assert (tmp_path / "scheduler_decision.jsonl").exists()
    assert (tmp_path / "runtime_execution.jsonl").exists()
    assert (tmp_path / "task_definitions.jsonl").read_text(encoding="utf-8").strip()
    assert (tmp_path / "task_outcomes.jsonl").read_text(encoding="utf-8").strip()
    assert (tmp_path / "runtime_execution.jsonl").read_text(encoding="utf-8").strip()

    experiment_meta = json.loads(
        (tmp_path / "experiment_meta.json").read_text(encoding="utf-8")
    )
    workload_event = json.loads(
        (tmp_path / "workload_events.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    task_definition = json.loads(
        (tmp_path / "task_definitions.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    task_outcome = json.loads(
        (tmp_path / "task_outcomes.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    scheduler_observation = json.loads(
        (tmp_path / "scheduler_observation.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    runtime_execution = json.loads(
        (tmp_path / "runtime_execution.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )

    assert "scenario_path" in experiment_meta
    assert "task_names" in experiment_meta
    assert "tool_names" in experiment_meta
    assert "agent_request_ids" in experiment_meta
    assert "node_instance_id" in workload_event
    assert "task_instance_id" in workload_event
    assert "resource_demand" in workload_event
    assert "definition_type" in task_definition
    assert "task_instance_id" in task_definition
    assert "event_type" in task_outcome
    assert "task_instance_id" in task_outcome
    assert "node_instance_id" in scheduler_observation["runnable_nodes"][0]
    assert "available_resources" in scheduler_observation
    assert "allocated_resources" in runtime_execution
    assert "resource_utilization" in runtime_execution
    assert "resource_pressure_multiplier" in runtime_execution
    assert "tick_progress_us" in runtime_execution["running_nodes"][0]
