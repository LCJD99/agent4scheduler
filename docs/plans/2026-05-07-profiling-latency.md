# Profiling Latency Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace fixed node latency with an online profiling-based latency estimate driven by tool name, allocated resources, and scenario scene complexity.

**Architecture:** Add scene complexity to scenario config, carry tool identity through workload and scheduler data structures, add explicit scheduler allocations, and load a per-tool profiling estimator from `data/profiling_data.csv`. Runtime will use the estimator when nodes start so trace output reflects allocation-aware latency.

**Tech Stack:** Python 3.12, pytest, pandas, numpy, scikit-learn, YAML config loader

---

### Task 1: Extend configuration and workload metadata

**Files:**
- Modify: `src/scheduler_sim/config/models.py`
- Modify: `src/scheduler_sim/config/loader.py`
- Modify: `src/scheduler_sim/workload/instances.py`
- Modify: `src/scheduler_sim/workload/generator.py`
- Modify: `configs/scenarios/home_eqa_scenario_001.yaml`
- Test: `tests/config/test_loader.py`
- Test: `tests/workload/test_generator.py`

**Step 1: Write the failing tests**

- Assert scenario loader returns `scene_complexity`.
- Assert workload releases carry `tool_name`.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/config/test_loader.py tests/workload/test_generator.py -v`

**Step 3: Write minimal implementation**

- Add `scene_complexity` to `ScenarioSpec`.
- Parse `scene_complexity` from scenario YAML.
- Add `tool_name` to `WorkloadRelease`, `CriticalTaskSpec`, and generated releases.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/config/test_loader.py tests/workload/test_generator.py -v`

**Step 5: Commit**

```bash
git add src/scheduler_sim/config/models.py src/scheduler_sim/config/loader.py src/scheduler_sim/workload/instances.py src/scheduler_sim/workload/generator.py configs/scenarios/home_eqa_scenario_001.yaml tests/config/test_loader.py tests/workload/test_generator.py
git commit -m "feat: carry scene complexity and tool metadata"
```

### Task 2: Add profiling estimator

**Files:**
- Create: `src/scheduler_sim/profiling/estimator.py`
- Create: `tests/profiling/test_estimator.py`
- Create: `data/profiling_data.csv`

**Step 1: Write the failing tests**

- Assert estimator loads profiling CSV.
- Assert estimator returns positive latency for a known tool.
- Assert estimator raises on missing tool rows.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/profiling/test_estimator.py -v`

**Step 3: Write minimal implementation**

- Build per-tool sklearn pipelines from the profiling CSV.
- Map `small | medium | large` to numeric complexity.
- Return integer latency predictions.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/profiling/test_estimator.py -v`

**Step 5: Commit**

```bash
git add src/scheduler_sim/profiling/estimator.py tests/profiling/test_estimator.py data/profiling_data.csv
git commit -m "feat: add tool profiling estimator"
```

### Task 3: Add explicit scheduler allocations

**Files:**
- Modify: `src/scheduler_sim/scheduler/base.py`
- Modify: `src/scheduler_sim/scheduler/heuristic.py`
- Modify: `src/scheduler_sim/runtime/control_plane.py`
- Test: `tests/scheduler/test_heuristic.py`
- Test: `tests/runtime/test_control_plane.py`

**Step 1: Write the failing tests**

- Assert scheduler decisions contain allocations.
- Assert control plane passes allocated resources into runtime.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/scheduler/test_heuristic.py tests/runtime/test_control_plane.py -v`

**Step 3: Write minimal implementation**

- Add `ScheduledNodeAllocation`.
- Change `SchedulerDecision` to use allocations.
- Update heuristic scheduler to allocate each node's requested resources.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/scheduler/test_heuristic.py tests/runtime/test_control_plane.py -v`

**Step 5: Commit**

```bash
git add src/scheduler_sim/scheduler/base.py src/scheduler_sim/scheduler/heuristic.py src/scheduler_sim/runtime/control_plane.py tests/scheduler/test_heuristic.py tests/runtime/test_control_plane.py
git commit -m "feat: add explicit scheduler allocations"
```

### Task 4: Connect runtime to profiling estimator

**Files:**
- Modify: `src/scheduler_sim/runtime/state.py`
- Modify: `src/scheduler_sim/runtime/engine.py`
- Modify: `src/scheduler_sim/app.py`
- Test: `tests/runtime/test_engine.py`
- Test: `tests/integration/test_end_to_end.py`

**Step 1: Write the failing tests**

- Assert runtime computes predicted latency from the profiling estimator.
- Assert trace contains `tool_name`, `allocated_resources`, `scene_complexity`, and profiling metadata.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/runtime/test_engine.py tests/integration/test_end_to_end.py -v`

**Step 3: Write minimal implementation**

- Inject profiling estimator and scene complexity into runtime.
- Use `tool_name + allocated_resources + scene_complexity` to compute node latency on start.
- Extend traces and experiment meta.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/runtime/test_engine.py tests/integration/test_end_to_end.py -v`

**Step 5: Commit**

```bash
git add src/scheduler_sim/runtime/state.py src/scheduler_sim/runtime/engine.py src/scheduler_sim/app.py tests/runtime/test_engine.py tests/integration/test_end_to_end.py
git commit -m "feat: use profiling latency in runtime"
```
