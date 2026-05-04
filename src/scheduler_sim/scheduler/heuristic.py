from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import RunnableNode, Scheduler, SchedulerDecision, SchedulerObservation


class HeuristicScheduler(Scheduler):
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        remaining_capacity = observation.available_resources
        selected_nodes: list[RunnableNode] = []
        for node in sorted(observation.runnable_nodes, key=self._priority_key):
            if node.resource_demand.fits_within(remaining_capacity):
                selected_nodes.append(node)
                remaining_capacity = remaining_capacity - node.resource_demand
        return SchedulerDecision(
            selected_nodes=selected_nodes,
            timestamp_us=observation.timestamp_us,
        )

    def _priority_key(self, node: RunnableNode) -> tuple[int, str]:
        criticality_rank = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }
        return (criticality_rank.get(node.criticality, 3), node.node_instance_id)
