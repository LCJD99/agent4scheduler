from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import (
    RunnableNode,
    ScheduledNodeAllocation,
    Scheduler,
    SchedulerDecision,
    SchedulerObservation,
)


class NavigationGuardrailScheduler(Scheduler):
    def __init__(self, parameters=None):
        self.agent_cpu_reservation_cores = 0.75
        self.agent_starvation_boost_after_us = 1000000
        self.high_criticality_only_when_backlogged = True
        if parameters:
            self.agent_cpu_reservation_cores = parameters.get('agent_cpu_reservation_cores', self.agent_cpu_reservation_cores)
            self.agent_starvation_boost_after_us = parameters.get('agent_starvation_boost_after_us', self.agent_starvation_boost_after_us)
            self.high_criticality_only_when_backlogged = parameters.get('high_criticality_only_when_backlogged', self.high_criticality_only_when_backlogged)

    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        runnable_nodes = observation.runnable_nodes
        running_nodes = observation.running_nodes
        remaining_capacity = observation.available_resources
        allocations = []

        # Classify nodes
        critical_nodes = []
        agent_nodes = []
        for node in runnable_nodes:
            if node.criticality == 'high' and 'navigation_algo_node' in node.tool_name:
                critical_nodes.append(node)
            else:
                agent_nodes.append(node)

        # Determine if backlog condition exists
        backlog_detected = len(critical_nodes) > 0

        # Sort critical nodes by instance id for deterministic ordering
        critical_nodes.sort(key=lambda x: x.node_instance_id)

        # Allocate critical nodes first (always prioritize)
        for node in critical_nodes:
            if node.resource_demand.fits_within(remaining_capacity):
                allocations.append(ScheduledNodeAllocation(
                    node=node,
                    allocated_resources=node.resource_demand,
                ))
                remaining_capacity = remaining_capacity - node.resource_demand

        # Apply guardrail: reserve CPU capacity for future critical releases when backlog is detected
        if backlog_detected and self.high_criticality_only_when_backlogged:
            # Reserve agent CPU reservation cores
            agent_reservation = ResourceVector(cpu_cores=self.agent_cpu_reservation_cores)
            if remaining_capacity.cpu_cores < self.agent_cpu_reservation_cores:
                # Not enough capacity to reserve, skip agent nodes
                return SchedulerDecision(
                    allocations=allocations,
                    timestamp_us=observation.timestamp_us,
                )
            # Reduce remaining capacity by reservation
            remaining_capacity = remaining_capacity - agent_reservation

        # Sort agent nodes by starvation boost time (older first)
        agent_nodes.sort(key=lambda x: -x.timestamp_us)

        # Allocate agent nodes if they fit
        for node in agent_nodes:
            if node.resource_demand.fits_within(remaining_capacity):
                allocations.append(ScheduledNodeAllocation(
                    node=node,
                    allocated_resources=node.resource_demand,
                ))
                remaining_capacity = remaining_capacity - node.resource_demand

        return SchedulerDecision(
            allocations=allocations,
            timestamp_us=observation.timestamp_us,
        )


def create_scheduler(parameters=None):
    return NavigationGuardrailScheduler(parameters=parameters)