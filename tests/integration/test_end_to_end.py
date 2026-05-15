import json
import re

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
    trace_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(trace_dirs) == 1
    assert re.fullmatch(r"\d{8}-\d{6}", trace_dirs[0].name)

    trace_dir = trace_dirs[0]
    assert (trace_dir / "experiment_meta.json").exists()
    assert (trace_dir / "workload_events.jsonl").exists()
    assert (trace_dir / "task_definitions.jsonl").exists()
    assert (trace_dir / "task_outcomes.jsonl").exists()
    assert (trace_dir / "scheduler_observation.jsonl").exists()
    assert (trace_dir / "scheduler_decision.jsonl").exists()
    assert (trace_dir / "runtime_execution.jsonl").exists()
    assert (trace_dir / "trace_summary.json").exists()
    assert (trace_dir / "task_definitions.jsonl").read_text(encoding="utf-8").strip()
    assert (trace_dir / "task_outcomes.jsonl").read_text(encoding="utf-8").strip()
    assert (trace_dir / "runtime_execution.jsonl").read_text(encoding="utf-8").strip()

    experiment_meta = json.loads(
        (trace_dir / "experiment_meta.json").read_text(encoding="utf-8")
    )
    workload_event = json.loads(
        (trace_dir / "workload_events.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    task_definition = json.loads(
        (trace_dir / "task_definitions.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    task_outcome = json.loads(
        (trace_dir / "task_outcomes.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    scheduler_observations = [
        json.loads(line)
        for line in (trace_dir / "scheduler_observation.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    scheduler_observation = scheduler_observations[0]
    running_observation = next(
        observation
        for observation in scheduler_observations
        if observation["running_nodes"]
    )
    runtime_execution = json.loads(
        (trace_dir / "runtime_execution.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    trace_summary = json.loads(
        (trace_dir / "trace_summary.json").read_text(encoding="utf-8")
    )

    assert experiment_meta["trace_run_id"] == trace_dir.name
    assert experiment_meta["scene_complexity"] == "large"
    assert experiment_meta["profiling_data_path"].endswith("data/profiling_data.csv")
    assert "scenario_path" in experiment_meta
    assert "task_names" in experiment_meta
    assert "tool_names" in experiment_meta
    assert "agent_request_ids" in experiment_meta
    assert workload_event["node_instance_id"]
    assert workload_event["task_instance_id"]
    assert workload_event["tool_name"]
    assert "resource_demand" in workload_event
    assert "definition_type" in task_definition
    assert task_definition["task_instance_id"]
    assert "event_type" in task_outcome
    assert task_outcome["task_instance_id"]
    assert scheduler_observation["runnable_nodes"][0]["node_instance_id"]
    assert "running_nodes" in scheduler_observation
    assert "started_at_us" in running_observation["running_nodes"][0]
    assert "available_resources" in scheduler_observation
    assert "tool_name" in running_observation["running_nodes"][0]
    assert "allocated_resources" in runtime_execution
    assert "resource_utilization" in runtime_execution
    assert "resource_pressure_multiplier" in runtime_execution
    assert "tick_progress_us" in runtime_execution["running_nodes"][0]
    assert runtime_execution["running_nodes"][0]["scene_complexity"] == "large"
    assert "localization_node" in trace_summary["critical_task_metrics"]
    assert (
        trace_summary["critical_task_metrics"]["localization_node"]["total_release_count"]
        > 0
    )
    assert (
        trace_summary["critical_task_metrics"]["navigation_algo_node"][
            "missed_deadline_count"
        ]
        > 0
    )
    assert (
        trace_summary["critical_task_metrics"]["navigation_algo_node"][
            "frequency_satisfaction_rate"
        ]
        < 1.0
    )
    assert trace_summary["agent_task_metrics"]["instances"][0]["task_instance_id"]
    assert (
        trace_summary["agent_task_metrics"]["instances"][0]["total_completion_time_us"]
        > 0
    )


def test_end_to_end_critical_workload_is_stable_without_agent_requests(tmp_path):
    scenario_path = tmp_path / "critical_only.yaml"
    scenario_path.write_text(
        "\n".join(
            [
                "api_version: sim.scenario/v1",
                "kind: ScenarioSpec",
                "",
                "metadata:",
                "  name: critical_only_validation",
                "",
                "scene_complexity: large",
                "tick_us: 1000",
                "duration_us: 1000000",
                "system_capacity:",
                "  cpu_cores: 4.0",
                "  memory_mb: 2048",
                "  gpu_vram_mb: 2048",
                "  network_mbps: 100.0",
                "",
                "tasks:",
                "  - configs/tasks/safe_navigation_task.yaml",
                "",
                "agent_requests: []",
                "",
            ]
        ),
        encoding="utf-8",
    )

    code = main(
        [
            "--scenario",
            str(scenario_path),
            "--trace-output",
            str(tmp_path / "trace"),
        ]
    )

    assert code == 0
    trace_dir = next(path for path in (tmp_path / "trace").iterdir() if path.is_dir())
    trace_summary = json.loads(
        (trace_dir / "trace_summary.json").read_text(encoding="utf-8")
    )

    localization = trace_summary["critical_task_metrics"]["localization_node"]
    pointcloud = trace_summary["critical_task_metrics"]["pointcloud_to_laserscan_node"]
    navigation = trace_summary["critical_task_metrics"]["navigation_algo_node"]

    assert localization["frequency_satisfaction_rate"] == 1.0
    assert pointcloud["frequency_satisfaction_rate"] == 1.0
    assert navigation["frequency_satisfaction_rate"] == 1.0
    assert localization["missed_deadline_count"] == 0
    assert pointcloud["missed_deadline_count"] == 0
    assert navigation["missed_deadline_count"] == 0
    assert navigation["total_release_count"] >= 34
