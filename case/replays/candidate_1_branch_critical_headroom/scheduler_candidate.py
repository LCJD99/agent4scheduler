from scheduler_sim.scheduler.base import Scheduler, SchedulerDecision, SchedulerObservation, RunnableNode, ScheduledNodeAllocation
from scheduler_sim.domain.resources import ResourceVector


def create_scheduler(parameters=None):
    return CriticalHeadroomScheduler(parameters)


class CriticalHeadroomScheduler(Scheduler):
    def __init__(self, parameters=None):
        if parameters is None:
            parameters = {}
        self.agent_cpu_reservation = parameters.get('agent_cpu_reservation_cores', 1.0)
        self.starvation_boost = parameters.get('agent_starvation_boost_after_us', 0)
    
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        available = observation.available_resources
        remaining_cpu = available.cpu_cores
        remaining_mem = available.memory_mb
        remaining_gpu = available.gpu_vram_mb
        remaining_net = available.network_mbps
        
        # Separate nodes by criticality
        critical_nodes = []
        agent_nodes = []
        for node in observation.runnable_nodes:
            if 'critical' in node.source:
                critical_nodes.append(node)
            else:
                agent_nodes.append(node)
        
        # Sort critical by predicted latency ascending (shortest deadline first)
        critical_nodes.sort(key=lambda n: n.predicted_latency_us)
        # Sort agent by timestamp ascending (oldest first)
        agent_nodes.sort(key=lambda n: n.timestamp_us)
        
        allocations = []
        
        # Allocate critical nodes first
        for node in critical_nodes:
            demand = node.resource_demand
            if (demand.cpu_cores <= remaining_cpu and
                demand.memory_mb <= remaining_mem and
                demand.gpu_vram_mb <= remaining_gpu and
                demand.network_mbps <= remaining_net):
                alloc = ScheduledNodeAllocation(
                    node=node,
                    allocated_resources=ResourceVector(
                        cpu_cores=demand.cpu_cores,
                        memory_mb=demand.memory_mb,
                        gpu_vram_mb=demand.gpu_vram_mb,
                        network_mbps=demand.network_mbps
                    )
                )
                allocations.append(alloc)
                remaining_cpu -= demand.cpu_cores
                remaining_mem -= demand.memory_mb
                remaining_gpu -= demand.gpu_vram_mb
                remaining_net -= demand.network_mbps
        
        # Compute effective CPU reservation for agents
        # If there are critical nodes still to run, reserve CPU; otherwise allow full use
        effective_reservation = self.agent_cpu_reservation if critical_nodes else 0.0
        
        # Allocate agent nodes only if enough CPU remains after reservation
        for node in agent_nodes:
            demand = node.resource_demand
            if (demand.cpu_cores <= remaining_cpu - effective_reservation and
                demand.memory_mb <= remaining_mem and
                demand.gpu_vram_mb <= remaining_gpu and
                demand.network_mbps <= remaining_net):
                alloc = ScheduledNodeAllocation(
                    node=node,
                    allocated_resources=ResourceVector(
                        cpu_cores=demand.cpu_cores,
                        memory_mb=demand.memory_mb,
                        gpu_vram_mb=demand.gpu_vram_mb,
                        network_mbps=demand.network_mbps
                    )
                )
                allocations.append(alloc)
                remaining_cpu -= demand.cpu_cores
                remaining_mem -= demand.memory_mb
                remaining_gpu -= demand.gpu_vram_mb
                remaining_net -= demand.network_mbps
        
        return SchedulerDecision(allocations=allocations)