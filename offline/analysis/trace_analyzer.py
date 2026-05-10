from dataclasses import dataclass
from pathlib import Path
from typing import Any

from offline.analysis.llm_agent import OpenAILLMFindingAgent
from offline.config_loader import load_offline_analyzer_config
from offline.io import read_json, read_jsonl, validate_trace_run


DEFAULT_ANALYZER_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "configs"
    / "offline"
    / "trace_analyzer_openai.yaml"
)


@dataclass(slots=True)
class TraceWindow:
    center_timestamp_us: int
    start_timestamp_us: int
    end_timestamp_us: int
    reason: str
    node_id: str
    node_instance_id: str


class TraceAnalyzer:
    def __init__(
        self,
        *,
        window_radius_us: int = 50_000,
        config_path: str | Path | None = None,
        client_factory=None,
    ) -> None:
        self.agent = AgenticTraceAnalyzer(
            window_radius_us=window_radius_us,
            config_path=config_path or DEFAULT_ANALYZER_CONFIG_PATH,
            client_factory=client_factory,
        )

    def analyze(self, trace_run: str | Path) -> list[dict[str, Any]]:
        return self.agent.analyze(trace_run)


class AgenticTraceAnalyzer:
    def __init__(
        self,
        *,
        window_radius_us: int,
        config_path: str | Path,
        client_factory=None,
    ) -> None:
        self.config = load_offline_analyzer_config(config_path)
        self.window_selector = TraceWindowSelector(window_radius_us=window_radius_us)
        self.window_inspector = TraceWindowInspector()
        self.finding_agent = OpenAILLMFindingAgent(
            config=self.config,
            client_factory=client_factory,
        )
        self.adapter = TraceFindingAdapter()

    def analyze(self, trace_run: str | Path) -> list[dict[str, Any]]:
        trace_path = Path(trace_run)
        validate_trace_run(trace_path)
        trace = TraceBundle.load(trace_path)
        windows = self.window_selector.select(trace)
        inspections = [
            self.window_inspector.inspect(trace=trace, window=window)
            for window in windows[: self.config.max_windows]
        ]
        llm_result = self.finding_agent.run(
            trace_summary=trace.summary,
            inspections=inspections,
        )
        return self.adapter.to_findings(
            trace_summary=trace.summary,
            inspections=inspections,
            llm_result=llm_result,
        )


@dataclass(slots=True)
class TraceBundle:
    trace_path: Path
    summary: dict[str, Any]
    outcomes: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    runtime_rows: list[dict[str, Any]]

    @classmethod
    def load(cls, trace_path: Path) -> "TraceBundle":
        return cls(
            trace_path=trace_path,
            summary=read_json(trace_path / "trace_summary.json"),
            outcomes=read_jsonl(trace_path / "task_outcomes.jsonl"),
            observations=read_jsonl(trace_path / "scheduler_observation.jsonl"),
            decisions=read_jsonl(trace_path / "scheduler_decision.jsonl"),
            runtime_rows=read_jsonl(trace_path / "runtime_execution.jsonl"),
        )


class TraceWindowSelector:
    def __init__(self, *, window_radius_us: int) -> None:
        self.window_radius_us = window_radius_us

    def select(self, trace: TraceBundle) -> list[TraceWindow]:
        missed_critical = [
            row
            for row in trace.outcomes
            if row.get("outcome_type") == "critical_release"
            and row.get("missed_deadline")
        ]
        windows = [self._window_for_missed_release(row) for row in missed_critical[:5]]
        if windows:
            return windows
        return self._fallback_windows(trace)

    def _window_for_missed_release(self, outcome: dict[str, Any]) -> TraceWindow:
        center_timestamp_us = int(
            outcome.get("deadline_us")
            or outcome.get("completed_at_us")
            or outcome.get("released_at_us")
            or 0
        )
        return TraceWindow(
            center_timestamp_us=center_timestamp_us,
            start_timestamp_us=max(0, center_timestamp_us - self.window_radius_us),
            end_timestamp_us=center_timestamp_us + self.window_radius_us,
            reason="critical_deadline_miss",
            node_id=str(outcome.get("node_id", "")),
            node_instance_id=str(outcome.get("node_instance_id", "")),
        )

    def _fallback_windows(self, trace: TraceBundle) -> list[TraceWindow]:
        if not trace.runtime_rows:
            return []
        highest_pressure = max(
            trace.runtime_rows,
            key=lambda row: max(
                (
                    float(value)
                    for value in row.get("resource_utilization", {}).values()
                ),
                default=0.0,
            ),
        )
        timestamp_us = int(highest_pressure.get("timestamp_us", 0))
        return [
            TraceWindow(
                center_timestamp_us=timestamp_us,
                start_timestamp_us=max(0, timestamp_us - self.window_radius_us),
                end_timestamp_us=timestamp_us + self.window_radius_us,
                reason="highest_resource_pressure",
                node_id="",
                node_instance_id="",
            )
        ]


class TraceWindowInspector:
    def inspect(self, *, trace: TraceBundle, window: TraceWindow) -> dict[str, Any]:
        observations = self._rows_in_window(trace.observations, window)
        decisions = self._rows_in_window(trace.decisions, window)
        runtime_rows = self._rows_in_window(trace.runtime_rows, window)
        return {
            "center_timestamp_us": window.center_timestamp_us,
            "start_timestamp_us": window.start_timestamp_us,
            "end_timestamp_us": window.end_timestamp_us,
            "reason": window.reason,
            "target_node_id": window.node_id,
            "target_node_instance_id": window.node_instance_id,
            "critical_runnable_nodes": self._runnable_nodes(
                observations, source="critical"
            ),
            "agent_runnable_nodes": self._runnable_nodes(observations, source="agent"),
            "agent_selected_nodes": self._selected_nodes(decisions, source="agent"),
            "critical_selected_nodes": self._selected_nodes(
                decisions, source="critical"
            ),
            "max_cpu_utilization": self._max_utilization(runtime_rows, "cpu_cores"),
            "max_gpu_utilization": self._max_utilization(runtime_rows, "gpu_vram_mb"),
            "running_agent_nodes": self._running_nodes(runtime_rows, source="agent"),
        }

    @staticmethod
    def _rows_in_window(
        rows: list[dict[str, Any]], window: TraceWindow
    ) -> list[dict[str, Any]]:
        return [
            row
            for row in rows
            if window.start_timestamp_us
            <= int(row.get("timestamp_us", 0))
            <= window.end_timestamp_us
        ]

    @staticmethod
    def _runnable_nodes(rows: list[dict[str, Any]], *, source: str) -> list[str]:
        node_ids: list[str] = []
        for row in rows:
            for node in row.get("runnable_nodes", []):
                if node.get("source") == source:
                    node_ids.append(
                        str(node.get("node_instance_id") or node.get("node_id"))
                    )
        return sorted(set(node_ids))

    @staticmethod
    def _selected_nodes(rows: list[dict[str, Any]], *, source: str) -> list[str]:
        node_ids: list[str] = []
        for row in rows:
            for node in row.get("selected_nodes", []):
                if node.get("source") == source:
                    node_ids.append(
                        str(node.get("node_instance_id") or node.get("node_id"))
                    )
        return sorted(set(node_ids))

    @staticmethod
    def _running_nodes(rows: list[dict[str, Any]], *, source: str) -> list[str]:
        node_ids: list[str] = []
        for row in rows:
            for node in row.get("running_nodes", []):
                if node.get("source") == source:
                    node_ids.append(
                        str(node.get("node_instance_id") or node.get("node_id"))
                    )
        return sorted(set(node_ids))

    @staticmethod
    def _max_utilization(rows: list[dict[str, Any]], key: str) -> float:
        return max(
            (float(row.get("resource_utilization", {}).get(key, 0.0)) for row in rows),
            default=0.0,
        )


class TraceFindingAdapter:
    def to_findings(
        self,
        *,
        trace_summary: dict[str, Any],
        inspections: list[dict[str, Any]],
        llm_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            self._adapt_finding(
                finding=finding,
                trace_summary=trace_summary,
                inspections=inspections,
            )
            for finding in llm_result.get("findings", [])
        ]

    def _adapt_finding(
        self,
        *,
        finding: dict[str, Any],
        trace_summary: dict[str, Any],
        inspections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "defect_type": finding["defect_type"],
            "severity": finding["severity"],
            "analysis_mode": "openai_llm_agent",
            "affected_nodes": list(finding["affected_nodes"]),
            "root_cause_hypothesis": finding["root_cause_hypothesis"],
            "evidence": [
                self._summary_evidence(
                    defect_type=str(finding["defect_type"]),
                    trace_summary=trace_summary,
                ),
                {
                    "file": "selected_trace_windows",
                    "windows": [
                        inspections[index]
                        for index in finding.get("window_refs", [])
                        if 0 <= index < len(inspections)
                    ],
                },
            ],
            "natural_language_advice": finding["natural_language_advice"],
        }

    def _summary_evidence(
        self,
        *,
        defect_type: str,
        trace_summary: dict[str, Any],
    ) -> dict[str, Any]:
        if defect_type == "critical_deadline_miss":
            total_missed = sum(
                int(metrics.get("missed_deadline_count", 0))
                for metrics in trace_summary.get("critical_task_metrics", {}).values()
            )
            return {
                "file": "trace_summary.json",
                "metric": "critical_task_metrics.*.missed_deadline_count",
                "value": total_missed,
            }
        if defect_type == "agent_completion_latency":
            avg_completion = int(
                trace_summary.get("agent_task_metrics", {})
                .get("aggregate", {})
                .get("avg_total_completion_time_us", 0)
            )
            return {
                "file": "trace_summary.json",
                "metric": "agent_task_metrics.aggregate.avg_total_completion_time_us",
                "value": avg_completion,
            }
        return {"file": "trace_summary.json"}
