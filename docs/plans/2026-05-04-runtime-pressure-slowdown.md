# Runtime Pressure Slowdown Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a simple resource-pressure slowdown model that degrades runtime progress under higher utilization while leaving admission rules unchanged.

**Architecture:** Keep the logic local to the runtime engine. Compute a per-tick pressure multiplier from current allocated versus system capacity, apply it when recalculating each running node's tick progress, and expose utilization plus slowdown fields in runtime trace payloads.

**Tech Stack:** Python, pytest

---

### Task 1: Add failing runtime tests

**Files:**
- Modify: `tests/runtime/test_engine.py`
- Modify: `tests/integration/test_end_to_end.py`

**Step 1: Write the failing test**

Add a runtime test that compares the same node's remaining work under light load versus higher concurrent load, and assert the high-pressure case advances less in one tick. Add a minimal end-to-end assertion that `runtime_execution.jsonl` contains pressure trace fields.

**Step 2: Run test to verify it fails**

Run: `/Users/lcjd/miniconda3/envs/agent/bin/python -m pytest -v tests/runtime/test_engine.py tests/integration/test_end_to_end.py`

Expected: FAIL because the runtime payload does not yet include pressure fields and progress does not yet depend on resource pressure.

### Task 2: Implement runtime pressure slowdown

**Files:**
- Modify: `src/scheduler_sim/runtime/engine.py`
- Modify: `src/scheduler_sim/runtime/state.py`

**Step 1: Write minimal implementation**

Add helpers in the runtime engine to compute utilization ratios and a `1.0 + max_utilization` slowdown multiplier, compute per-node progress slices during each tick, and include the new trace-facing fields in the runtime payload.

**Step 2: Run tests to verify they pass**

Run: `/Users/lcjd/miniconda3/envs/agent/bin/python -m pytest -v tests/runtime/test_engine.py tests/integration/test_end_to_end.py`

Expected: PASS

### Task 3: Full verification

**Files:**
- No additional file changes expected

**Step 1: Run the full suite**

Run: `/Users/lcjd/miniconda3/envs/agent/bin/python -m pytest -v`

Expected: PASS
