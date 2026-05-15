from scheduler_sim.config.loader import load_scenario_bundle
from scheduler_sim.domain.resources import ResourceVector


def test_load_scenario_bundle_resolves_tool_task_and_scenario():
    bundle = load_scenario_bundle("configs/scenarios/home_eqa_scenario_001.yaml")

    assert bundle.scenario.metadata.name == "home_eqa_scenario_001"
    assert bundle.scenario.scene_complexity == "large"
    assert bundle.scenario.tick_us == 1_000
    assert bundle.scenario.duration_us == 4_000_000
    assert bundle.scenario.system_capacity == ResourceVector(
        cpu_cores=4.0,
        memory_mb=4096,
        gpu_vram_mb=2048,
        network_mbps=100.0,
    )
    assert bundle.scenario.agent_requests[0].request_id == "agent-caption-pipeline"
    assert bundle.scenario.agent_requests[0].user_request == "Describe, translate, and speak the latest image."
    assert bundle.scenario.agent_requests[0].arrival_time_us == 18_000
    assert "image_captioning" in bundle.tools
    assert "localization_node" in bundle.tools
    assert "pointcloud_to_laserscan_node" in bundle.tools
    assert "navigation_algo_node" in bundle.tools
    assert "text_translation" in bundle.tools
    assert "text_to_speech" in bundle.tools
    assert "safe_navigation_task" in bundle.tasks
    assert "agent_caption_pipeline_task" in bundle.tasks
    tool = bundle.tools["image_captioning"]
    assert tool.default_predicted_latency_us == 820_000
    assert tool.default_resource_demand == ResourceVector(
        cpu_cores=1.0,
        memory_mb=384,
        gpu_vram_mb=768,
    )
    task = bundle.tasks["safe_navigation_task"]
    assert [node.node_id for node in task.critical_nodes] == [
        "localization_node",
        "pointcloud_to_laserscan_node",
        "navigation_algo_node",
    ]
    assert task.critical_nodes[0].period_us == 20_000
    assert task.critical_nodes[0].criticality == "high"
    assert task.critical_nodes[0].tool_name == "localization_node"
    assert task.critical_nodes[1].period_us == 50_000
    assert task.critical_nodes[1].criticality == "medium"
    assert task.critical_nodes[1].tool_name == "pointcloud_to_laserscan_node"
    assert task.critical_nodes[2].period_us == 28_571
    assert task.critical_nodes[2].criticality == "high"
    assert task.critical_nodes[2].tool_name == "navigation_algo_node"
    assert task.critical_nodes[0].resource_demand == ResourceVector(
        cpu_cores=0.24,
        memory_mb=128,
    )
    assert task.critical_nodes[1].resource_demand == ResourceVector(
        cpu_cores=0.55,
        memory_mb=192,
    )
    assert task.critical_nodes[2].resource_demand == ResourceVector(
        cpu_cores=1.0,
        memory_mb=256,
    )
