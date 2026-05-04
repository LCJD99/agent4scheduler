from scheduler_sim.runtime.engine import RuntimeEngine
from scheduler_sim.scheduler.base import SchedulerDecision


class SchedulerControlPlane:
    def __init__(
        self,
        *,
        runtime: RuntimeEngine,
        default_predicted_latency_us: int = 100,
    ) -> None:
        self.runtime = runtime
        self.default_predicted_latency_us = default_predicted_latency_us

    def apply(self, *, decision: SchedulerDecision) -> None:
        for selected_node in decision.selected_nodes:
            self.runtime.start_node(
                node_id=selected_node.node_id,
                predicted_latency_us=self.default_predicted_latency_us,
            )
