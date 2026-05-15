from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import (
    RunnableNode,
    ScheduledNodeAllocation,
    Scheduler,
    SchedulerDecision,
    SchedulerObservation,
)


class CriticalHeadroomScheduler(Scheduler):
    def __init__(self, parameters=None):
        # Default reservation: 1 CPU core for critical headroom
        self.agent_cpu_reservation_cores = 1.0
        if parameters and "agent_cpu_reservation_cores" in parameters:
            self.agent_cpu_reservation_cores = parameters["agent_cpu_reservation_cores"]

    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        # Separate nodes by criticality
        critical_nodes = []
        agent_nodes = []
        for node in observation.runnable_nodes:
            if node.criticality == "high":
                critical_nodes.append(node)
            else:
                agent_nodes.append(node)

        # Sort critical nodes by priority (earliest deadline first among high criticality)
        critical_nodes.sort(key=lambda n: (n.predicted_latency_us, n.node_instance_id))
        # Sort agent nodes by arrival time (FIFO) then by instance id
        agent_nodes.sort(key=lambda n: (n.timestamp_us, n.node_instance_id))

        remaining_capacity = observation.available_resources
        allocations: list[ScheduledNodeAllocation] = []

        # Allocate critical nodes first with full resource demand
        for node in critical_nodes:
            if node.resource_demand.fits_within(remaining_capacity):
                allocations.append(
                    ScheduledNodeAllocation(
                        node=node,
                        allocated_resources=node.resource_demand,
                    )
                )
                remaining_capacity = remaining_capacity - node.resource_demand

        # Reserve CPU headroom for critical releases
        reservation_cores = min(self.agent_cpu_reservation_cores, remaining_capacity.cpu_cores)
        reserved_cpu = ResourceVector(
            cpu_cores=reservation_cores,
            memory_mb=0,
            gpu_vram_mb=0,
            network_mbps=0,
        )
        effective_capacity = remaining_capacity - reserved_cpu

        # Allocate agent nodes only if they fit within effective capacity (after reservation)
        for node in agent_nodes:
            if node.resource_demand.fits_within(effective_capacity):
                allocations.append(
                    ScheduledNodeAllocation(
                        node=node,
                        allocated_resources=node.resource_demand,
                    )
                )
                effective_capacity = effective_capacity - node.resource_demand
                remaining_capacity = remaining_capacity - node.resource_demand

        return SchedulerDecision(
            allocations=allocations,
            timestamp_us=observation.timestamp_us,
        )


def create_scheduler(parameters=None):
    return CriticalHeadroomScheduler(parameters)