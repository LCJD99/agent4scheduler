from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import RunnableNode, ScheduledNodeAllocation, Scheduler, SchedulerDecision, SchedulerObservation

class NavFocusB(Scheduler):
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        remaining = observation.available_resources
        allocations = []
        nodes = sorted(observation.runnable_nodes, key=lambda n: (0 if n.node_id=='navigation_algo_node' else 1 if n.criticality=='high' else 2 if n.criticality=='medium' else 3, n.node_instance_id))
        for node in nodes:
            alloc = node.resource_demand
            if node.node_id == 'navigation_algo_node':
                alloc = ResourceVector(cpu_cores=min(1.5, remaining.cpu_cores), memory_mb=max(node.resource_demand.memory_mb, 320), gpu_vram_mb=node.resource_demand.gpu_vram_mb, network_mbps=node.resource_demand.network_mbps)
            if alloc.fits_within(remaining):
                allocations.append(ScheduledNodeAllocation(node=node, allocated_resources=alloc))
                remaining = remaining - alloc
        return SchedulerDecision(allocations=allocations, timestamp_us=observation.timestamp_us)

def create_scheduler(parameters=None):
    return NavFocusB()
