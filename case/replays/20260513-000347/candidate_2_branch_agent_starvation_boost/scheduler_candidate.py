from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import (
    RunnableNode,
    ScheduledNodeAllocation,
    Scheduler,
    SchedulerDecision,
    SchedulerObservation,
)


class HeuristicScheduler(Scheduler):
    def __init__(self, parameters=None):
        # Extract parameters if provided, otherwise use defaults
        if parameters is None:
            parameters = {}
        self.agent_cpu_reservation_cores = parameters.get("agent_cpu_reservation_cores", 0.5)
        self.agent_starvation_boost_after_us = parameters.get("agent_starvation_boost_after_us", 500000)
    
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        remaining_capacity = observation.available_resources
        allocations: list[ScheduledNodeAllocation] = []
        
        # Separate runnable nodes into critical and agent categories
        critical_nodes = []
        agent_nodes = []
        for node in observation.runnable_nodes:
            if node.source.startswith("critical-"):
                critical_nodes.append(node)
            else:
                agent_nodes.append(node)
        
        # Sort critical nodes by their priority (criticality, then instance ID)
        critical_nodes.sort(key=self._critical_priority_key)
        
        # Sort agent nodes by waiting time (longest waiting first), then by instance ID
        # For now, we use timestamp_us as a proxy for arrival time; lower timestamp means longer waiting
        agent_nodes.sort(key=lambda node: (-node.timestamp_us, node.node_instance_id))
        
        # First pass: schedule all critical nodes that fit
        for node in critical_nodes:
            if node.resource_demand.fits_within(remaining_capacity):
                allocations.append(
                    ScheduledNodeAllocation(
                        node=node,
                        allocated_resources=node.resource_demand,
                    )
                )
                remaining_capacity = remaining_capacity - node.resource_demand
        
        # Compute remaining capacity after critical nodes
        # For agent scheduling, we may need to reserve some CPU for future critical releases
        # But we don't have future knowledge, so we use a reservation heuristic based on parameters
        # However, the advice branch suggests boosting agent nodes after a waiting time,
        # not necessarily reserving capacity. We'll implement a starvation-boost mechanism:
        # If an agent node has been waiting longer than the threshold, we prioritize it
        # among other agent nodes, but still after critical nodes.
        
        # For agent nodes, we schedule them in order of longest waiting first,
        # respecting the reservation of CPU for critical tasks.
        # We'll implement a simple reservation: reduce available CPU for agents by
        # agent_cpu_reservation_cores, but only if there are critical nodes present?
        # Actually, the branch advice says: "Boost agent nodes after bounded waiting time while keeping critical fit checks."
        # So we keep critical fit checks (already done) and then boost agents that have waited too long.
        
        # We'll sort agent nodes by whether they have waited longer than threshold,
        # then by waiting time descending.
        def agent_sort_key(node):
            # Wait time can be approximated by current time minus node.timestamp_us
            # But we don't have the creation time; node.timestamp_us is when it became runnable?
            # We'll assume node.timestamp_us is the time it became runnable.
            wait_time_us = observation.timestamp_us - node.timestamp_us
            # If wait_time_us > threshold, give it a boost (lower sort key)
            boosted = 0 if wait_time_us >= self.agent_starvation_boost_after_us else 1
            # Among boosted or non-boosted, sort by longest waiting first (descending wait_time_us)
            return (boosted, -wait_time_us, node.node_instance_id)
        
        agent_nodes.sort(key=agent_sort_key)
        
        # Second pass: schedule agent nodes that fit
        for node in agent_nodes:
            if node.resource_demand.fits_within(remaining_capacity):
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
    
    def _critical_priority_key(self, node: RunnableNode) -> tuple[int, str]:
        # Critical nodes are scheduled first; among them, higher criticality (high > medium > low)
        criticality_rank = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }
        return (criticality_rank.get(node.criticality, 3), node.node_instance_id)

def create_scheduler(parameters=None):
    return HeuristicScheduler(parameters=parameters)