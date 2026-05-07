# Scheduler Sim

Online scheduler simulator for fixed-tick workload release, scheduling, runtime execution, and trace emission.

## Current Scope

The repository currently supports the online path only:

1. Load a scenario YAML file.
2. Resolve referenced task YAML files and tool YAML files.
3. Build the workload described in [docs/meta/workload.md](docs/meta/workload.md).
4. Run a fixed-tick scheduler/runtime loop.
5. Emit multi-file trace output under a timestamped run directory.

## Implemented Workload

Critical workload:

- `localization_node`
- `pointcloud_to_laserscan_node`
- `navigation_algo_node`

Agent workload:

- `image_captioning -> text_translation -> text_to_speech`

The bundled example scenario is:

- `configs/scenarios/home_eqa_scenario_001.yaml`

## Run

Use the repository interpreter defined in [AGENTS.md](AGENTS.md):

```bash
PYTHONPATH=src /Users/lcjd/miniconda3/envs/agent/bin/python -m scheduler_sim.app \
  --scenario configs/scenarios/home_eqa_scenario_001.yaml \
  --trace-output traces/home_eqa_scenario_001
```

## Trace Output

Each run creates a timestamped directory under `--trace-output`:

- `YYYYMMDD-HHMMSS/experiment_meta.json`
- `YYYYMMDD-HHMMSS/workload_events.jsonl`
- `YYYYMMDD-HHMMSS/task_definitions.jsonl`
- `YYYYMMDD-HHMMSS/task_outcomes.jsonl`
- `YYYYMMDD-HHMMSS/scheduler_observation.jsonl`
- `YYYYMMDD-HHMMSS/scheduler_decision.jsonl`
- `YYYYMMDD-HHMMSS/runtime_execution.jsonl`
