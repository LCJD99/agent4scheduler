from pathlib import Path
from typing import Any

from offline.io import read_json, read_jsonl, validate_trace_run


class WorkloadProfiler:
    def profile(self, trace_run: str | Path) -> dict[str, Any]:
        trace_path = Path(trace_run)
        validate_trace_run(trace_path)
        meta = read_json(trace_path / "experiment_meta.json")
        summary = read_json(trace_path / "trace_summary.json")
        task_definitions = read_jsonl(trace_path / "task_definitions.jsonl")
        workload_events = read_jsonl(trace_path / "workload_events.jsonl")
        runtime_rows = read_jsonl(trace_path / "runtime_execution.jsonl")

        critical_defs = [
            row
            for row in task_definitions
            if row.get("definition_type") == "scenario_critical_task"
        ]
        critical_periods = [
            int(row["period_us"]) for row in critical_defs if row.get("period_us")
        ]
        agent_releases = [
            row for row in workload_events if row.get("source") == "agent"
        ]
        critical_metrics = summary.get("critical_task_metrics", {})
        missed = sum(
            int(metrics.get("missed_deadline_count", 0))
            for metrics in critical_metrics.values()
        )
        total = sum(
            int(metrics.get("total_release_count", 0))
            for metrics in critical_metrics.values()
        )
        agent_aggregate = summary.get("agent_task_metrics", {}).get("aggregate", {})

        return {
            "scenario_name": meta.get("scenario_name", ""),
            "scenario_path": meta.get("scenario_path", ""),
            "scene_complexity": meta.get("scene_complexity", "unknown"),
            "critical_node_count": len(critical_defs),
            "min_critical_period_us": min(critical_periods) if critical_periods else 0,
            "avg_critical_period_us": int(sum(critical_periods) / len(critical_periods))
            if critical_periods
            else 0,
            "high_criticality_node_count": sum(
                1 for row in critical_defs if row.get("criticality") == "high"
            ),
            "agent_request_count": len(
                {row.get("task_instance_id") for row in agent_releases}
            ),
            "agent_release_count": len(agent_releases),
            "agent_arrival_density": self._density(
                count=len(agent_releases), duration_us=int(meta.get("duration_us", 0))
            ),
            "cpu_capacity": float(meta.get("system_capacity", {}).get("cpu_cores", 0)),
            "memory_capacity": int(meta.get("system_capacity", {}).get("memory_mb", 0)),
            "gpu_capacity": int(meta.get("system_capacity", {}).get("gpu_vram_mb", 0)),
            "network_capacity": float(
                meta.get("system_capacity", {}).get("network_mbps", 0)
            ),
            "avg_cpu_utilization": self._avg_utilization(runtime_rows, "cpu_cores"),
            "avg_gpu_utilization": self._avg_utilization(runtime_rows, "gpu_vram_mb"),
            "critical_deadline_miss_rate": missed / total if total else 0.0,
            "avg_agent_completion_time_us": int(
                agent_aggregate.get("avg_total_completion_time_us", 0)
            ),
        }

    @staticmethod
    def _density(*, count: int, duration_us: int) -> float:
        if duration_us <= 0:
            return 0.0
        return count / (duration_us / 1_000_000)

    @staticmethod
    def _avg_utilization(rows: list[dict[str, Any]], key: str) -> float:
        values = [
            float(row.get("resource_utilization", {}).get(key, 0.0))
            for row in rows
            if "resource_utilization" in row
        ]
        return sum(values) / len(values) if values else 0.0
