from scheduler_sim.runtime.engine import RuntimeEngine
from scheduler_sim.scheduler.base import ScheduledNodeAllocation, SchedulerDecision


class SchedulerControlPlane:
    def __init__(
        self,
        *,
        runtime: RuntimeEngine,
        default_predicted_latency_us: int = 100,
    ) -> None:
        self.runtime = runtime
        self.default_predicted_latency_us = default_predicted_latency_us

    def apply(self, *, decision: SchedulerDecision) -> list[ScheduledNodeAllocation]:
        started_nodes: list[ScheduledNodeAllocation] = []
        for allocation in decision.allocations:
            selected_node = allocation.node
            started = self.runtime.start_node(
                node_id=selected_node.node_id,
                tool_name=selected_node.tool_name,
                node_instance_id=selected_node.node_instance_id,
                task_instance_id=selected_node.task_instance_id,
                allocated_resources=allocation.allocated_resources,
                resource_demand=selected_node.resource_demand,
                source=selected_node.source,
                criticality=selected_node.criticality,
                timestamp_us=decision.timestamp_us,
            )
            if started:
                started_nodes.append(allocation)
        return started_nodes
