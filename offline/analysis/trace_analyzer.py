from pathlib import Path
from typing import Any

from offline.io import read_json, read_jsonl, validate_trace_run


class TraceAnalyzer:
    def analyze(self, trace_run: str | Path) -> list[dict[str, Any]]:
        trace_path = Path(trace_run)
        validate_trace_run(trace_path)
        summary = read_json(trace_path / "trace_summary.json")
        outcomes = read_jsonl(trace_path / "task_outcomes.jsonl")
        findings = self._deadline_findings(summary)
        findings.extend(self._agent_latency_findings(summary))
        if not findings:
            findings.append(
                {
                    "defect_type": "no_major_defect_detected",
                    "severity": "info",
                    "affected_nodes": [],
                    "root_cause_hypothesis": "trace summary did not expose critical misses or agent latency outliers",
                    "evidence": [{"file": "trace_summary.json"}],
                    "natural_language_advice": "Keep the baseline scheduler as a reference and explore conservative agent latency improvements.",
                }
            )
        missed_outcomes = [
            row for row in outcomes if row.get("outcome_type") == "critical_release" and row.get("missed_deadline")
        ]
        if missed_outcomes and findings:
            findings[0]["evidence"].append(
                {
                    "file": "task_outcomes.jsonl",
                    "missed_release_examples": [
                        {
                            "node_id": row.get("node_id"),
                            "node_instance_id": row.get("node_instance_id"),
                            "deadline_us": row.get("deadline_us"),
                            "completed_at_us": row.get("completed_at_us"),
                        }
                        for row in missed_outcomes[:5]
                    ],
                }
            )
        return findings

    @staticmethod
    def _deadline_findings(summary: dict[str, Any]) -> list[dict[str, Any]]:
        affected_nodes = []
        total_missed = 0
        for node_id, metrics in summary.get("critical_task_metrics", {}).items():
            missed = int(metrics.get("missed_deadline_count", 0))
            if missed:
                affected_nodes.append(str(node_id))
                total_missed += missed
        if not affected_nodes:
            return []
        return [
            {
                "defect_type": "critical_deadline_miss",
                "severity": "high",
                "affected_nodes": affected_nodes,
                "root_cause_hypothesis": "scheduler allowed resource pressure or waiting time to violate critical release deadlines",
                "evidence": [
                    {
                        "file": "trace_summary.json",
                        "metric": "critical_task_metrics.*.missed_deadline_count",
                        "value": total_missed,
                    }
                ],
                "natural_language_advice": "Add critical-resource headroom and avoid launching low-criticality agent nodes when critical releases are likely to need capacity.",
            }
        ]

    @staticmethod
    def _agent_latency_findings(summary: dict[str, Any]) -> list[dict[str, Any]]:
        aggregate = summary.get("agent_task_metrics", {}).get("aggregate", {})
        avg_completion = int(aggregate.get("avg_total_completion_time_us", 0))
        if avg_completion <= 0:
            return []
        return [
            {
                "defect_type": "agent_completion_latency",
                "severity": "medium",
                "affected_nodes": [],
                "root_cause_hypothesis": "agent task makespan can improve if safe leftover resources are used more aggressively",
                "evidence": [
                    {
                        "file": "trace_summary.json",
                        "metric": "agent_task_metrics.aggregate.avg_total_completion_time_us",
                        "value": avg_completion,
                    }
                ],
                "natural_language_advice": "Add bounded starvation boosting for agent nodes after critical safety filters are satisfied.",
            }
        ]
