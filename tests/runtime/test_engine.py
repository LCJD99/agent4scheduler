from scheduler_sim.runtime.engine import RuntimeEngine


def test_runtime_completes_node_after_enough_ticks():
    engine = RuntimeEngine(tick_us=20)
    engine.start_node(node_id="node-a", predicted_latency_us=100)

    for _ in range(5):
        engine.advance_tick()

    assert engine.completed_count == 1
