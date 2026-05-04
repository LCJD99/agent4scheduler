from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.runtime.engine import RuntimeEngine


def test_runtime_completes_node_after_enough_ticks():
    engine = RuntimeEngine(
        tick_us=20,
        system_capacity=ResourceVector(cpu_cores=2.0, memory_mb=1024),
    )
    engine.start_node(
        node_id="node-a",
        node_instance_id="node-a:0",
        task_instance_id="task-a",
        predicted_latency_us=100,
        resource_demand=ResourceVector.zero(),
    )

    for _ in range(5):
        engine.advance_tick()

    assert engine.completed_count == 1


def test_runtime_rejects_duplicate_and_over_capacity_starts():
    engine = RuntimeEngine(
        tick_us=20,
        system_capacity=ResourceVector(cpu_cores=2.0, memory_mb=1024),
    )

    started = engine.start_node(
        node_id="node-a",
        node_instance_id="node-a:0",
        task_instance_id="task-a",
        predicted_latency_us=100,
        resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
    )
    duplicate = engine.start_node(
        node_id="node-a",
        node_instance_id="node-a:0",
        task_instance_id="task-a",
        predicted_latency_us=100,
        resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
    )
    overflow = engine.start_node(
        node_id="node-b",
        node_instance_id="node-b:0",
        task_instance_id="task-b",
        predicted_latency_us=100,
        resource_demand=ResourceVector(cpu_cores=2.0, memory_mb=128),
    )

    assert started is True
    assert duplicate is False
    assert overflow is False


def test_runtime_reports_completed_node_timing():
    engine = RuntimeEngine(
        tick_us=20,
        system_capacity=ResourceVector(cpu_cores=2.0, memory_mb=1024),
    )
    engine.start_node(
        node_id="node-a",
        node_instance_id="task-a:node-a:0",
        task_instance_id="task-a",
        predicted_latency_us=20,
        resource_demand=ResourceVector.zero(),
        source="critical",
        criticality="high",
        timestamp_us=100,
    )

    payload = engine.advance_tick(timestamp_us=100)

    assert payload["completed_node_instance_ids"] == ["task-a:node-a:0"]
    assert payload["completed_nodes"][0]["node_id"] == "node-a"
    assert payload["completed_nodes"][0]["node_instance_id"] == "task-a:node-a:0"
    assert payload["completed_nodes"][0]["task_instance_id"] == "task-a"
    assert payload["completed_nodes"][0]["source"] == "critical"
    assert payload["completed_nodes"][0]["criticality"] == "high"
    assert payload["completed_nodes"][0]["started_at_us"] == 100
    assert payload["completed_nodes"][0]["completed_at_us"] == 120
    assert payload["completed_nodes"][0]["predicted_latency_us"] == 20
    assert payload["completed_nodes"][0]["resource_demand"]["cpu_cores"] == 0.0
    assert payload["completed_nodes"][0]["resource_demand"]["memory_mb"] == 0


def test_runtime_slows_progress_under_higher_resource_pressure():
    light_engine = RuntimeEngine(
        tick_us=20,
        system_capacity=ResourceVector(cpu_cores=4.0, memory_mb=1024),
    )
    heavy_engine = RuntimeEngine(
        tick_us=20,
        system_capacity=ResourceVector(cpu_cores=4.0, memory_mb=1024),
    )

    light_engine.start_node(
        node_id="node-a",
        node_instance_id="task-a:node-a:0",
        task_instance_id="task-a",
        predicted_latency_us=100,
        resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
    )
    heavy_engine.start_node(
        node_id="node-a",
        node_instance_id="task-a:node-a:0",
        task_instance_id="task-a",
        predicted_latency_us=100,
        resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
    )
    heavy_engine.start_node(
        node_id="node-b",
        node_instance_id="task-b:node-b:0",
        task_instance_id="task-b",
        predicted_latency_us=100,
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
