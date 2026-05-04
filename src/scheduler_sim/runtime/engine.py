from scheduler_sim.latency.estimator import estimate_node_progress
from scheduler_sim.runtime.state import RunningNode


class RuntimeEngine:
    def __init__(self, *, tick_us: int) -> None:
        self.tick_us = tick_us
        self.running_nodes: list[RunningNode] = []
        self.completed_count = 0

    @property
    def running_count(self) -> int:
        return len(self.running_nodes)

    def start_node(self, *, node_id: str, predicted_latency_us: int) -> None:
        progress = estimate_node_progress(
            predicted_latency_us=predicted_latency_us,
            tick_us=self.tick_us,
            penalty_multiplier=1.0,
        )
        self.running_nodes.append(
            RunningNode(
                node_id=node_id,
                remaining_work_us=predicted_latency_us,
                progress=progress,
            )
        )

    def advance_tick(self) -> None:
        still_running: list[RunningNode] = []
        for node in self.running_nodes:
            node.remaining_work_us -= node.progress.progress_us
            if node.remaining_work_us <= 0:
                self.completed_count += 1
                continue
            still_running.append(node)
        self.running_nodes = still_running
