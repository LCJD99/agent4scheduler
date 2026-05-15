from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import RunnableNode, ScheduledNodeAllocation, Scheduler, SchedulerDecision, SchedulerObservation

class NavFocusC(Scheduler):
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        remaining = observation.available_resources
        allocations = []
        nav_runnable = [n for n in observation.runnable_nodes if n.node_id == 'navigation_algo_node']
        other_high = [n for n in observation.runnable_nodes if n.criticality == 'high' and n.node_id != 'navigation_algo_node']
        medium = [n for n in observation.runnable_nodes if n.criticality == 'medium']
        low = [n for n in observation.runnable_nodes if n.criticality == 'low']
        nav_runnable.sort(key=lambda n: n.node_instance_id)
        other_high.sort(key=lambda n: n.node_instance_id)
        medium.sort(key=lambda n: n.node_instance_id)
        low.sort(key=lambda n: n.node_instance_id)
        for node in nav_runnable:
            alloc = ResourceVector(cpu_cores=min(1.8, remaining.cpu_cores), memory_mb=max(node.resource_demand.memory_mb, 320), gpu_vram_mb=node.resource_demand.gpu_vram_mb, network_mbps=node.resource_demand.network_mbps)
            if alloc.fits_within(remaining):
                allocations.append(ScheduledNodeAllocation(node=node, allocated_resources=alloc))
                remaining = remaining - alloc
        for node in other_high:
            if node.resource_demand.fits_within(remaining):
                allocations.append(ScheduledNodeAllocation(node=node, allocated_resources=node.resource_demand))
                remaining = remaining - node.resource_demand
        for node in medium:
            # only allow medium critical if navigation is not waiting
            if not nav_runnable and node.resource_demand.fits_within(remaining):
                allocations.append(ScheduledNodeAllocation(node=node, allocated_resources=node.resource_demand))
                remaining = remaining - node.resource_demand
        for node in low:
            if not nav_runnable and node.resource_demand.fits_within(remaining):
                allocations.append(ScheduledNodeAllocation(node=node, allocated_resources=node.resource_demand))
                remaining = remaining - node.resource_demand
        return SchedulerDecision(allocations=allocations, timestamp_us=observation.timestamp_us)

def create_scheduler(parameters=None):
    return NavFocusC()
