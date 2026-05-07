from typing import Any


class AdviceGenerator:
    def generate(
        self,
        *,
        workload_signature: dict[str, Any],
        trace_findings: list[dict[str, Any]],
        similar_cases: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        scene = workload_signature.get("scene_complexity", "unknown")
        miss_rate = float(workload_signature.get("critical_deadline_miss_rate", 0.0))
        branches = [
            {
                "branch_id": "branch_critical_headroom",
                "workload_characterization": f"{scene} workload with critical deadline miss rate {miss_rate:.3f}",
                "scheduler_defect_summary": self._finding_summary(trace_findings),
                "key_trace_refs": self._evidence(trace_findings),
                "proposed_heuristic_change": "Reserve CPU headroom for critical releases before admitting low-criticality agent nodes.",
                "expected_metric_impact": "Reduce critical deadline misses with possible agent makespan increase.",
                "regression_risk": "May under-utilize CPU when critical releases are sparse.",
                "parameters": {
                    "agent_cpu_reservation_cores": 1.0,
                    "agent_starvation_boost_after_us": 0,
                },
                "similar_case_count": len(similar_cases),
            },
            {
                "branch_id": "branch_agent_starvation_boost",
                "workload_characterization": f"{scene} workload with agent completion latency {workload_signature.get('avg_agent_completion_time_us', 0)} us",
                "scheduler_defect_summary": self._finding_summary(trace_findings),
                "key_trace_refs": self._evidence(trace_findings),
                "proposed_heuristic_change": "Boost agent nodes after bounded waiting time while keeping critical fit checks.",
                "expected_metric_impact": "Improve agent completion latency without removing critical-first scheduling.",
                "regression_risk": "Can increase critical contention if the boost threshold is too low.",
                "parameters": {
                    "agent_cpu_reservation_cores": 0.5,
                    "agent_starvation_boost_after_us": 500_000,
                },
                "similar_case_count": len(similar_cases),
            },
        ]
        return branches

    @staticmethod
    def _finding_summary(findings: list[dict[str, Any]]) -> str:
        return "; ".join(
            f"{finding.get('defect_type')}: {finding.get('root_cause_hypothesis')}"
            for finding in findings
        )

    @staticmethod
    def _evidence(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for finding in findings:
            refs.extend(finding.get("evidence", []))
        return refs[:8]
