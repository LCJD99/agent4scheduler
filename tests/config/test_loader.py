from scheduler_sim.config.loader import load_scenario_bundle


def test_load_scenario_bundle_resolves_tool_task_and_scenario():
    bundle = load_scenario_bundle("configs/scenarios/home_eqa_scenario_001.yaml")

    assert bundle.scenario.metadata.name == "home_eqa_scenario_001"
    assert "object_detection" in bundle.tools
    assert "safe_navigation_task" in bundle.tasks
