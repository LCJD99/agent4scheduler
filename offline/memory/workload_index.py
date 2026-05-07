from typing import Any

from offline.memory.trace_store import TraceMemoryDB


class WorkloadIndex:
    FEATURE_KEYS = [
        "critical_node_count",
        "min_critical_period_us",
        "avg_critical_period_us",
        "high_criticality_node_count",
        "agent_request_count",
        "agent_release_count",
        "agent_arrival_density",
        "cpu_capacity",
        "memory_capacity",
        "gpu_capacity",
        "network_capacity",
        "avg_cpu_utilization",
        "avg_gpu_utilization",
        "critical_deadline_miss_rate",
        "avg_agent_completion_time_us",
    ]

    def __init__(self, db: TraceMemoryDB) -> None:
        self.db = db

    def upsert_case(
        self,
        *,
        workload_signature: dict[str, Any],
        scheduler_version: str,
        trace_run: str,
        metrics: dict[str, Any],
        advice: list[dict[str, Any]],
    ) -> None:
        self.db.upsert_case(
            workload_signature=workload_signature,
            scheduler_version=scheduler_version,
            trace_run=trace_run,
            metrics=metrics,
            advice=advice,
        )

    def query_similar(
        self, workload_signature: dict[str, Any], *, top_k: int = 5
    ) -> list[dict[str, Any]]:
        target = self.to_vector(workload_signature)
        cases = self.db.list_cases()
        scored = [
            (self._distance(target, self.to_vector(case["workload_signature"])), case)
            for case in cases
        ]
        scored.sort(key=lambda item: item[0])
        return [case | {"distance": distance} for distance, case in scored[:top_k]]

    @classmethod
    def to_vector(cls, signature: dict[str, Any]) -> list[float]:
        return [float(signature.get(key, 0.0) or 0.0) for key in cls.FEATURE_KEYS]

    @staticmethod
    def _distance(left: list[float], right: list[float]) -> float:
        return sum((a - b) ** 2 for a, b in zip(left, right)) ** 0.5
