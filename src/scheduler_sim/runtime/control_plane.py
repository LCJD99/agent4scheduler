from scheduler_sim.runtime.engine import RuntimeEngine
from scheduler_sim.scheduler.base import RunnableNode, SchedulerDecision


class SchedulerControlPlane:
    def __init__(
        self,
        *,
        runtime: RuntimeEngine,
        default_predicted_latency_us: int = 100,
    ) -> None:
        self.runtime = runtime
        self.default_predicted_latency_us = default_predicted_latency_us

    def apply(self, *, decision: SchedulerDecision) -> list[RunnableNode]:
        started_nodes: list[RunnableNode] = []
        for selected_node in decision.selected_nodes:
            started = self.runtime.start_node(
                node_id=selected_node.node_id,
                predicted_latency_us=selected_node.predicted_latency_us
                or self.default_predicted_latency_us,
                source=selected_node.source,
                criticality=selected_node.criticality,
                timestamp_us=decision.timestamp_us,
            )
            if started:
                started_nodes.append(selected_node)
        return started_nodes
