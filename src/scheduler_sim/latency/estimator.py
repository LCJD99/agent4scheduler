from scheduler_sim.latency.models import ProgressSlice


def estimate_node_progress(
    *,
    predicted_latency_us: int,
    tick_us: int,
    penalty_multiplier: float,
) -> ProgressSlice:
    effective_penalty = penalty_multiplier if penalty_multiplier > 0 else 1.0
    progress_us = min(predicted_latency_us, tick_us / effective_penalty)
    return ProgressSlice(
        predicted_latency_us=predicted_latency_us,
        progress_us=progress_us,
        penalty_multiplier=effective_penalty,
    )
