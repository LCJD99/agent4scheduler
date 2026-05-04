# Online Scheduler Sim Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a configuration-driven online scheduler simulator that runs critical periodic tasks and agent DAG tasks on a fixed-step runtime, applies resource contention penalties, and emits trace files for analysis.

**Architecture:** Use a Python `src` layout with explicit domain models, a fixed-tick simulation loop, a decoupled `Scheduler -> ControlPlane -> Runtime` execution path, and trace writers that mirror `docs/meta/trace.md`. Keep the first version deterministic, configurable, and easy to replace with future schedulers.

**Tech Stack:** Python 3.12, `PyYAML`, `pytest`, standard-library `dataclasses`, `pathlib`, `json`

---

## Assumptions

- The repository is effectively greenfield.
- Implementation should start with Python rather than a compiled language.
- The first runnable entrypoint should be a CLI-style script, not a service.
- Only the online path is implemented.

### Task 1: Bootstrap Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/scheduler_sim/__init__.py`
- Create: `src/scheduler_sim/app.py`
- Create: `tests/test_smoke.py`

**Step 1: Write the failing test**

```python
from scheduler_sim.app import main


def test_main_returns_zero_for_help_mode():
    assert main(["--help"]) == 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError` or `cannot import name 'main'`

**Step 3: Write minimal implementation**

```python
def main(argv: list[str] | None = None) -> int:
    if argv == ["--help"]:
        return 0
    return 0
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_smoke.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/scheduler_sim/__init__.py src/scheduler_sim/app.py tests/test_smoke.py
git commit -m "chore: bootstrap scheduler simulator package"
```

### Task 2: Add Config Schemas and YAML Loading

**Files:**
- Create: `src/scheduler_sim/config/models.py`
- Create: `src/scheduler_sim/config/loader.py`
- Create: `tests/config/test_loader.py`
- Create: `configs/tools/object_detection.yaml`
- Create: `configs/tasks/safe_navigation_task.yaml`
- Create: `configs/scenarios/home_eqa_scenario_001.yaml`

**Step 1: Write the failing test**

```python
from scheduler_sim.config.loader import load_scenario_bundle


def test_load_scenario_bundle_resolves_tool_task_and_scenario():
    bundle = load_scenario_bundle("configs/scenarios/home_eqa_scenario_001.yaml")
    assert bundle.scenario.metadata.name == "home_eqa_scenario_001"
    assert "object_detection" in bundle.tools
    assert "safe_navigation_task" in bundle.tasks
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/config/test_loader.py -v`
Expected: FAIL with missing loader or missing config model definitions

**Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class ScenarioBundle:
    scenario: ScenarioSpec
    tools: dict[str, ToolSpec]
    tasks: dict[str, TaskSpec]


def load_scenario_bundle(path: str) -> ScenarioBundle:
    ...
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/config/test_loader.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add configs src/scheduler_sim/config tests/config
git commit -m "feat: add scenario and tool config loading"
```

### Task 3: Implement Domain Models and DAG Validation

**Files:**
- Create: `src/scheduler_sim/domain/resources.py`
- Create: `src/scheduler_sim/domain/tasks.py`
- Create: `src/scheduler_sim/domain/nodes.py`
- Create: `tests/domain/test_task_graph.py`

**Step 1: Write the failing test**

```python
from scheduler_sim.domain.tasks import TaskGraph


def test_task_graph_rejects_cycles():
    graph = TaskGraph(
        nodes=["a", "b"],
        edges=[("a", "b"), ("b", "a")],
    )
    assert graph.validate().is_ok is False
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/domain/test_task_graph.py -v`
Expected: FAIL because `TaskGraph` or `validate` is missing

**Step 3: Write minimal implementation**

```python
class TaskGraph:
    def validate(self) -> ValidationResult:
        return detect_cycle(self.nodes, self.edges)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/domain/test_task_graph.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scheduler_sim/domain tests/domain
git commit -m "feat: add domain models and dag validation"
```

### Task 4: Implement Template-Based Online Planning Agent

**Files:**
- Create: `src/scheduler_sim/planner/templates.py`
- Create: `src/scheduler_sim/planner/agent.py`
- Create: `tests/planner/test_agent.py`

**Step 1: Write the failing test**

```python
from scheduler_sim.planner.agent import plan_request


def test_plan_request_returns_dag_template_for_known_prompt():
    dag = plan_request("What objects are on the table?")
    assert len(dag.nodes) >= 2
    assert dag.edges
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/planner/test_agent.py -v`
Expected: FAIL because the planner module does not exist

**Step 3: Write minimal implementation**

```python
def plan_request(user_request: str) -> PlannedDag:
    if "objects" in user_request.lower():
        return build_table_object_query_template()
    raise ValueError("unsupported request")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/planner/test_agent.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scheduler_sim/planner tests/planner
git commit -m "feat: add template based planning agent"
```

### Task 5: Implement Workload Release for Critical and Agent Tasks

**Files:**
- Create: `src/scheduler_sim/workload/generator.py`
- Create: `src/scheduler_sim/workload/instances.py`
- Create: `tests/workload/test_generator.py`

**Step 1: Write the failing test**

```python
from scheduler_sim.workload.generator import WorkloadGenerator


def test_generator_releases_periodic_critical_node_on_tick_boundary():
    generator = WorkloadGenerator(...)
    events = generator.release(timestamp_us=50000)
    assert any(event.node_id == "local_planner_node" for event in events)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/workload/test_generator.py -v`
Expected: FAIL because `WorkloadGenerator` does not exist

**Step 3: Write minimal implementation**

```python
class WorkloadGenerator:
    def release(self, timestamp_us: int) -> list[ReleaseEvent]:
        return self._release_critical(timestamp_us) + self._release_agent(timestamp_us)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/workload/test_generator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scheduler_sim/workload tests/workload
git commit -m "feat: add workload release logic"
```

### Task 6: Implement Latency Models and Contention Penalty

**Files:**
- Create: `src/scheduler_sim/latency/models.py`
- Create: `src/scheduler_sim/latency/estimator.py`
- Create: `tests/latency/test_estimator.py`

**Step 1: Write the failing test**

```python
from scheduler_sim.latency.estimator import estimate_node_progress


def test_contention_penalty_slows_effective_progress():
    free = estimate_node_progress(predicted_latency_us=1000, tick_us=100, penalty_multiplier=1.0)
    contended = estimate_node_progress(predicted_latency_us=1000, tick_us=100, penalty_multiplier=2.0)
    assert contended.progress_us < free.progress_us
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/latency/test_estimator.py -v`
Expected: FAIL because estimator functions are missing

**Step 3: Write minimal implementation**

```python
def estimate_node_progress(*, predicted_latency_us: int, tick_us: int, penalty_multiplier: float) -> ProgressSlice:
    return ProgressSlice(progress_us=tick_us / penalty_multiplier)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/latency/test_estimator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scheduler_sim/latency tests/latency
git commit -m "feat: add latency and contention estimator"
```

### Task 7: Implement Fixed-Step Runtime

**Files:**
- Create: `src/scheduler_sim/runtime/state.py`
- Create: `src/scheduler_sim/runtime/engine.py`
- Create: `tests/runtime/test_engine.py`

**Step 1: Write the failing test**

```python
from scheduler_sim.runtime.engine import RuntimeEngine


def test_runtime_completes_node_after_enough_ticks():
    engine = RuntimeEngine(...)
    engine.start_node(...)
    for _ in range(5):
        engine.advance_tick()
    assert engine.completed_count == 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/runtime/test_engine.py -v`
Expected: FAIL because runtime engine is missing

**Step 3: Write minimal implementation**

```python
class RuntimeEngine:
    def advance_tick(self) -> None:
        for node in self.running_nodes:
            node.remaining_work_us -= node.progress_us_per_tick
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/runtime/test_engine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scheduler_sim/runtime tests/runtime
git commit -m "feat: add fixed step runtime engine"
```

### Task 8: Implement Baseline Scheduler and Decision Model

**Files:**
- Create: `src/scheduler_sim/scheduler/base.py`
- Create: `src/scheduler_sim/scheduler/heuristic.py`
- Create: `tests/scheduler/test_heuristic.py`

**Step 1: Write the failing test**

```python
from scheduler_sim.scheduler.heuristic import HeuristicScheduler


def test_scheduler_prioritizes_critical_nodes_before_agent_nodes():
    scheduler = HeuristicScheduler()
    decision = scheduler.decide(observation=build_observation_with_critical_and_agent())
    assert decision.selected_nodes[0].criticality == "high"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/scheduler/test_heuristic.py -v`
Expected: FAIL because the scheduler implementation is missing

**Step 3: Write minimal implementation**

```python
class HeuristicScheduler(BaseScheduler):
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        ordered = sort_critical_first(observation.runnable_nodes)
        return allocate_minimum_then_best_effort(ordered, observation.available_resources)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/scheduler/test_heuristic.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scheduler_sim/scheduler tests/scheduler
git commit -m "feat: add baseline heuristic scheduler"
```

### Task 9: Implement Scheduler Control Plane

**Files:**
- Create: `src/scheduler_sim/runtime/control_plane.py`
- Create: `tests/runtime/test_control_plane.py`

**Step 1: Write the failing test**

```python
from scheduler_sim.runtime.control_plane import SchedulerControlPlane


def test_control_plane_starts_selected_nodes_in_runtime():
    control_plane = SchedulerControlPlane(...)
    control_plane.apply(decision=build_decision_with_one_node())
    assert control_plane.runtime.running_count == 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/runtime/test_control_plane.py -v`
Expected: FAIL because the control plane does not exist

**Step 3: Write minimal implementation**

```python
class SchedulerControlPlane:
    def apply(self, decision: SchedulerDecision) -> ApplyResult:
        for selected in decision.selected_nodes:
            self.runtime.start_node(selected)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/runtime/test_control_plane.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scheduler_sim/runtime/control_plane.py tests/runtime/test_control_plane.py
git commit -m "feat: add scheduler control plane"
```

### Task 10: Implement Trace Writers

**Files:**
- Create: `src/scheduler_sim/trace/writer.py`
- Create: `src/scheduler_sim/trace/events.py`
- Create: `tests/integration/test_trace_writer.py`

**Step 1: Write the failing test**

```python
from scheduler_sim.trace.writer import TraceWriter


def test_trace_writer_emits_required_files(tmp_path):
    writer = TraceWriter(output_dir=tmp_path)
    writer.write_experiment_meta({"experiment_id": "exp_001"})
    assert (tmp_path / "experiment_meta.json").exists()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_trace_writer.py -v`
Expected: FAIL because the trace writer is missing

**Step 3: Write minimal implementation**

```python
class TraceWriter:
    def write_experiment_meta(self, payload: dict) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "experiment_meta.json").write_text(json.dumps(payload))
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_trace_writer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scheduler_sim/trace tests/integration
git commit -m "feat: add trace writer"
```

### Task 11: Wire End-to-End Simulation Runner

**Files:**
- Modify: `src/scheduler_sim/app.py`
- Create: `tests/integration/test_end_to_end.py`

**Step 1: Write the failing test**

```python
from scheduler_sim.app import main


def test_end_to_end_scenario_runs_and_emits_trace(tmp_path):
    code = main(
        [
            "--scenario",
            "configs/scenarios/home_eqa_scenario_001.yaml",
            "--trace-output",
            str(tmp_path),
        ]
    )
    assert code == 0
    assert (tmp_path / "experiment_meta.json").exists()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_end_to_end.py -v`
Expected: FAIL because the app does not wire together the simulation loop

**Step 3: Write minimal implementation**

```python
def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    bundle = load_scenario_bundle(args.scenario)
    sim = build_simulation(bundle, trace_output=args.trace_output)
    sim.run()
    return 0
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_end_to_end.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scheduler_sim/app.py tests/integration/test_end_to_end.py
git commit -m "feat: wire end to end simulation runner"
```

### Task 12: Run Full Verification and Clean Up

**Files:**
- Create: `README.md`
- Modify: `docs/plans/2026-05-04-online-scheduler-sim-design.md`
- Modify: `docs/plans/2026-05-04-online-scheduler-sim.md`

**Step 1: Write the failing test**

```python
def test_placeholder():
    assert True
```

**Step 2: Run verification**

Run: `python -m pytest -v`
Expected: PASS across all tests

**Step 3: Write minimal implementation**

```text
Document the final CLI usage, scenario layout, and trace outputs.
```

**Step 4: Run final checks**

Run: `python -m pytest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md docs/plans/2026-05-04-online-scheduler-sim-design.md docs/plans/2026-05-04-online-scheduler-sim.md
git commit -m "docs: finalize simulator implementation guidance"
```

## Task 12 Completion Notes

- `README.md` documents the current CLI entrypoint, the scenario -> task -> tool config layout, and the single trace artifact emitted by the implemented flow.
- `docs/plans/2026-05-04-online-scheduler-sim-design.md` now distinguishes between the target architecture and the currently implemented minimal path.
- This cleanup intentionally does not claim that a full simulator loop, runtime execution pipeline, or complete trace suite exists yet.

Plan complete and saved to `docs/plans/2026-05-04-online-scheduler-sim.md`. Two execution options:

**1. Subagent-Driven (this session)** - dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - open a new session with executing-plans, batch execution with checkpoints
