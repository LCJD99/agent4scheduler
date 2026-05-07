from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.runtime.engine import RuntimeEngine


class StubProfilingEstimator:
    def estimate_latency_us(
        self,
        *,
        tool_name: str,
        allocated_resources: ResourceVector,
        scene_complexity: str,
    ) -> int:
        return int(
            100
            + allocated_resources.cpu_cores * 100
            + allocated_resources.memory_mb / 4
            + {"small": 0, "medium": 25, "large": 50}[scene_complexity]
        )


def build_engine(*, scene_complexity: str = "medium") -> RuntimeEngine:
    return RuntimeEngine(
        tick_us=20,
        system_capacity=ResourceVector(cpu_cores=4.0, memory_mb=1024),
        profiling_estimator=StubProfilingEstimator(),
        scene_complexity=scene_complexity,
    )


def test_runtime_completes_node_after_enough_ticks():
    engine = build_engine()
    engine.start_node(
        node_id="node-a",
        tool_name="image_captioning",
        node_instance_id="node-a:0",
        task_instance_id="task-a",
        allocated_resources=ResourceVector.zero(),
        resource_demand=ResourceVector.zero(),
    )

    for _ in range(7):
        engine.advance_tick()

    assert engine.completed_count == 1


def test_runtime_rejects_duplicate_and_over_capacity_starts():
    engine = build_engine()

    started = engine.start_node(
        node_id="node-a",
        tool_name="image_captioning",
        node_instance_id="node-a:0",
        task_instance_id="task-a",
        allocated_resources=ResourceVector(cpu_cores=1.0, memory_mb=128),
        resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
    )
    duplicate = engine.start_node(
        node_id="node-a",
        tool_name="image_captioning",
        node_instance_id="node-a:0",
        task_instance_id="task-a",
        allocated_resources=ResourceVector(cpu_cores=1.0, memory_mb=128),
        resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
    )
    overflow = engine.start_node(
        node_id="node-b",
        tool_name="text_translation",
        node_instance_id="node-b:0",
        task_instance_id="task-b",
        allocated_resources=ResourceVector(cpu_cores=4.0, memory_mb=128),
        resource_demand=ResourceVector(cpu_cores=4.0, memory_mb=128),
    )

    assert started is True
    assert duplicate is False
    assert overflow is False


def test_runtime_reports_completed_node_timing_and_profiled_latency():
    engine = build_engine()
    engine.start_node(
        node_id="node-a",
        tool_name="text_translation",
        node_instance_id="task-a:node-a:0",
        task_instance_id="task-a",
        allocated_resources=ResourceVector.zero(),
        resource_demand=ResourceVector.zero(),
        source="critical",
        criticality="high",
        timestamp_us=100,
    )

    for _ in range(7):
        payload = engine.advance_tick(timestamp_us=100)

    assert payload["completed_node_instance_ids"] == ["task-a:node-a:0"]
    assert payload["completed_nodes"][0]["node_id"] == "node-a"
    assert payload["completed_nodes"][0]["node_instance_id"] == "task-a:node-a:0"
    assert payload["completed_nodes"][0]["task_instance_id"] == "task-a"
    assert payload["completed_nodes"][0]["tool_name"] == "text_translation"
    assert payload["completed_nodes"][0]["source"] == "critical"
    assert payload["completed_nodes"][0]["criticality"] == "high"
    assert payload["completed_nodes"][0]["started_at_us"] == 100
    assert payload["completed_nodes"][0]["completed_at_us"] == 120
    assert payload["completed_nodes"][0]["predicted_latency_us"] == 125
    assert payload["completed_nodes"][0]["allocated_resources"]["cpu_cores"] == 0.0
    assert payload["completed_nodes"][0]["resource_demand"]["cpu_cores"] == 0.0
    assert payload["completed_nodes"][0]["resource_demand"]["memory_mb"] == 0


def test_runtime_slows_progress_under_higher_resource_pressure():
    light_engine = build_engine(scene_complexity="small")
    heavy_engine = build_engine(scene_complexity="small")

    light_engine.start_node(
        node_id="node-a",
        tool_name="image_captioning",
        node_instance_id="task-a:node-a:0",
        task_instance_id="task-a",
        allocated_resources=ResourceVector(cpu_cores=1.0, memory_mb=128),
        resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
    )
    heavy_engine.start_node(
        node_id="node-a",
        tool_name="image_captioning",
        node_instance_id="task-a:node-a:0",
        task_instance_id="task-a",
        allocated_resources=ResourceVector(cpu_cores=1.0, memory_mb=128),
        resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
    )
    heavy_engine.start_node(
        node_id="node-b",
        tool_name="text_translation",
        node_instance_id="task-b:node-b:0",
        task_instance_id="task-b",
        allocated_resources=ResourceVector(cpu_cores=2.0, memory_mb=128),
        resource_demand=ResourceVector(cpu_cores=2.0, memory_mb=128),
    )

    light_payload = light_engine.advance_tick(timestamp_us=0)
    heavy_payload = heavy_engine.advance_tick(timestamp_us=0)

    light_node = light_payload["running_nodes"][0]
    heavy_node = next(
        node
        for node in heavy_payload["running_nodes"]
        if node["node_instance_id"] == "task-a:node-a:0"
    )

    assert light_payload["resource_pressure_multiplier"] < (
        heavy_payload["resource_pressure_multiplier"]
    )
    assert light_node["tick_progress_us"] > heavy_node["tick_progress_us"]
    assert light_node["remaining_work_us"] < heavy_node["remaining_work_us"]


def test_runtime_uses_scene_complexity_in_profiled_latency():
    small_engine = build_engine(scene_complexity="small")
    large_engine = build_engine(scene_complexity="large")

    small_engine.start_node(
        node_id="node-a",
        tool_name="image_captioning",
        node_instance_id="task-a:node-a:0",
        task_instance_id="task-a",
        allocated_resources=ResourceVector(cpu_cores=1.0, memory_mb=128),
        resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
    )
    large_engine.start_node(
        node_id="node-a",
        tool_name="image_captioning",
        node_instance_id="task-a:node-a:0",
        task_instance_id="task-a",
        allocated_resources=ResourceVector(cpu_cores=1.0, memory_mb=128),
        resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
    )

    assert small_engine.running_nodes[0].predicted_latency_us < (
        large_engine.running_nodes[0].predicted_latency_us
    )
