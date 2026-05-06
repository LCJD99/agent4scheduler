from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.latency.estimator import estimate_node_progress
from scheduler_sim.runtime.state import RunningNode


class RuntimeEngine:
    def __init__(self, *, tick_us: int, system_capacity: ResourceVector) -> None:
        self.tick_us = tick_us
        self.system_capacity = system_capacity
        self.running_nodes: list[RunningNode] = []
        self.completed_count = 0

    @property
    def running_count(self) -> int:
        return len(self.running_nodes)

    @property
    def allocated_resources(self) -> ResourceVector:
        allocated = ResourceVector.zero()
        for node in self.running_nodes:
            allocated = allocated + node.resource_demand
        return allocated

    @property
    def available_resources(self) -> ResourceVector:
        return self.system_capacity - self.allocated_resources

    def _resource_utilization(
        self, allocated_resources: ResourceVector
    ) -> dict[str, float]:
        return {
            "cpu_cores": self._utilization_ratio(
                allocated=allocated_resources.cpu_cores,
                capacity=self.system_capacity.cpu_cores,
            ),
            "memory_mb": self._utilization_ratio(
                allocated=allocated_resources.memory_mb,
                capacity=self.system_capacity.memory_mb,
            ),
            "gpu_vram_mb": self._utilization_ratio(
                allocated=allocated_resources.gpu_vram_mb,
                capacity=self.system_capacity.gpu_vram_mb,
            ),
            "network_mbps": self._utilization_ratio(
                allocated=allocated_resources.network_mbps,
                capacity=self.system_capacity.network_mbps,
            ),
        }

    @staticmethod
    def _utilization_ratio(*, allocated: float | int, capacity: float | int) -> float:
        if capacity <= 0:
            return 0.0
        return float(allocated) / float(capacity)

    @staticmethod
    def _pressure_multiplier(resource_utilization: dict[str, float]) -> float:
        return 1.0 + max(resource_utilization.values(), default=0.0)

    def start_node(
        self,
        *,
        node_id: str,
        node_instance_id: str,
        task_instance_id: str,
        predicted_latency_us: int,
        resource_demand: ResourceVector,
        source: str = "unknown",
        criticality: str = "low",
        timestamp_us: int = 0,
    ) -> bool:
        if any(
            node.node_instance_id == node_instance_id for node in self.running_nodes
        ):
            return False
        if not resource_demand.fits_within(self.available_resources):
            return False

        progress = estimate_node_progress(
            predicted_latency_us=predicted_latency_us,
            tick_us=self.tick_us,
            penalty_multiplier=1.0,
        )
        self.running_nodes.append(
            RunningNode(
                node_id=node_id,
                node_instance_id=node_instance_id,
                task_instance_id=task_instance_id,
                source=source,
                criticality=criticality,
                predicted_latency_us=predicted_latency_us,
                started_at_us=timestamp_us,
                remaining_work_us=predicted_latency_us,
                progress=progress,
                tick_progress_us=progress.progress_us,
                resource_demand=resource_demand,
            )
        )
        return True

    def advance_tick(self, *, timestamp_us: int = 0) -> dict[str, object]:
        allocated_resources = self.allocated_resources
        resource_utilization = self._resource_utilization(allocated_resources)
        pressure_multiplier = self._pressure_multiplier(resource_utilization)
        still_running: list[RunningNode] = []
        completed_node_instance_ids: list[str] = []
        completed_nodes: list[dict[str, object]] = []
        for node in self.running_nodes:
            node.progress = estimate_node_progress(
                predicted_latency_us=node.predicted_latency_us,
                tick_us=self.tick_us,
                penalty_multiplier=pressure_multiplier,
            )
            node.tick_progress_us = node.progress.progress_us
            node.remaining_work_us -= node.tick_progress_us
            if node.remaining_work_us <= 0:
                self.completed_count += 1
                completed_node_instance_ids.append(node.node_instance_id)
                completed_nodes.append(
                    {
                        "node_id": node.node_id,
                        "node_instance_id": node.node_instance_id,
                        "task_instance_id": node.task_instance_id,
                        "source": node.source,
                        "criticality": node.criticality,
                        "started_at_us": node.started_at_us,
                        "completed_at_us": timestamp_us + self.tick_us,
                        "predicted_latency_us": node.predicted_latency_us,
                        "tick_progress_us": node.tick_progress_us,
                        "resource_pressure_multiplier": node.progress.penalty_multiplier,
                        "resource_demand": node.resource_demand.to_dict(),
                    }
                )
                continue
            still_running.append(node)
        self.running_nodes = still_running
        return {
            "timestamp_us": timestamp_us,
            "allocated_resources": allocated_resources.to_dict(),
            "resource_utilization": resource_utilization,
            "resource_pressure_multiplier": pressure_multiplier,
            "running_nodes": [
                {
                    "node_id": node.node_id,
                    "node_instance_id": node.node_instance_id,
                    "task_instance_id": node.task_instance_id,
                    "source": node.source,
                    "criticality": node.criticality,
                    "remaining_work_us": node.remaining_work_us,
                    "predicted_latency_us": node.predicted_latency_us,
                    "started_at_us": node.started_at_us,
                    "tick_progress_us": node.tick_progress_us,
                    "resource_pressure_multiplier": node.progress.penalty_multiplier,
                    "resource_demand": node.resource_demand.to_dict(),
                }
                for node in self.running_nodes
            ],
            "completed_node_instance_ids": completed_node_instance_ids,
            "completed_nodes": completed_nodes,
        }
