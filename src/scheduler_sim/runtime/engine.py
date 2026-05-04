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

    def start_node(
        self,
        *,
        node_id: str,
        predicted_latency_us: int,
        source: str = "unknown",
        criticality: str = "low",
        timestamp_us: int = 0,
    ) -> bool:
        if any(node.node_id == node_id for node in self.running_nodes):
            return False

        progress = estimate_node_progress(
            predicted_latency_us=predicted_latency_us,
            tick_us=self.tick_us,
            penalty_multiplier=1.0,
        )
        self.running_nodes.append(
            RunningNode(
                node_id=node_id,
                source=source,
                criticality=criticality,
                predicted_latency_us=predicted_latency_us,
                started_at_us=timestamp_us,
                remaining_work_us=predicted_latency_us,
                progress=progress,
            )
        )
        return True

    def advance_tick(self, *, timestamp_us: int = 0) -> dict[str, object]:
        still_running: list[RunningNode] = []
        completed_node_ids: list[str] = []
        for node in self.running_nodes:
            node.remaining_work_us -= node.progress.progress_us
            if node.remaining_work_us <= 0:
                self.completed_count += 1
                completed_node_ids.append(node.node_id)
                continue
            still_running.append(node)
        self.running_nodes = still_running
        return {
            "timestamp_us": timestamp_us,
            "running_nodes": [
                {
                    "node_id": node.node_id,
                    "source": node.source,
                    "criticality": node.criticality,
                    "remaining_work_us": node.remaining_work_us,
                    "predicted_latency_us": node.predicted_latency_us,
                    "started_at_us": node.started_at_us,
                }
                for node in self.running_nodes
            ],
            "completed_node_ids": completed_node_ids,
        }
