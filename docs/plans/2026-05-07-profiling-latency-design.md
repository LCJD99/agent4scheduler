# Profiling Latency Design

## Goal

Replace the runtime's fixed per-node latency with an online latency estimate driven by:

- `tool_name`
- scheduler-assigned `allocated_resources`
- scenario-level `scene_complexity`

## Scope

- Add `scene_complexity` to scenario config.
- Add explicit per-node resource allocation to `SchedulerDecision`.
- Load profiling data from `data/profiling_data.csv`.
- Train one estimator per tool from the profiling CSV.
- Recompute node base latency online when a node starts and when its allocation changes.
- Preserve the existing runtime pressure slowdown as a separate multiplicative penalty.

## Data Model

- `ScenarioSpec.scene_complexity: str`
- `WorkloadRelease.tool_name: str`
- `RunnableNode.tool_name: str`
- `ScheduledNodeAllocation(node, allocated_resources)`
- `RunningNode.tool_name: str`
- `RunningNode.allocated_resources: ResourceVector`

## Profiling Model

- Read `data/profiling_data.csv`.
- Filter rows by `tool_name`.
- Fit a per-tool model using the approach described in `docs/meta/profiling.md`:
  - log-transform numeric inputs
  - map `input_size` / `scene_complexity` from `small | medium | large` to ordinal values
  - polynomial features degree 2
  - standard scaling
  - `RidgeCV`
- Runtime inference uses:
  - `cpu_core`
  - `cpu_memory_mb`
  - `gpu_memory_mb`
  - `network_bandwidth_mbps`
  - `scene_complexity`

## Runtime Behavior

- Scheduler allocates resources per selected node.
- Control plane passes `tool_name` and `allocated_resources` into runtime.
- Runtime asks the profiling estimator for `predicted_latency_us`.
- Runtime stores the estimate as the node's current base latency.
- Tick progress still uses the existing pressure slowdown on top of the base latency.

## Error Handling

- Missing profiling CSV: fail fast.
- Missing tool rows in profiling CSV: fail fast.
- Invalid `scene_complexity`: fail fast.

## Trace Impact

- `experiment_meta.json`
  - `scene_complexity`
  - `profiling_data_path`
- `workload_events.jsonl`
  - `tool_name`
- `scheduler_decision.jsonl`
  - `allocated_resources`
  - `tool_name`
- `runtime_execution.jsonl`
  - `tool_name`
  - `allocated_resources`
  - `predicted_latency_us`
  - `scene_complexity`
