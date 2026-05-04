from scheduler_sim.config.loader import load_scenario_bundle
from scheduler_sim.domain.resources import ResourceVector


def test_load_scenario_bundle_resolves_tool_task_and_scenario():
    bundle = load_scenario_bundle("configs/scenarios/home_eqa_scenario_001.yaml")

    assert bundle.scenario.metadata.name == "home_eqa_scenario_001"
    assert bundle.scenario.tick_us == 1_000
    assert bundle.scenario.duration_us == 10_000
    assert bundle.scenario.system_capacity == ResourceVector(
        cpu_cores=2.0,
        memory_mb=1024,
    )
    assert bundle.scenario.agent_requests[0].request_id == "agent-home-eqa-request-001"
    assert bundle.scenario.agent_requests[0].user_request == "What objects are on the table?"
    assert bundle.scenario.agent_requests[0].arrival_time_us == 2_000
    assert "object_detection" in bundle.tools
    assert "safe_navigation_task" in bundle.tasks
    tool = bundle.tools["object_detection"]
    assert tool.default_predicted_latency_us == 2_000
    assert tool.default_resource_demand == ResourceVector(
        cpu_cores=1.0,
        memory_mb=256,
    )
    task = bundle.tasks["safe_navigation_task"]
    assert task.critical_nodes[0].node_id == "perception.object_detection"
    assert task.critical_nodes[0].period_us == 5_000
    assert task.critical_nodes[0].criticality == "high"
    assert task.critical_nodes[0].predicted_latency_us == 2_000
    assert task.critical_nodes[0].resource_demand == ResourceVector(
        cpu_cores=1.0,
        memory_mb=256,
    )
