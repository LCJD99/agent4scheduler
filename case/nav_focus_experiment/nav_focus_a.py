from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import RunnableNode, ScheduledNodeAllocation, Scheduler, SchedulerDecision, SchedulerObservation

class NavFocusA(Scheduler):
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        remaining = observation.available_resources
        allocations = []
        nav_runnable = [n for n in observation.runnable_nodes if n.node_id == 'navigation_algo_node']
        nav_running = any(n.node_id == 'navigation_algo_node' for n in observation.running_nodes)
        high = [n for n in observation.runnable_nodes if n.criticality == 'high' and n.node_id != 'navigation_algo_node']
        medium = [n for n in observation.runnable_nodes if n.criticality == 'medium']
        low = [n for n in observation.runnable_nodes if n.criticality == 'low']
        nav_runnable.sort(key=lambda n: n.node_instance_id)
        high.sort(key=lambda n: n.node_instance_id)
        medium.sort(key=lambda n: n.node_instance_id)
        low.sort(key=lambda n: n.node_instance_id)

        for node in nav_runnable:
            alloc = ResourceVector(cpu_cores=min(1.5, remaining.cpu_cores), memory_mb=max(node.resource_demand.memory_mb, 320), gpu_vram_mb=node.resource_demand.gpu_vram_mb, network_mbps=node.resource_demand.network_mbps)
            if alloc.fits_within(remaining):
                allocations.append(ScheduledNodeAllocation(node=node, allocated_resources=alloc))
                remaining = remaining - alloc

        for node in high:
            if node.resource_demand.fits_within(remaining):
                allocations.append(ScheduledNodeAllocation(node=node, allocated_resources=node.resource_demand))
                remaining = remaining - node.resource_demand

        nav_backlog = bool(nav_runnable) or nav_running
        if not nav_backlog:
            for node in medium:
                if node.resource_demand.fits_within(remaining):
                    allocations.append(ScheduledNodeAllocation(node=node, allocated_resources=node.resource_demand))
                    remaining = remaining - node.resource_demand
            for node in low:
                if node.resource_demand.fits_within(remaining):
                    allocations.append(ScheduledNodeAllocation(node=node, allocated_resources=node.resource_demand))
                    remaining = remaining - node.resource_demand
        return SchedulerDecision(allocations=allocations, timestamp_us=observation.timestamp_us)

def create_scheduler(parameters=None):
    return NavFocusA()
