from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import (
    RunnableNode,
    ScheduledNodeAllocation,
    Scheduler,
    SchedulerDecision,
    SchedulerObservation,
)


class CriticalHeadroomScheduler(Scheduler):
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        # Separate nodes by criticality
        critical_nodes = []
        agent_nodes = []
        for node in observation.runnable_nodes:
            if node.criticality == "high":
                critical_nodes.append(node)
            else:
                agent_nodes.append(node)
        
        # Sort critical nodes by priority (criticality rank, then instance id)
        critical_nodes.sort(key=self._priority_key)
        # Sort agent nodes by priority (same key, but they will be considered after critical)
        agent_nodes.sort(key=self._priority_key)
        
        remaining = observation.available_resources
        allocations = []
        
        # First pass: allocate all critical nodes that fit
        for node in critical_nodes:
            if node.resource_demand.fits_within(remaining):
                allocations.append(
                    ScheduledNodeAllocation(
                        node=node,
                        allocated_resources=node.resource_demand,
                    )
                )
                remaining = remaining - node.resource_demand
        
        # Second pass: allocate agent nodes only if there is enough headroom
        # Use reservation logic: reserve 1 CPU core for critical tasks before admitting agent nodes
        # Check if after reserving 1 CPU core, there is enough capacity for the agent node
        for node in agent_nodes:
            # Reserve headroom: ensure at least 1.0 CPU core remains available for future critical tasks
            reserved_cpu = min(1.0, remaining.cpu_cores)
            # Create a resource vector that reflects the remaining capacity after reservation
            headroom = ResourceVector(
                cpu_cores=remaining.cpu_cores - reserved_cpu,
                memory_mb=remaining.memory_mb,
                gpu_vram_mb=remaining.gpu_vram_mb,
                network_mbps=remaining.network_mbps,
            )
            # Only allocate if the node fits within the headroom (i.e., after reservation)
            if node.resource_demand.fits_within(headroom):
                allocations.append(
                    ScheduledNodeAllocation(
                        node=node,
                        allocated_resources=node.resource_demand,
                    )
                )
                remaining = remaining - node.resource_demand
        
        return SchedulerDecision(
            allocations=allocations,
            timestamp_us=observation.timestamp_us,
        )
    
    def _priority_key(self, node: RunnableNode) -> tuple[int, str]:
        criticality_rank = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }
        return (criticality_rank.get(node.criticality, 3), node.node_instance_id)


def create_scheduler(parameters=None):
    return CriticalHeadroomScheduler()