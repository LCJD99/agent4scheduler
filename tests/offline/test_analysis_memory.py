import json

from offline.analysis.trace_analyzer import TraceAnalyzer
from offline.analysis.workload_profiler import WorkloadProfiler
from offline.memory.trace_store import TraceMemoryDB
from offline.memory.workload_index import WorkloadIndex


def write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def create_trace_run(tmp_path):
    trace_run = tmp_path / "trace-001"
    trace_run.mkdir()
    (trace_run / "experiment_meta.json").write_text(
        json.dumps(
            {
                "scenario_name": "home_eqa",
                "scenario_path": "configs/scenarios/home_eqa_scenario_001.yaml",
                "trace_run_id": "trace-001",
                "scene_complexity": "large",
                "tick_us": 10_000,
                "duration_us": 100_000,
                "system_capacity": {
                    "cpu_cores": 4.0,
                    "memory_mb": 4096,
                    "gpu_vram_mb": 8192,
                    "network_mbps": 1000.0,
                },
            }
        ),
        encoding="utf-8",
    )
    write_jsonl(
        trace_run / "task_definitions.jsonl",
        [
            {
                "definition_type": "scenario_critical_task",
                "node_id": "localization_node",
                "criticality": "high",
                "period_us": 20_000,
            },
            {
                "definition_type": "agent_task",
                "task_instance_id": "agent-1",
                "nodes": [{"node_id": "a"}, {"node_id": "b"}],
                "edges": [{"src": "a", "dst": "b"}],
            },
        ],
    )
    write_jsonl(
        trace_run / "workload_events.jsonl",
        [
            {
                "event_type": "workload_release",
                "timestamp_us": 0,
                "source": "critical",
                "node_id": "localization_node",
            },
            {
                "event_type": "workload_release",
                "timestamp_us": 10_000,
                "source": "agent",
                "node_id": "image_captioning",
            },
        ],
    )
    write_jsonl(
        trace_run / "runtime_execution.jsonl",
        [
            {
                "resource_utilization": {
                    "cpu_cores": 0.8,
                    "memory_mb": 0.2,
                    "gpu_vram_mb": 0.5,
                    "network_mbps": 0.1,
                }
            }
        ],
    )
    write_jsonl(trace_run / "scheduler_observation.jsonl", [])
    write_jsonl(trace_run / "scheduler_decision.jsonl", [])
    write_jsonl(
        trace_run / "task_outcomes.jsonl",
        [
            {
                "outcome_type": "critical_release",
                "node_id": "localization_node",
                "completed": True,
                "missed_deadline": True,
            }
        ],
    )
    (trace_run / "trace_summary.json").write_text(
        json.dumps(
            {
                "critical_task_metrics": {
                    "localization_node": {
                        "total_release_count": 10,
                        "missed_deadline_count": 2,
                        "frequency_satisfaction_rate": 0.8,
                    }
                },
                "agent_task_metrics": {
                    "instances": [
                        {
                            "task_instance_id": "agent-1",
                            "total_completion_time_us": 60_000,
                        }
                    ],
                    "aggregate": {
                        "completed_instance_count": 1,
                        "avg_total_completion_time_us": 60_000,
                        "max_total_completion_time_us": 60_000,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return trace_run


def test_profiler_analyzer_and_memory_index_trace_run(tmp_path):
    trace_run = create_trace_run(tmp_path)
    profiler = WorkloadProfiler()
    analyzer = TraceAnalyzer()

    signature = profiler.profile(trace_run)
    findings = analyzer.analyze(trace_run)

    assert signature["scene_complexity"] == "large"
    assert signature["critical_node_count"] == 1
    assert signature["agent_request_count"] == 1
    assert signature["critical_deadline_miss_rate"] == 0.2
    assert findings[0]["defect_type"] == "critical_deadline_miss"
    assert findings[0]["affected_nodes"] == ["localization_node"]

    db = TraceMemoryDB(tmp_path / "offline.db")
    case_id = db.ingest_trace_run(trace_run, signature=signature)
    index = WorkloadIndex(db)
    index.upsert_case(
        workload_signature=signature,
        scheduler_version="baseline",
        trace_run=str(trace_run),
        metrics={"score": -1.0},
        advice=[{"branch_id": "branch_critical_headroom"}],
    )

    similar = index.query_similar(signature, top_k=1)

    assert case_id
    assert similar[0]["scheduler_version"] == "baseline"
