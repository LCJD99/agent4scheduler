# AGENTS

## Environment

- All development, test, and verification commands for this repository must use the `conda` environment named `agent`.
- Use `/Users/lcjd/miniconda3/envs/agent/bin/python` as the Python interpreter for repository commands.
- Use `/Users/lcjd/miniconda3/envs/agent/bin/python -m <module>` for Python-based tooling such as `pytest`.
- Do not rely on bare `conda run -n agent python`, because it resolves to the wrong interpreter in this environment.
- If an interactive shell is required, activate `agent` and verify that `python --version` reports the environment interpreter before running repository commands.

## Project Content Conventions

- Treat `docs/meta/need.md`, `docs/meta/workload.md`, `docs/meta/profiling.md`, and `docs/meta/trace.md` as the source-of-truth requirement documents. Code and config changes must stay aligned with them.
- Keep scenario, task, and tool configuration split under `configs/scenarios/`, `configs/tasks/`, and `configs/tools/`. Do not inline tool definitions into scenario files.
- Every critical node in task YAML must declare `node_id`, `tool_name`, `period_us`, `criticality`, and `resource_demand`.
- Every tool referenced by `tool_name` must have a matching YAML in `configs/tools/`, and `metadata.name` must match the runtime/tool reference exactly.
- Scenario YAML must carry `scene_complexity`, `tick_us`, `duration_us`, `system_capacity`, and `agent_requests`. Valid `scene_complexity` values are `small`, `medium`, and `large`.
- Profiling data lives in `data/profiling_data.csv`. Its `tool_name` column must match `configs/tools/*.yaml` `metadata.name` exactly.
- Profiling-based latency is the default runtime behavior. Runtime latency must be derived from `tool_name + allocated_resources + scene_complexity`, then combined with runtime pressure slowdown.
- Scheduler decisions must express explicit per-node `allocated_resources`; do not treat resource demand and scheduler allocation as the same concept unless the implementation is intentionally using demand as the allocation.
- Trace output must remain replay-oriented. At minimum, runs should emit `experiment_meta.json`, `workload_events.jsonl`, `task_definitions.jsonl`, `task_outcomes.jsonl`, `scheduler_observation.jsonl`, `scheduler_decision.jsonl`, `runtime_execution.jsonl`, and `trace_summary.json`.
- `trace_summary.json` is the primary summary view for outcome metrics. It must expose critical-task deadline/frequency satisfaction and agent-task total completion latency in directly consumable form.
- The default bundled scenario is expected to demonstrate resource contention: under the default config, agent arrival should be able to cause at least one critical-task deadline miss.

## Change Log

- After every code implementation, append an incremental record to `docs/changlog.md`.
- Each record should include the date, a concise summary of the implementation, key files or modules changed, and verification performed.
- Do not rewrite or reorder existing change log entries unless explicitly requested.

## Verification

- Run tests with `/Users/lcjd/miniconda3/envs/agent/bin/python -m pytest -v`.
- For end-to-end validation, run `PYTHONPATH=src /Users/lcjd/miniconda3/envs/agent/bin/python -m scheduler_sim.app --scenario configs/scenarios/home_eqa_scenario_001.yaml --trace-output <dir>`.
