from typing import Any, TypedDict


class EvolutionState(TypedDict, total=False):
    trace_run_path: str
    memory_path: str
    replay_output: str
    scenario_path: str
    max_candidates: int
    baseline_scheduler: str
    workload_signature: dict[str, Any]
    similar_cases: list[dict[str, Any]]
    trace_findings: list[dict[str, Any]]
    critical_trace_refs: list[dict[str, Any]]
    advice_branches: list[dict[str, Any]]
    candidate_schedulers: list[dict[str, Any]]
    replay_results: list[dict[str, Any]]
    selected_candidate: dict[str, Any] | None
    result_path: str
