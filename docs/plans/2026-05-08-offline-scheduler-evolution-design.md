# Offline Scheduler Evolution Design

## Goal

Build an offline scheduler evolution subsystem under `offline/` that consumes replay-oriented trace runs, identifies defects in the current scheduler, generates natural-language and structured heuristic improvement advice, produces candidate scheduler variants, replays those candidates, and stores the workload-to-scheduler-to-trace history for future reuse.

The online simulator remains deterministic and versioned. Offline evolution proposes and validates new scheduler versions, but deployment remains an explicit later step.

## Scope

- Add an `offline/` subsystem driven by LangGraph.
- Ingest existing trace directories emitted by `scheduler_sim.app`.
- Analyze workload characteristics from scenario metadata, task definitions, scheduler observations, runtime execution, task outcomes, and `trace_summary.json`.
- Generate scheduler defect reports with key trace evidence.
- Generate multiple heuristic evolution branches from those reports.
- Replay candidate schedulers against the same scenario or trace-derived workload.
- Store workload signatures, trace summaries, advice, candidate schedulers, and replay results in a memory layer.
- Provide a vector-like workload index that maps similar workloads to historical schedulers and traces.

Out of scope for the first version:

- Automatic online deployment of evolved schedulers.
- Arbitrary unbounded LLM-generated Python execution.
- Real production vector databases.
- Learning a neural scheduler policy.
- Changing the trace contract unless an implementation gap blocks replay or attribution.

## Current Project Alignment

The design follows the source-of-truth requirements in:

- `docs/meta/need.md`
- `docs/meta/workload.md`
- `docs/meta/profiling.md`
- `docs/meta/trace.md`

The offline subsystem must preserve the online trace chain:

```text
workload release
-> scheduler observation
-> scheduler decision
-> runtime execution
-> task outcome
-> trace summary
```

The first version should consume the trace files already emitted by the app:

- `experiment_meta.json`
- `workload_events.jsonl`
- `task_definitions.jsonl`
- `task_outcomes.jsonl`
- `scheduler_observation.jsonl`
- `scheduler_decision.jsonl`
- `runtime_execution.jsonl`
- `trace_summary.json`

If additional trace files are later added, such as control-plane, contention, latency-model, or resource-snapshot traces, they should extend the analysis layer without changing the graph shape.

## Recommended Architecture

Use a modular offline package:

```text
offline/
|-- graph/
|   |-- state.py
|   |-- nodes.py
|   `-- workflow.py
|-- memory/
|   |-- schemas.py
|   |-- trace_store.py
|   `-- workload_index.py
|-- analysis/
|   |-- workload_profiler.py
|   |-- trace_analyzer.py
|   `-- advice.py
|-- evolution/
|   |-- proposal.py
|   |-- codegen.py
|   `-- registry.py
|-- replay/
|   |-- runner.py
|   `-- evaluator.py
`-- cli.py
```

This keeps the online simulator isolated from offline experimentation. The only shared contracts should be scheduler interfaces, scenario config, trace formats, and replay commands.

## LangGraph Workflow

The offline graph should be explicit and replayable:

```text
load_trace
-> profile_workload
-> retrieve_similar_workloads
-> analyze_scheduler_defects
-> generate_advice_branches
-> generate_scheduler_candidates
-> replay_candidates
-> compare_candidates
-> persist_memory
```

Optional iterative edge:

```text
compare_candidates
-> generate_advice_branches
```

The iterative edge is used only when all candidates fail to improve over baseline, or when replay identifies a new failure pattern.

## Graph State

The graph state should carry both natural-language reasoning and machine-checkable evidence:

```python
OfflineEvolutionState = {
    "trace_run_paths": list[str],
    "scenario_path": str,
    "baseline_scheduler": str,
    "workload_signature": dict,
    "similar_cases": list[dict],
    "trace_findings": list[dict],
    "critical_trace_refs": list[dict],
    "advice_branches": list[dict],
    "candidate_schedulers": list[dict],
    "replay_results": list[dict],
    "selected_candidate": dict | None,
}
```

The state should not store full trace files. It should store summaries and references to trace rows or files so that the memory layer remains compact.

## Core Modules

### Trace Memory DB

`TraceMemoryDB` is the factual memory layer. It ingests trace directories, stores normalized metadata, and keeps references to raw trace files.

First-version storage should be SQLite plus filesystem paths. This is enough for deterministic local development, easy inspection, and tests.

Minimum stored entities:

- Trace run metadata.
- Scenario and scheduler identity.
- Workload signature.
- Critical-task metrics.
- Agent-task metrics.
- Resource pressure summaries.
- Scheduler defect findings.
- Advice branches.
- Candidate scheduler versions.
- Replay results.

### Workload Profiler

`WorkloadProfiler` summarizes workload shape into a comparable signature.

Suggested features:

- `scene_complexity`
- critical node count
- minimum critical period
- average critical period
- high-criticality node count
- agent request count
- agent arrival density
- agent DAG depth
- agent DAG width
- CPU capacity
- memory capacity
- GPU capacity
- network capacity
- average CPU utilization
- average GPU utilization
- critical deadline miss rate
- average agent completion latency

This signature is used both for natural-language workload analysis and vector-like retrieval.

### Trace Critic Agent

The critic analyzes the current scheduler's defects from trace evidence.

It should answer:

- Which critical nodes missed deadlines?
- Did misses cluster near agent arrivals?
- Did the scheduler launch agent nodes too close to critical releases?
- Did resource pressure correlate with latency slowdown?
- Were some agent nodes starved for too long?
- Did the scheduler allocate resources conservatively or aggressively?
- Which trace rows support each conclusion?

Output should combine structured evidence and natural language:

```json
{
  "defect_type": "critical_deadline_miss",
  "severity": "high",
  "affected_nodes": ["localization_node"],
  "root_cause_hypothesis": "agent nodes consumed CPU during high-frequency critical releases",
  "evidence": [
    {
      "file": "trace_summary.json",
      "metric": "critical_task_metrics.localization_node.missed_deadline_count"
    },
    {
      "file": "scheduler_decision.jsonl",
      "timestamp_us": 1200000,
      "reason": "agent node selected while critical releases were pending"
    }
  ],
  "natural_language_advice": "Reserve CPU headroom before localization releases and delay low-criticality agent launches inside the guard window."
}
```

### Advice Generator

The advice generator converts findings into one or more heuristic evolution branches.

Each branch should include:

- Workload characterization.
- Scheduler defect summary.
- Key trace references.
- Proposed heuristic change.
- Expected metric impact.
- Possible regression risk.
- Replay acceptance criteria.

Example branches:

- Critical headroom reservation before high-frequency releases.
- Agent starvation boost after bounded waiting time.
- GPU-heavy agent launch throttling under high pressure.
- Deadline guard window around critical nodes.
- Critical-path-aware agent DAG prioritization.

### Scheduler Evolution Agent

The evolution agent should consume advice branches and generate scheduler candidates.

For the first version, candidates should be parameterized heuristic variants rather than arbitrary generated Python. Example:

```json
{
  "candidate_id": "critical_headroom_v1",
  "strategy": "parameterized_heuristic",
  "parameters": {
    "critical_cpu_reservation_ratio": 0.35,
    "deadline_guard_window_us": 30000,
    "agent_starvation_boost_after_us": 800000,
    "gpu_pressure_launch_threshold": 0.75
  },
  "source_advice_branch": "branch_001"
}
```

This keeps replay safe and makes scheduler differences easy to compare.

### Replay Evaluator

Replay runs each candidate against the same scenario and records the resulting trace directory.

The evaluator should compare each candidate against the baseline using `trace_summary.json`.

Hard rejection rules:

- Candidate increases critical deadline miss count.
- Candidate creates incomplete critical releases that baseline completed.
- Candidate fails to complete a replay.

Suggested score:

```text
score =
  - 1000 * critical_deadline_miss_rate
  - 10 * pending_critical_count
  - normalized_agent_avg_completion_time
  - 0.2 * normalized_agent_max_completion_time
```

The score is only for ranking candidates that pass hard safety rules.

### Workload Index

The workload index maps workload signatures to historical scheduler versions, advice, and trace evidence.

First-version API:

```python
upsert_case(workload_signature, scheduler_version, trace_run, metrics, advice)
query_similar(workload_signature, top_k=5)
```

The first implementation should use deterministic numeric feature vectors and nearest-neighbor distance. This avoids adding a production vector database before the offline loop has proven useful.

## Data Flow

### Ingestion

```text
trace directory
-> TraceMemoryDB.ingest_trace_run()
-> normalized trace metadata
-> workload signature
-> stored case
```

### Evolution

```text
baseline trace run
-> workload profiling
-> similar workload retrieval
-> defect analysis
-> advice branches
-> scheduler candidates
-> replay
-> candidate ranking
-> persisted evolution case
```

### Future Deployment

Deployment should be a separate explicit command:

```text
selected candidate
-> final replay validation
-> scheduler registry promotion
-> online scheduler config update
```

The offline graph should not silently replace the online scheduler.

## Modules To Replace After The Flow Runs

This section is intentionally explicit. The first implementation should optimize for a working closed loop, not perfect modeling.

### Replace: SQLite Trace Memory

Initial module:

- SQLite tables plus raw trace file paths.

Replace later with:

- DuckDB or a columnar trace warehouse if trace volume grows.
- A lakehouse-style layout if many experiments are stored.

Replacement trigger:

- Trace ingestion or analysis becomes slow.
- Queries need cross-run aggregation over many large JSONL files.

Keep stable:

- `TraceMemoryDB.ingest_trace_run`
- `TraceMemoryDB.get_trace_summary`
- `TraceMemoryDB.list_cases`
- `TraceMemoryDB.store_evolution_result`

### Replace: Deterministic Vector-Like Workload Index

Initial module:

- Handcrafted workload signature vector.
- Local nearest-neighbor search.

Replace later with:

- FAISS, Chroma, SQLite-vec, or another vector store.
- LLM embedding of workload summaries plus numeric features.

Replacement trigger:

- Similar workload retrieval misses obvious cases.
- Natural-language workload descriptions become important retrieval keys.
- The number of stored cases grows beyond simple local scan.

Keep stable:

- `WorkloadIndex.upsert_case`
- `WorkloadIndex.query_similar`
- `WorkloadSignature.to_vector`

### Replace: Rule-Based Trace Analyzer

Initial module:

- Deterministic metrics and heuristics over trace files.
- Optional LLM summarization over compact findings.

Replace later with:

- A stronger agentic analyzer that inspects selected trace windows.
- Causal counterfactual analysis over alternative scheduler decisions.
- Learned defect classifiers.

Replacement trigger:

- The analyzer gives shallow or repetitive advice.
- Candidate generation stops improving replay metrics.
- Trace volume contains enough examples to learn defect patterns.

Keep stable:

- `TraceAnalyzer.analyze(trace_run) -> list[TraceFinding]`
- `TraceFinding` schema with severity, evidence, and root-cause hypothesis.

### Replace: Parameterized Heuristic Candidate Generator

Initial module:

- Generate scheduler candidates as strategy names plus JSON parameters.
- Execute candidates through a fixed scheduler adapter.

Replace later with:

- DSL-generated scheduler policies.
- Constrained Python code generation.
- Evolutionary search over scheduler rule graphs.

Replacement trigger:

- Parameter tuning saturates.
- Needed policies cannot be represented by current parameters.
- Replay shows workload-specific behavior requires new decision logic.

Keep stable:

- `SchedulerCandidate` schema.
- `CandidateRegistry.register`
- `ReplayRunner.run_candidate`

### Replace: Single-Scenario Replay

Initial module:

- Replay candidate scheduler on the same scenario that produced the baseline trace.

Replace later with:

- Multi-scenario replay suites.
- Trace-derived stochastic workload variants.
- Stress tests for adversarial agent arrivals.

Replacement trigger:

- Candidates overfit one trace.
- A scheduler improves one workload but regresses related workloads.

Keep stable:

- `ReplayRunner.run(candidate, scenario_path) -> ReplayResult`
- `ReplayEvaluator.compare(baseline, candidates)`

### Replace: Simple Weighted Score

Initial module:

- Hard critical-task safety filters.
- Weighted scalar score for surviving candidates.

Replace later with:

- Multi-objective Pareto ranking.
- Safety-constrained optimization.
- Workload-specific utility functions.

Replacement trigger:

- Trade-offs between critical slack and agent latency become ambiguous.
- Multiple candidates are non-dominated.

Keep stable:

- `ReplayEvaluator.evaluate`
- `ReplayResult.metrics`
- `ReplayResult.accepted`

### Replace: Natural-Language Advice Prompt

Initial module:

- Prompt template over workload profile, findings, similar cases, and trace references.

Replace later with:

- Few-shot advice generation from successful historical evolutions.
- Retrieval-augmented advice using prior candidate outcomes.
- A multi-agent critic/proposer/verifier loop.

Replacement trigger:

- Advice does not predict replay outcomes.
- Similar workloads have useful prior evolution history.

Keep stable:

- `EvolutionAdvice` schema.
- `advice_branches` state key.

## Error Handling

- Missing required trace files should fail fast with the missing file list.
- Invalid JSONL rows should report file name and line number.
- Missing `trace_summary.json` should block candidate ranking.
- Replay failure should mark the candidate as rejected and preserve logs.
- Candidate scheduler import or construction failure should not fail the whole evolution run.
- The memory layer should never overwrite a prior scheduler version without a new version ID.

## Testing Strategy

Use the repository's required Python interpreter:

```text
/Users/lcjd/miniconda3/envs/agent/bin/python
```

Unit tests:

- Trace ingestion accepts a minimal valid trace directory.
- Workload profiler produces stable signatures from known traces.
- Workload index returns nearest similar cases.
- Trace analyzer detects critical deadline misses from `trace_summary.json`.
- Advice generator returns multiple branches with evidence references.
- Replay evaluator rejects candidates with worse critical miss counts.

Integration tests:

- Run the default scenario to produce a baseline trace.
- Ingest that trace into offline memory.
- Run one offline evolution pass with deterministic fake advice/candidates.
- Replay candidates.
- Persist selected result and verify it can be retrieved by workload signature.

End-to-end validation command shape:

```text
PYTHONPATH=src /Users/lcjd/miniconda3/envs/agent/bin/python -m scheduler_sim.app --scenario configs/scenarios/home_eqa_scenario_001.yaml --trace-output <dir>
PYTHONPATH=src /Users/lcjd/miniconda3/envs/agent/bin/python -m offline.cli evolve --trace-run <dir>/<run-id> --memory <offline-db>
```

## Acceptance Criteria

- Offline graph can run end-to-end on a trace produced by the default scenario.
- Trace critic emits at least one structured finding when critical deadline misses exist.
- Advice contains workload characteristics, defect summary, key trace references, and at least two heuristic branches.
- Candidate replay produces separate trace directories for each candidate.
- Replay evaluator ranks candidates and rejects safety regressions.
- Workload index stores and retrieves historical workload-to-scheduler-to-trace mappings.
- All offline commands use `/Users/lcjd/miniconda3/envs/agent/bin/python`.
