from scheduler_sim.workload.generator import WorkloadGenerator


def test_generator_releases_periodic_critical_node_on_tick_boundary():
    generator = WorkloadGenerator.critical_only(
        node_id="local_planner_node",
        period_us=50_000,
    )

    events = generator.release(timestamp_us=50_000)

    assert any(event.node_id == "local_planner_node" for event in events)
