# Scheduler Sim

Minimal online scheduler simulator scaffold for loading a scenario bundle and emitting a trace artifact.

## Current End-to-End Flow

The current CLI supports a small, working path:

1. Load a scenario YAML file.
2. Resolve referenced task YAML files.
3. Resolve referenced tool YAML files.
4. Write `experiment_meta.json` to the requested trace directory.

This repository does not yet implement a full fixed-tick simulator loop, runtime progression, or multi-file trace stream output.

## CLI Usage

Run with the project interpreter:

```bash
PYTHONPATH=src /Users/lcjd/miniconda3/envs/agent/bin/python -m scheduler_sim.app \
  --scenario configs/scenarios/home_eqa_scenario_001.yaml \
  --trace-output traces/home_eqa_scenario_001
```

Equivalent module-free invocation from tests:

```python
from scheduler_sim.app import main

main([
    "--scenario",
    "configs/scenarios/home_eqa_scenario_001.yaml",
    "--trace-output",
    "traces/home_eqa_scenario_001",
])
```

## Scenario Layout

The implemented config chain is:

- `configs/scenarios/*.yaml` defines scenario metadata and `tasks`.
- `configs/tasks/*.yaml` defines task metadata and `tools`.
- `configs/tools/*.yaml` defines tool metadata.

The bundled example is:

- `configs/scenarios/home_eqa_scenario_001.yaml`
- `configs/tasks/safe_navigation_task.yaml`
- `configs/tools/object_detection.yaml`

## Trace Output

The current CLI writes one file:

- `experiment_meta.json`: JSON object with the loaded scenario name, for example `{"scenario_name": "home_eqa_scenario_001"}`.

The broader trace schema described in `docs/meta/trace.md` remains a design target rather than the current implementation.
