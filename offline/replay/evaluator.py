from pathlib import Path
from typing import Any

from offline.io import read_json


class ReplayEvaluator:
    def evaluate(
        self,
        *,
        baseline_trace_run: str | Path,
        replay_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        baseline_summary = read_json(Path(baseline_trace_run) / "trace_summary.json")
        baseline_missed = self._critical_missed(baseline_summary)
        baseline_agent_avg = self._agent_avg(baseline_summary)
        evaluated: list[dict[str, Any]] = []
        for result in replay_results:
            if result.get("exit_code") != 0 or not result.get("trace_run"):
                evaluated.append(result | {"accepted": False, "score": float("-inf")})
                continue
            summary = read_json(Path(str(result["trace_run"])) / "trace_summary.json")
            missed = self._critical_missed(summary)
            agent_avg = self._agent_avg(summary)
            accepted = missed <= baseline_missed
            score = -1000.0 * missed - self._normalized(agent_avg, baseline_agent_avg)
            evaluated.append(
                result
                | {
                    "accepted": accepted,
                    "score": score,
                    "metrics": {
                        "critical_missed_deadline_count": missed,
                        "agent_avg_completion_time_us": agent_avg,
                    },
                }
            )
        return evaluated

    @staticmethod
    def select_best(evaluated_results: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not evaluated_results:
            return None
        accepted = [result for result in evaluated_results if result.get("accepted")]
        pool = accepted or evaluated_results
        return max(pool, key=lambda result: float(result.get("score", float("-inf"))))

    @staticmethod
    def _critical_missed(summary: dict[str, Any]) -> int:
        return sum(
            int(metrics.get("missed_deadline_count", 0))
            for metrics in summary.get("critical_task_metrics", {}).values()
        )

    @staticmethod
    def _agent_avg(summary: dict[str, Any]) -> int:
        return int(
            summary.get("agent_task_metrics", {})
            .get("aggregate", {})
            .get("avg_total_completion_time_us", 0)
        )

    @staticmethod
    def _normalized(value: int, baseline: int) -> float:
        if baseline <= 0:
            return float(value)
        return value / baseline
