from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import (
    RunnableNode,
    ScheduledNodeAllocation,
    Scheduler,
    SchedulerDecision,
    SchedulerObservation,
)


class ParameterizedHeuristicScheduler(Scheduler):
    def __init__(self, *, parameters: dict[str, object] | None = None) -> None:
        self.parameters = parameters or {}

    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        remaining_capacity = observation.available_resources
        allocations: list[ScheduledNodeAllocation] = []
        for node in sorted(
            observation.runnable_nodes,
            key=lambda node: self._priority_key_with_observation(
                node=node,
                timestamp_us=observation.timestamp_us,
            ),
        ):
            if self._can_allocate_node(node=node, remaining_capacity=remaining_capacity):
                allocations.append(
                    ScheduledNodeAllocation(
                        node=node,
                        allocated_resources=node.resource_demand,
                    )
                )
                remaining_capacity = remaining_capacity - node.resource_demand
        return SchedulerDecision(
            allocations=allocations,
            timestamp_us=observation.timestamp_us,
        )

    def _can_allocate_node(
        self, *, node: RunnableNode, remaining_capacity: ResourceVector
    ) -> bool:
        if not node.resource_demand.fits_within(remaining_capacity):
            return False
        if node.source == "agent":
            reserved_cpu = float(self.parameters.get("agent_cpu_reservation_cores", 0.0))
            remaining_cpu = remaining_capacity.cpu_cores - node.resource_demand.cpu_cores
            if remaining_cpu < reserved_cpu:
                return False
            gpu_threshold = float(
                self.parameters.get("gpu_pressure_launch_threshold", 1.0)
            )
            if gpu_threshold < 1.0 and remaining_capacity.gpu_vram_mb > 0:
                used_after_launch = node.resource_demand.gpu_vram_mb
                if used_after_launch / remaining_capacity.gpu_vram_mb > gpu_threshold:
                    return False
        return True

    def _priority_key_with_observation(
        self, *, node: RunnableNode, timestamp_us: int
    ) -> tuple[int, int, str]:
        boost_after_us = int(self.parameters.get("agent_starvation_boost_after_us", 0))
        waiting_time_us = max(0, timestamp_us - node.timestamp_us)
        if (
            node.source == "agent"
            and boost_after_us
            and waiting_time_us >= boost_after_us
        ):
            return (-1, -waiting_time_us, node.node_instance_id)
        criticality_rank = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }
        return (
            criticality_rank.get(node.criticality, 3),
            -waiting_time_us,
            node.node_instance_id,
        )
