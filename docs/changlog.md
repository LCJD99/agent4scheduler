# Changlog

## 2026-05-10

- Added filesystem case recording for offline evolution runs. `offline_case.json` is now written under the replay output directory for both completed and failed runs, including trace analyzer findings, advice branches, candidate scheduler source, replay results, selected candidate, failed stage, and error message.
- Updated the offline CLI to execute graph nodes sequentially so partial state can be captured when code generation or replay fails, making generated-code issues inspectable without relying on the memory database.
- Added `tests/offline/test_case_recording.py` to verify failed cases preserve trace findings and generated scheduler source.
- Verification: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/offline` passed with 12 tests.

## 2026-05-12

- Replaced `data/profiling_data.csv` with deterministic synthetic profiling data generated from a helper script and aligned it with more realistic latency anchors for critical nodes and agent tools.
- Added `src/scheduler_sim/profiling/synthetic_data.py` and `scripts/generate_profiling_data.py` to generate non-uniform profiling samples with controlled jitter across scene complexity and resource levels.
- Updated critical-task configuration so `safe_navigation_task` contains `localization_node` at 50 Hz, `pointcloud_to_laserscan_node` at 20 Hz, and `navigation_algo_node` at 35 Hz with the highest resource demand, while `localization_node` remains the lightest.
- Updated agent tool defaults and scenario capacity so GPU-sensitive agent tools can run in the default scenario and the agent DAG can complete within the scenario duration.
- Verification: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/profiling/test_profiling_estimator.py tests/profiling/test_synthetic_data.py tests/config/test_loader.py tests/integration/test_end_to_end.py` passed with 5 tests.

- Added OpenAI-compatible chat completions support for providers whose base URL exposes `/chat/completions` rather than `/responses`, and switched the offline OpenAI config to `provider.api: openai_chat_completions` for the configured BigModel endpoint.
- Added chat-completions JSON mode (`response_format: {"type": "json_object"}`), JSON substring extraction fallback, stricter generated-scheduler import/runtime validation, and codegen retry with validation-error feedback.
- Tightened the scheduler codegen prompt with exact `RunnableNode` fields and import rules, including `resource_demand` usage and the absence of a parameterized `Scheduler.__init__`.
- Added `socksio` to runtime dependencies so the OpenAI SDK can use SOCKS proxy configuration.
- Verification: real BigModel endpoint reached `/chat/completions`; trace analyzer and scheduler codegen calls progressed to generated-code validation/replay. Final real run was blocked by provider 429 rate limiting (`您的账户已达到速率限制，请您控制请求频率`). Local offline tests still pass.

- Ran trace-driven offline end-to-end validation through baseline trace generation, OpenAI-backed analyzer/codegen fakes, generated scheduler replay, candidate comparison, and result persistence.
- Fixed `offline/replay/runner.py` to select replay trace directories by the presence of `trace_summary.json`, avoiding `__pycache__/` directories created when generated scheduler modules are imported.
- Added profiling runtime dependencies (`numpy`, `pandas`, `scikit-learn`) to `pyproject.toml` so fresh environments can import `scheduler_sim.profiling.estimator`.
- Verification: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/offline/test_cli_evolve.py` passed with 1 trace-driven end-to-end test; `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/offline` passed with 10 tests.

- Replaced the generated scheduler template path with OpenAI-backed LLM scheduler code generation.
- Added `offline/evolution/llm_codegen.py` and `offline/evolution/schemas.py` to call the Responses API with structured output, pass scheduler interface/input/output protocol and execution constraints as context, validate returned scheduler source, and reject forbidden file/network/process/dynamic-execution patterns.
- Updated `offline/evolution/proposal.py` and `offline/graph/nodes.py` so candidate generation uses workload signatures, trace findings, similar cases, and advice branches as LLM context before replay.
- Updated offline tests to use fake OpenAI codegen clients and verify that the scheduler codegen prompt includes the scheduler protocol, output contract, and safety constraints.
- Verification: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/offline/test_llm_scheduler_codegen.py tests/offline/test_scheduler_code_evolution.py` passed with 5 tests.

- Changed offline scheduler evolution from parameter-only candidate replay to generated Python scheduler code replay.
- Updated `offline/evolution/proposal.py` to emit `generated_python_scheduler` candidates with `scheduler_source` and `create_scheduler` entrypoint metadata.
- Updated `offline/replay/runner.py` to write each candidate's `scheduler_candidate.py`, pass it to replay with `--scheduler-code`, and persist the generated code path in replay results.
- Updated `src/scheduler_sim/app.py` to load generated scheduler modules through a `create_scheduler(parameters=...)` factory while preserving the existing baseline and parameterized scheduler paths.
- Added `tests/offline/test_scheduler_code_evolution.py` and strengthened `tests/offline/test_cli_evolve.py` assertions for generated scheduler source and replay artifacts.
- Verification: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/offline/test_scheduler_code_evolution.py` passed; `py_compile` passed for changed Python files. Broader offline tests are blocked in the current `agent` environment because `scikit-learn` is missing, causing `scheduler_sim.profiling.estimator` import failure.

## 2026-05-09

- Replaced the offline trace analyzer's deterministic finding synthesizer with a real OpenAI-backed LLM agent while preserving `TraceAnalyzer.analyze(trace_run) -> list[dict]`.
- Added offline analyzer configuration loading from `configs/offline/trace_analyzer_openai.yaml`, with `base_url`, `model`, and `api_key_env` sourced from config and API key values loaded from `.env` at runtime.
- Added `offline/analysis/llm_agent.py`, `offline/analysis/schemas.py`, and `offline/config_loader.py`, and updated the offline CLI and LangGraph state to pass an analyzer config path.
- Added `.env-example`, updated `.gitignore` to ignore `.env`, and added `.env`-backed API key loading for the analyzer.
- Added tests for offline analyzer config loading, missing API key environment variables, `.env` loading, fake OpenAI-backed analyzer behavior, and CLI integration using a fake client.
- Verification: `/Users/lcjd/miniconda3/envs/agent/bin/python -m pytest -v` passed with 29 tests after the `.env` change; verified the installed OpenAI SDK exposes `client.responses` after upgrading to `openai 2.36.0`.

## 2026-05-08

- Replaced the offline rule-based trace analyzer with an agentic trace analyzer that selects missed-deadline trace windows, inspects scheduler observations, scheduler decisions, and runtime utilization inside those windows, then synthesizes findings with window-level evidence while preserving `TraceAnalyzer.analyze(trace_run) -> list[dict]`.
- Updated `tests/offline/test_analysis_memory.py` to assert `analysis_mode == "agentic_window_inspection"` and selected-window evidence such as agent-selected nodes and max CPU utilization.
- Verification: `/Users/lcjd/miniconda3/envs/agent/bin/python -m pytest -v` passed with 26 tests; manual offline CLI evolve run produced `agentic_window_inspection` findings, 2 advice branches, and 2 replay results.

- Added repository instruction that every code implementation must append an incremental record to `docs/changlog.md`.
- Updated `AGENTS.md` with required change log content: date, implementation summary, key changed files or modules, and verification performed.
- Verification: documentation-only change; inspected updated files with shell commands.

## 2026-05-12

- Fixed periodic critical release scheduling so non-tick-aligned periods such as `28571 us` release on the next scheduler tick instead of only when `timestamp_us % period_us == 0`.
- Reduced the critical navigation workload's default resource demands and profiling latencies for `localization_node`, `pointcloud_to_laserscan_node`, and `navigation_algo_node`, then regenerated `data/profiling_data.csv` so the critical workload is schedulable without agent interference under the current system-capacity scenario.
- Updated integration and workload tests to cover non-tick-aligned releases and to require `frequency_satisfaction_rate == 1.0` for a no-agent critical-only scenario.
- Key files changed: `src/scheduler_sim/workload/generator.py`, `src/scheduler_sim/profiling/synthetic_data.py`, `configs/tasks/safe_navigation_task.yaml`, `configs/tools/localization_node.yaml`, `configs/tools/pointcloud_to_laserscan_node.yaml`, `configs/tools/navigation_algo_node.yaml`, `data/profiling_data.csv`, `tests/workload/test_generator.py`, `tests/profiling/test_synthetic_data.py`, `tests/config/test_loader.py`, `tests/integration/test_end_to_end.py`.
- Verification: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/workload/test_generator.py tests/profiling/test_synthetic_data.py tests/config/test_loader.py tests/integration/test_end_to_end.py` passed with 8 tests; `PYTHONPATH=src /home/dawnat9/miniconda3/envs/agent/bin/python -m scheduler_sim.app --scenario configs/scenarios/home_eqa_scenario_001.yaml --trace-output <tmpdir>` produced `trace_summary.json` with all three critical tasks at `frequency_satisfaction_rate = 1.0`.

- Re-validated the default bundled scenario after the periodic-release fix and restored the contention regression expectation: with the default agent request present, `navigation_algo_node` must incur critical deadline misses, while a no-agent critical-only scenario must still keep all three critical tasks at `frequency_satisfaction_rate = 1.0`.
- Updated `tests/integration/test_end_to_end.py` to assert the default scenario still provides scheduler-evolution headroom and synchronized `tests/config/test_loader.py` with the actual bundled scenario capacity (`4.0 CPU / 4096 MB`).
- Verification: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/workload/test_generator.py tests/config/test_loader.py tests/integration/test_end_to_end.py` passed with 7 tests; `PYTHONPATH=src /home/dawnat9/miniconda3/envs/agent/bin/python -m scheduler_sim.app --scenario configs/scenarios/home_eqa_scenario_001.yaml --trace-output <tmpdir>` produced `trace_summary.json` with `navigation_algo_node.missed_deadline_count = 100` and `frequency_satisfaction_rate = 0.2857142857142857`.

- Tightened the offline scheduler codegen prompt so it explicitly whitelists allowed scheduler symbols, observation fields, and resource fields, and instructs the model to avoid any API or field it is not certain exists.
- Added prompt markdown emission before each scheduler codegen call and persisted the generated prompt path into candidate metadata so prompt/debug artifacts survive into offline results and `offline_case.json`.
- Key files changed: `offline/evolution/llm_codegen.py`, `offline/evolution/proposal.py`, `offline/graph/nodes.py`, `tests/offline/test_llm_scheduler_codegen.py`, `tests/offline/test_cli_evolve.py`, `tests/offline/test_case_recording.py`.
- Verification: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/offline/test_llm_scheduler_codegen.py tests/offline/test_case_recording.py tests/offline/test_cli_evolve.py` passed with 9 tests; `/home/dawnat9/miniconda3/envs/agent/bin/python -m py_compile offline/evolution/llm_codegen.py offline/evolution/proposal.py offline/graph/nodes.py tests/offline/test_llm_scheduler_codegen.py tests/offline/test_cli_evolve.py tests/offline/test_case_recording.py` passed.

- Changed offline replay artifact layout to create a timestamped evolve-run directory under the replay root so repeated heuristic/code evolution runs do not overwrite one another.
- Each evolve run now writes `offline_evolution_result.json`, `offline_case.json`, prompt markdown, candidate scheduler code, params, and replay traces under `replays/<evolution_run_id>/...`, and persists `evolution_run_id` in case/result payloads.
- Key files changed: `offline/cli.py`, `offline/graph/nodes.py`, `offline/memory/schemas.py`, `tests/offline/test_scheduler_code_evolution.py`, `tests/offline/test_case_recording.py`, `tests/offline/test_cli_evolve.py`.
- Verification: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/offline/test_llm_scheduler_codegen.py tests/offline/test_scheduler_code_evolution.py tests/offline/test_case_recording.py tests/offline/test_cli_evolve.py` passed with 11 tests; `/home/dawnat9/miniconda3/envs/agent/bin/python -m py_compile offline/cli.py offline/graph/nodes.py offline/replay/runner.py offline/evolution/proposal.py offline/evolution/llm_codegen.py tests/offline/test_llm_scheduler_codegen.py tests/offline/test_scheduler_code_evolution.py tests/offline/test_case_recording.py tests/offline/test_cli_evolve.py` passed.

- Extended the scheduler codegen prompt with the full source of the current heuristic scheduler (`src/scheduler_sim/scheduler/heuristic.py`) and the scheduler base/API definitions (`src/scheduler_sim/scheduler/base.py`) so the model sees the exact current implementation and reference interfaces before the output schema.
- Updated the prompt markdown debug artifact to render both source files as dedicated sections before `## Output Schema`, matching the actual codegen prompt context.
- Key files changed: `offline/evolution/llm_codegen.py`, `tests/offline/test_llm_scheduler_codegen.py`.
- Verification: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/offline/test_llm_scheduler_codegen.py tests/offline/test_scheduler_code_evolution.py tests/offline/test_case_recording.py tests/offline/test_cli_evolve.py` passed with 11 tests; `/home/dawnat9/miniconda3/envs/agent/bin/python -m py_compile offline/evolution/llm_codegen.py tests/offline/test_llm_scheduler_codegen.py` passed.

- Added a third offline advice branch, `branch_navigation_guardrail`, so one offline evolve run can generate three scheduler variants for comparison on the same trace.
- Ran a real offline scheduler evolution case on baseline trace `case/baseline/20260513-000345`, producing three scheduler candidates and replay traces under `case/replays/20260513-000347/`, then documented the workload, diagnosis, advice branches, current scheduler, evolved schedulers, and metric comparison in `docs/case.md`.
- Key files changed: `offline/analysis/advice.py`, `docs/case.md`.
- Verification: real run produced `3` advice branches, `3` generated candidates, and `3` replay results in `case/replays/20260513-000347/offline_evolution_result.json`; `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/dawnat9/miniconda3/envs/agent/bin/python -m pytest -v tests/offline/test_cli_evolve.py` passed.

- Added a focused navigation case study in `docs/case_1.md`, documenting a hand-crafted scheduler evolution that prioritizes `navigation_algo_node` and over-allocates CPU to it on the current workload.
- Verified the targeted scheduler on replay traces under `case/nav_focus_experiment/`, showing that `NavFocusB` improves `navigation_algo_node` completion from `28.57%` to `100.00%` and raises aggregate critical completion from `76.19%` to `100.00%`, with agent latency increasing from `2,986,000 us` to `3,059,000 us`.
- Key files changed: `docs/case_1.md`.
- Verification: inspected `case/baseline/20260513-000345/trace_summary.json` and `case/nav_focus_experiment/run_b/20260513-002020/trace_summary.json`; replay experiment produced consistent metrics across three navigation-focused scheduler variants.

- Added a Chinese version of the navigation-focused case study in `docs/case_zh.md`, covering workload, the original scheduler, the evolution rationale, the new scheduler, and the metric comparison table.
- Key files changed: `docs/case_zh.md`.
- Verification: manually checked that the Chinese document matches the baseline and replay metrics used in `docs/case_1.md`.
