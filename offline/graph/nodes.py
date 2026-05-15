from pathlib import Path
from typing import Any

from offline.analysis.advice import AdviceGenerator
from offline.analysis.trace_analyzer import TraceAnalyzer
from offline.analysis.workload_profiler import WorkloadProfiler
from offline.evolution.proposal import CandidateGenerator
from offline.io import read_json, write_json
from offline.memory.trace_store import TraceMemoryDB
from offline.memory.workload_index import WorkloadIndex
from offline.replay.evaluator import ReplayEvaluator
from offline.replay.runner import ReplayRunner


def load_trace(state: dict[str, Any]) -> dict[str, Any]:
    trace_run = Path(state["trace_run_path"])
    meta = read_json(trace_run / "experiment_meta.json")
    return {
        "baseline_scheduler": "heuristic",
        "scenario_path": str(meta["scenario_path"]),
    }


def profile_workload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "workload_signature": WorkloadProfiler().profile(state["trace_run_path"]),
    }


def retrieve_similar_workloads(state: dict[str, Any]) -> dict[str, Any]:
    db = TraceMemoryDB(state["memory_path"])
    index = WorkloadIndex(db)
    return {
        "similar_cases": index.query_similar(
            state["workload_signature"], top_k=5
        )
    }


def analyze_scheduler_defects(state: dict[str, Any]) -> dict[str, Any]:
    findings = TraceAnalyzer(
        config_path=state.get("analyzer_config_path")
    ).analyze(state["trace_run_path"])
    refs: list[dict[str, Any]] = []
    for finding in findings:
        refs.extend(finding.get("evidence", []))
    return {
        "trace_findings": findings,
        "critical_trace_refs": refs[:8],
    }


def generate_advice_branches(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "advice_branches": AdviceGenerator().generate(
            workload_signature=state["workload_signature"],
            trace_findings=state["trace_findings"],
            similar_cases=state.get("similar_cases", []),
        )
    }


def generate_scheduler_candidates(state: dict[str, Any]) -> dict[str, Any]:
    prompt_output_dir = Path(state["replay_output"]) / "prompt_debug"
    return {
        "candidate_schedulers": CandidateGenerator().generate(
            advice_branches=state["advice_branches"],
            max_candidates=int(state.get("max_candidates", 2)),
            workload_signature=state["workload_signature"],
            trace_findings=state["trace_findings"],
            similar_cases=state.get("similar_cases", []),
            codegen_config_path=state.get("analyzer_config_path"),
            prompt_output_dir=str(prompt_output_dir),
        )
    }


def replay_candidates(state: dict[str, Any]) -> dict[str, Any]:
    runner = ReplayRunner()
    results = [
        runner.run(
            candidate=candidate,
            scenario_path=state["scenario_path"],
            replay_output=state["replay_output"],
        )
        for candidate in state["candidate_schedulers"]
    ]
    return {"replay_results": results}


def compare_candidates(state: dict[str, Any]) -> dict[str, Any]:
    evaluator = ReplayEvaluator()
    evaluated = evaluator.evaluate(
        baseline_trace_run=state["trace_run_path"],
        replay_results=state["replay_results"],
    )
    return {
        "replay_results": evaluated,
        "selected_candidate": evaluator.select_best(evaluated),
    }


def persist_memory(state: dict[str, Any]) -> dict[str, Any]:
    trace_run = Path(state["trace_run_path"])
    db = TraceMemoryDB(state["memory_path"])
    trace_run_id = db.ingest_trace_run(
        trace_run,
        signature=state["workload_signature"],
    )
    selected = state.get("selected_candidate") or {}
    index = WorkloadIndex(db)
    index.upsert_case(
        workload_signature=state["workload_signature"],
        scheduler_version=str(selected.get("candidate_id", "baseline")),
        trace_run=str(selected.get("trace_run", trace_run)),
        metrics=selected.get("metrics", {}),
        advice=state["advice_branches"],
    )
    result = {
        "evolution_run_id": state.get("evolution_run_id"),
        "trace_run_id": trace_run_id,
        "trace_run_path": str(trace_run),
        "workload_signature": state["workload_signature"],
        "similar_cases": state.get("similar_cases", []),
        "trace_findings": state["trace_findings"],
        "critical_trace_refs": state["critical_trace_refs"],
        "advice_branches": state["advice_branches"],
        "candidate_schedulers": state["candidate_schedulers"],
        "replay_results": state["replay_results"],
        "selected_candidate": state.get("selected_candidate"),
    }
    db.store_evolution_result(result)
    result_path = Path(state["replay_output"]) / "offline_evolution_result.json"
    write_json(result_path, result)
    record_offline_case(state | result, status="completed")
    return {"result_path": str(result_path)}


def record_offline_case(
    state: dict[str, Any],
    *,
    status: str,
    failed_stage: str | None = None,
    error: BaseException | None = None,
) -> dict[str, Any]:
    case = {
        "status": status,
        "evolution_run_id": state.get("evolution_run_id"),
        "trace_run_path": state.get("trace_run_path"),
        "scenario_path": state.get("scenario_path"),
        "baseline_scheduler": state.get("baseline_scheduler"),
        "workload_signature": state.get("workload_signature", {}),
        "similar_cases": state.get("similar_cases", []),
        "trace_findings": state.get("trace_findings", []),
        "critical_trace_refs": state.get("critical_trace_refs", []),
        "advice_branches": state.get("advice_branches", []),
        "candidate_schedulers": state.get("candidate_schedulers", []),
        "replay_results": state.get("replay_results", []),
        "selected_candidate": state.get("selected_candidate"),
    }
    if failed_stage is not None:
        case["failed_stage"] = failed_stage
    if error is not None:
        case["error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }
    case_path = Path(state["replay_output"]) / "offline_case.json"
    write_json(case_path, case)
    return {"case_path": str(case_path)}
