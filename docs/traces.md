# Unified Trace Specification

## Purpose

This document is the canonical trace contract for both online simulation and offline scheduler evolution.

Online components must write traces that follow this specification. Offline components must read traces through this same specification and must not depend on hidden online implementation details.

The trace must answer four questions:

- What workload and system state did the scheduler see?
- What decision did the scheduler make?
- What did the runtime execute?
- What happened to critical-task deadlines and agent-task completion latency?

`docs/meta/trace.md` remains background design material. This file is the shared implementation contract.

## Trace Run Layout

Each simulation run writes one trace directory:

```text
<trace-output>/<trace-run-id>/
|-- experiment_meta.json
|-- workload_events.jsonl
|-- task_definitions.jsonl
|-- task_outcomes.jsonl
|-- scheduler_observation.jsonl
|-- scheduler_decision.jsonl
|-- runtime_execution.jsonl
`-- trace_summary.json
```

These files are required for a complete trace run. Offline readers must reject trace runs that miss any required file.

Future optional files may be added, but they must not replace the required files:

- `control_plane_events.jsonl`
- `resource_snapshots.jsonl`
- `contention_events.jsonl`
- `latency_model_calls.jsonl`
- `agent_task_progress.jsonl`

## Common Field Rules

- Time fields use integer microseconds and end with `_us`.
- Resource fields use the canonical resource vector:

```json
{
  "cpu_cores": 1.0,
  "memory_mb": 512,
  "gpu_vram_mb": 0,
  "network_mbps": 0.0
}
```

- `source` must be either `critical` or `agent` when describing node origin.
- `criticality` must be one of `high`, `medium`, or `low`.
- `node_instance_id` uniquely identifies a released node instance.
- `task_instance_id` identifies the critical release instance or agent DAG instance that owns the node instance.
- JSONL files contain one JSON object per line. Blank lines are ignored by readers.
- Writers should preserve field names exactly. Readers may ignore unknown additive fields.

## Event Chain

Every trace should preserve this replay chain:

```text
task_definitions.jsonl
-> workload_events.jsonl
-> scheduler_observation.jsonl
-> scheduler_decision.jsonl
-> runtime_execution.jsonl
-> task_outcomes.jsonl
-> trace_summary.json
```

Offline analysis and replay compare scheduler behavior by following this chain.

## `experiment_meta.json`

Records run-level metadata needed for replay and attribution.

Required fields:

- `scenario_name`: scenario metadata name.
- `scenario_path`: path to the scenario YAML used for the run.
- `trace_run_id`: trace directory ID.
- `trace_output_dir`: absolute trace directory path.
- `profiling_data_path`: profiling CSV path.
- `scene_complexity`: `small`, `medium`, or `large`.
- `task_names`: sorted task names loaded by the scenario.
- `tool_names`: sorted tool names loaded by the scenario.
- `agent_request_ids`: request IDs configured in the scenario.
- `critical_task_count`: number of critical nodes loaded from task configs.
- `agent_request_count`: number of configured agent requests.
- `tick_us`: simulation tick duration.
- `duration_us`: simulation duration.
- `system_capacity`: canonical resource vector.

Example:

```json
{
  "scenario_name": "home_eqa_scenario_001",
  "scenario_path": "/repo/configs/scenarios/home_eqa_scenario_001.yaml",
  "trace_run_id": "20260508-153000",
  "trace_output_dir": "/tmp/traces/20260508-153000",
  "profiling_data_path": "/repo/data/profiling_data.csv",
  "scene_complexity": "large",
  "task_names": ["safe_navigation_task"],
  "tool_names": ["image_captioning", "localization_node"],
  "agent_request_ids": ["agent_request_001"],
  "critical_task_count": 3,
  "agent_request_count": 1,
  "tick_us": 10000,
  "duration_us": 1000000,
  "system_capacity": {
    "cpu_cores": 4.0,
    "memory_mb": 4096,
    "gpu_vram_mb": 8192,
    "network_mbps": 1000.0
  }
}
```

## `task_definitions.jsonl`

Records static and dynamic task definitions.

### Critical Task Definition

Critical task definitions are emitted at run start.

Required fields:

- `event_type`: `task_definition`.
- `definition_type`: `scenario_critical_task`.
- `task_instance_id`: scenario task name.
- `task_name`: scenario task name.
- `node_id`: critical node ID.
- `tool_name`: tool used by the node.
- `criticality`: criticality level.
- `period_us`: node release period and default deadline interval.
- `predicted_latency_us`: config-level predicted latency value.
- `resource_demand`: canonical resource vector.

Example:

```json
{
  "event_type": "task_definition",
  "definition_type": "scenario_critical_task",
  "task_instance_id": "safe_navigation_task",
  "task_name": "safe_navigation_task",
  "node_id": "localization_node",
  "tool_name": "localization_node",
  "criticality": "high",
  "period_us": 20000,
  "predicted_latency_us": 18000,
  "resource_demand": {
    "cpu_cores": 1.0,
    "memory_mb": 512,
    "gpu_vram_mb": 0,
    "network_mbps": 0.0
  }
}
```

### Agent Task Definition

Agent task definitions are emitted when an agent DAG instance is created.

Required fields:

- `event_type`: `task_definition`.
- `definition_type`: `agent_task_instance`.
- `task_instance_id`: unique agent DAG instance ID.
- `request_id`: scenario request ID.
- `arrival_time_us`: agent request arrival time.
- `criticality`: criticality assigned to this agent task.
- `user_request`: original user request text.
- `node_ids`: DAG node IDs.
- `edges`: DAG edges as `[src, dst]` pairs.
- `tool_map`: mapping from DAG node ID to tool name.

Example:

```json
{
  "event_type": "task_definition",
  "definition_type": "agent_task_instance",
  "task_instance_id": "caption-request-00020000-001",
  "request_id": "caption_request",
  "arrival_time_us": 20000,
  "criticality": "low",
  "user_request": "caption and translate the scene",
  "node_ids": ["image_captioning", "text_translation", "text_to_speech"],
  "edges": [["image_captioning", "text_translation"], ["text_translation", "text_to_speech"]],
  "tool_map": {
    "image_captioning": "image_captioning",
    "text_translation": "text_translation",
    "text_to_speech": "text_to_speech"
  }
}
```

## `workload_events.jsonl`

Records node releases entering the scheduler's pending set.

Required fields:

- `event_type`: `workload_release`.
- `timestamp_us`: release time.
- `node_id`: node ID in the task or DAG.
- `tool_name`: runtime tool name.
- `node_instance_id`: unique node instance ID.
- `task_instance_id`: owning task or DAG instance ID.
- `source`: `critical` or `agent`.
- `criticality`: node criticality.
- `predicted_latency_us`: config-level predicted latency value.
- `period_us`: period for critical nodes, `null` for agent nodes.
- `resource_demand`: canonical resource vector.
- `predecessor_instance_ids`: completed predecessor node instance IDs required before this release.

Example:

```json
{
  "event_type": "workload_release",
  "timestamp_us": 20000,
  "node_id": "image_captioning",
  "tool_name": "image_captioning",
  "node_instance_id": "caption-request-00020000-001--image_captioning--0",
  "task_instance_id": "caption-request-00020000-001",
  "source": "agent",
  "criticality": "low",
  "predicted_latency_us": 450000,
  "period_us": null,
  "resource_demand": {
    "cpu_cores": 1.0,
    "memory_mb": 512,
    "gpu_vram_mb": 2048,
    "network_mbps": 0.0
  },
  "predecessor_instance_ids": []
}
```

## `scheduler_observation.jsonl`

Records the exact scheduler input at a scheduling point.

Required fields:

- `event_type`: `scheduler_observation`.
- `timestamp_us`: observation time.
- `available_resources`: canonical resource vector available before the decision.
- `runnable_nodes`: nodes available to launch.
- `running_nodes`: nodes already running.

Each runnable node must include:

- `node_id`
- `node_instance_id`
- `task_instance_id`
- `tool_name`
- `source`
- `criticality`
- `predicted_latency_us`
- `released_at_us`
- `resource_demand`

Each running node must include:

- `node_id`
- `node_instance_id`
- `task_instance_id`
- `tool_name`
- `source`
- `criticality`
- `predicted_latency_us`
- `started_at_us`
- `allocated_resources`
- `resource_demand`

Example:

```json
{
  "event_type": "scheduler_observation",
  "timestamp_us": 30000,
  "available_resources": {
    "cpu_cores": 2.0,
    "memory_mb": 2048,
    "gpu_vram_mb": 4096,
    "network_mbps": 1000.0
  },
  "runnable_nodes": [
    {
      "node_id": "localization_node",
      "node_instance_id": "critical-localization-node-00002--localization_node--0",
      "task_instance_id": "critical-localization-node-00002",
      "tool_name": "localization_node",
      "source": "critical",
      "criticality": "high",
      "predicted_latency_us": 18000,
      "released_at_us": 30000,
      "resource_demand": {
        "cpu_cores": 1.0,
        "memory_mb": 512,
        "gpu_vram_mb": 0,
        "network_mbps": 0.0
      }
    }
  ],
  "running_nodes": []
}
```

## `scheduler_decision.jsonl`

Records scheduler output after an observation.

Required fields:

- `event_type`: `scheduler_decision`.
- `timestamp_us`: decision time.
- `selected_nodes`: nodes accepted by the control plane/runtime for launch.

Each selected node must include:

- `node_id`
- `node_instance_id`
- `task_instance_id`
- `tool_name`
- `source`
- `criticality`
- `predicted_latency_us`
- `allocated_resources`
- `resource_demand`

`allocated_resources` is the scheduler decision. It must not be inferred from `resource_demand` by offline readers, even if a specific scheduler currently sets allocation equal to demand.

Example:

```json
{
  "event_type": "scheduler_decision",
  "timestamp_us": 30000,
  "selected_nodes": [
    {
      "node_id": "localization_node",
      "node_instance_id": "critical-localization-node-00002--localization_node--0",
      "task_instance_id": "critical-localization-node-00002",
      "tool_name": "localization_node",
      "source": "critical",
      "criticality": "high",
      "predicted_latency_us": 18000,
      "allocated_resources": {
        "cpu_cores": 1.0,
        "memory_mb": 512,
        "gpu_vram_mb": 0,
        "network_mbps": 0.0
      },
      "resource_demand": {
        "cpu_cores": 1.0,
        "memory_mb": 512,
        "gpu_vram_mb": 0,
        "network_mbps": 0.0
      }
    }
  ]
}
```

## `runtime_execution.jsonl`

Records runtime state and completions after each tick.

Required fields:

- `timestamp_us`: tick start time.
- `allocated_resources`: aggregate allocated resource vector.
- `resource_utilization`: utilization ratios keyed by resource name.
- `resource_pressure_multiplier`: runtime slowdown multiplier.
- `running_nodes`: still-running node instances after the tick.
- `completed_node_instance_ids`: node instance IDs completed in this tick.
- `completed_nodes`: completed node payloads.

Each running node should include:

- `node_id`
- `tool_name`
- `node_instance_id`
- `task_instance_id`
- `source`
- `criticality`
- `remaining_work_us`
- `predicted_latency_us`
- `started_at_us`
- `tick_progress_us`
- `resource_pressure_multiplier`
- `scene_complexity`
- `allocated_resources`
- `resource_demand`

Each completed node should include:

- `node_id`
- `tool_name`
- `node_instance_id`
- `task_instance_id`
- `source`
- `criticality`
- `started_at_us`
- `completed_at_us`
- `predicted_latency_us`
- `tick_progress_us`
- `resource_pressure_multiplier`
- `allocated_resources`
- `resource_demand`

Example:

```json
{
  "timestamp_us": 30000,
  "allocated_resources": {
    "cpu_cores": 1.0,
    "memory_mb": 512,
    "gpu_vram_mb": 0,
    "network_mbps": 0.0
  },
  "resource_utilization": {
    "cpu_cores": 0.25,
    "memory_mb": 0.125,
    "gpu_vram_mb": 0.0,
    "network_mbps": 0.0
  },
  "resource_pressure_multiplier": 1.25,
  "running_nodes": [],
  "completed_node_instance_ids": [
    "critical-localization-node-00002--localization_node--0"
  ],
  "completed_nodes": [
    {
      "node_id": "localization_node",
      "tool_name": "localization_node",
      "node_instance_id": "critical-localization-node-00002--localization_node--0",
      "task_instance_id": "critical-localization-node-00002",
      "source": "critical",
      "criticality": "high",
      "started_at_us": 30000,
      "completed_at_us": 40000,
      "predicted_latency_us": 18000,
      "tick_progress_us": 10000,
      "resource_pressure_multiplier": 1.25,
      "allocated_resources": {
        "cpu_cores": 1.0,
        "memory_mb": 512,
        "gpu_vram_mb": 0,
        "network_mbps": 0.0
      },
      "resource_demand": {
        "cpu_cores": 1.0,
        "memory_mb": 512,
        "gpu_vram_mb": 0,
        "network_mbps": 0.0
      }
    }
  ]
}
```

## `task_outcomes.jsonl`

Records task-level outcomes.

### Critical Release Outcome

Required fields:

- `event_type`: `task_outcome`.
- `outcome_type`: `critical_release`.
- `task_instance_id`: critical release instance ID.
- `node_id`: critical node ID.
- `node_instance_id`: node instance ID.
- `criticality`: criticality level.
- `released_at_us`: release time.
- `completed_at_us`: completion time, or `null` if incomplete.
- `deadline_us`: deadline time.
- `period_us`: period interval.
- `completed`: boolean.
- `missed_deadline`: boolean.

Example:

```json
{
  "event_type": "task_outcome",
  "outcome_type": "critical_release",
  "task_instance_id": "critical-localization-node-00002",
  "node_id": "localization_node",
  "node_instance_id": "critical-localization-node-00002--localization_node--0",
  "criticality": "high",
  "released_at_us": 30000,
  "completed_at_us": 40000,
  "deadline_us": 50000,
  "period_us": 20000,
  "completed": true,
  "missed_deadline": false
}
```

### Agent Task Outcome

Required fields:

- `event_type`: `task_outcome`.
- `outcome_type`: `agent_task_instance`.
- `task_instance_id`: agent DAG instance ID.
- `source`: `agent`.
- `completed_at_us`: DAG completion time.
- `total_completion_time_us`: end-to-end latency from arrival to completion.
- `completed_node_ids`: completed DAG node IDs.

Example:

```json
{
  "event_type": "task_outcome",
  "outcome_type": "agent_task_instance",
  "task_instance_id": "caption-request-00020000-001",
  "source": "agent",
  "completed_at_us": 700000,
  "total_completion_time_us": 680000,
  "completed_node_ids": ["image_captioning", "text_translation", "text_to_speech"]
}
```

## `trace_summary.json`

Records directly consumable outcome metrics. Offline scheduler evolution should use this as the primary ranking input.

Required top-level fields:

- `critical_task_metrics`
- `agent_task_metrics`

`critical_task_metrics` maps `node_id` to:

- `total_release_count`
- `met_deadline_count`
- `missed_deadline_count`
- `pending_release_count`
- `frequency_satisfaction_rate`

`agent_task_metrics.instances` contains:

- `task_instance_id`
- `completed_at_us`
- `total_completion_time_us`

`agent_task_metrics.aggregate` contains:

- `completed_instance_count`
- `avg_total_completion_time_us`
- `max_total_completion_time_us`

Example:

```json
{
  "critical_task_metrics": {
    "localization_node": {
      "total_release_count": 50,
      "met_deadline_count": 48,
      "missed_deadline_count": 2,
      "pending_release_count": 0,
      "frequency_satisfaction_rate": 0.96
    }
  },
  "agent_task_metrics": {
    "instances": [
      {
        "task_instance_id": "caption-request-00020000-001",
        "completed_at_us": 700000,
        "total_completion_time_us": 680000
      }
    ],
    "aggregate": {
      "completed_instance_count": 1,
      "avg_total_completion_time_us": 680000,
      "max_total_completion_time_us": 680000
    }
  }
}
```

## Online Writer Requirements

The online simulator must:

- Emit every required file in the trace run layout.
- Emit `task_definitions.jsonl` before or at the same tick as corresponding workload releases.
- Emit `workload_events.jsonl` when nodes become schedulable.
- Emit `scheduler_observation.jsonl` before each scheduler decision.
- Emit `scheduler_decision.jsonl` after the control plane applies accepted launches.
- Emit `runtime_execution.jsonl` once per tick.
- Emit `task_outcomes.jsonl` when critical releases finish, become incomplete at simulation end, or agent DAGs complete.
- Emit `trace_summary.json` after all outcomes have been finalized.
- Preserve `allocated_resources` explicitly in scheduler decisions and runtime events.

## Offline Reader Requirements

The offline subsystem must:

- Validate required files before analysis or replay.
- Treat `trace_summary.json` as the primary summary view.
- Use `scheduler_observation.jsonl`, `scheduler_decision.jsonl`, `runtime_execution.jsonl`, and `task_outcomes.jsonl` for attribution.
- Use `task_definitions.jsonl` and `workload_events.jsonl` for workload characterization.
- Ignore unknown additive fields.
- Reject malformed JSONL with file name and line number.
- Not infer scheduler allocation from resource demand when `allocated_resources` is present.

## Compatibility And Evolution

Trace changes must be backward-compatible unless a migration is explicitly documented.

Allowed changes:

- Add fields to existing JSON objects.
- Add optional trace files.
- Add new `definition_type` or `outcome_type` values if existing values remain unchanged.

Breaking changes:

- Rename required files.
- Rename required fields.
- Change time units away from microseconds.
- Change canonical resource field names.
- Remove `allocated_resources` from scheduler decisions or runtime events.

When a breaking change is unavoidable, update this file first and then update online writers, offline readers, and tests in the same change set.

