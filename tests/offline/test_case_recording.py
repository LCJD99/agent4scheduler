import json

from offline.graph import nodes


def test_record_offline_case_writes_failed_case_with_trace_findings_and_candidate_source(tmp_path):
    replay_output = tmp_path / "replays" / "20260512-150000"
    state = {
        "trace_run_path": "/tmp/trace-run",
        "replay_output": str(replay_output),
        "evolution_run_id": "20260512-150000",
        "workload_signature": {"scene_complexity": "large"},
        "similar_cases": [],
        "trace_findings": [
            {
                "defect_type": "critical_deadline_miss",
                "natural_language_advice": "reserve CPU headroom",
            }
        ],
        "critical_trace_refs": [{"file": "trace_summary.json"}],
        "advice_branches": [
            {
                "branch_id": "branch_critical_headroom",
                "proposed_heuristic_change": "Reserve CPU headroom.",
            }
        ],
        "candidate_schedulers": [
            {
                "candidate_id": "candidate_1_branch_critical_headroom",
                "scheduler_source": "def create_scheduler(parameters=None):\n    return None\n",
                "codegen_rationale": "bad generated code",
                "prompt_markdown_path": "/tmp/prompt.md",
            }
        ],
    }

    result = nodes.record_offline_case(
        state,
        status="failed",
        failed_stage="replay_candidates",
        error=RuntimeError("generated scheduler failed"),
    )

    case_path = replay_output / "offline_case.json"
    case = json.loads(case_path.read_text(encoding="utf-8"))

    assert result == {"case_path": str(case_path)}
    assert case["status"] == "failed"
    assert case["evolution_run_id"] == "20260512-150000"
    assert case["failed_stage"] == "replay_candidates"
    assert "generated scheduler failed" in case["error"]["message"]
    assert case["trace_findings"][0]["defect_type"] == "critical_deadline_miss"
    assert case["advice_branches"][0]["branch_id"] == "branch_critical_headroom"
    assert "def create_scheduler" in case["candidate_schedulers"][0]["scheduler_source"]
    assert case["candidate_schedulers"][0]["prompt_markdown_path"] == "/tmp/prompt.md"
