from scheduler_sim.config.loader import load_scenario_bundle


def test_load_scenario_bundle_resolves_tool_task_and_scenario():
    bundle = load_scenario_bundle("configs/scenarios/home_eqa_scenario_001.yaml")

    assert bundle.scenario.metadata.name == "home_eqa_scenario_001"
    assert bundle.scenario.tick_us == 1_000
    assert bundle.scenario.duration_us == 10_000
    assert bundle.scenario.agent_requests[0].node_id == "agent-home-eqa-request-001"
    assert bundle.scenario.agent_requests[0].arrival_time_us == 2_000
    assert "object_detection" in bundle.tools
    assert "safe_navigation_task" in bundle.tasks
    task = bundle.tasks["safe_navigation_task"]
    assert task.critical_nodes[0].node_id == "perception.object_detection"
    assert task.critical_nodes[0].period_us == 5_000
    assert task.critical_nodes[0].criticality == "high"
    assert task.critical_nodes[0].predicted_latency_us == 2_000
