from scheduler_sim.latency.estimator import estimate_node_progress


def test_contention_penalty_slows_effective_progress():
    free = estimate_node_progress(
        predicted_latency_us=1000,
        tick_us=100,
        penalty_multiplier=1.0,
    )
    contended = estimate_node_progress(
        predicted_latency_us=1000,
        tick_us=100,
        penalty_multiplier=2.0,
    )
    assert contended.progress_us < free.progress_us
