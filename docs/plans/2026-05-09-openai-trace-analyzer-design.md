# OpenAI Trace Analyzer Design

## Goal

Replace the current rule-based / deterministic finding synthesis in the offline trace analyzer with a real OpenAI-backed LLM agent while preserving the existing external interface:

```python
TraceAnalyzer.analyze(trace_run) -> list[dict[str, Any]]
```

The analyzer remains a LangGraph-driven, self-authored agent workflow. The LLM is used for trace finding synthesis, not for replacing the entire offline analysis pipeline.

## Scope

- Keep the current `TraceAnalyzer` entrypoint and return shape.
- Keep deterministic trace loading, trace window selection, and trace window inspection.
- Replace finding synthesis with a real OpenAI Responses API call.
- Configure `base_url`, `model`, and `api_key` indirection through a standalone YAML file under `configs/offline/`.
- Read the API key from an environment variable named in the YAML config.
- Fail fast when config or credentials are missing, or when the model response does not match the expected schema.

Out of scope for this change:

- Replacing LangGraph with another agent runtime.
- Moving online scheduling or replay logic to OpenAI calls.
- Silent fallback to the old rule-based finding synthesizer.
- Embeddings, vector search, or tool-calling beyond the current analyzer workflow.

## Current State

The current analyzer already has a useful agent-like decomposition:

```text
TraceBundle.load
-> TraceWindowSelector.select
-> TraceWindowInspector.inspect
-> TraceFindingSynthesizer.synthesize
```

The current weakness is the last step. It is deterministic and hand-authored, so it cannot generalize its causal analysis or advice quality beyond the encoded heuristics.

This design keeps the first three stages and replaces only the synthesis stage with a real LLM-backed component.

## Recommended Architecture

Use the current LangGraph-compatible analyzer structure and insert an OpenAI-backed agent stage:

```text
TraceBundle.load
-> TraceWindowSelector.select
-> TraceWindowInspector.inspect
-> OpenAILLMFindingAgent.run
-> TraceFindingAdapter.to_findings
```

This is the narrowest change that still satisfies the goal of using a real LLM agent.

## Why This Design

This design is preferred over a full LLM replacement because:

- Trace window selection is deterministic and should stay deterministic.
- Trace window inspection is structured extraction from trace files and should stay testable.
- Only the causal synthesis and advice generation benefit materially from an LLM.
- The external interface stays stable, so the rest of offline evolution does not need to change.
- Cost, latency, and regression surface remain contained.

## Config Layout

Add a new offline config namespace:

```text
configs/
`-- offline/
    `-- trace_analyzer_openai.yaml
```

Recommended config shape:

```yaml
metadata:
  name: trace_analyzer_openai

provider:
  api: openai
  base_url: https://api.openai.com/v1
  api_key_env: OPENAI_API_KEY

model:
  name: gpt-5.4
  reasoning_effort: medium

runtime:
  timeout_s: 60
  max_windows: 5
```

## Config Rules

- `base_url` is explicit and always comes from config.
- `model.name` is explicit and always comes from config.
- `api_key_env` is the environment variable name to read at runtime.
- The YAML file must not contain the raw API key.
- Missing config file is an error.
- Missing `api_key_env` is an error.
- Missing environment variable value is an error.
- Unsupported `provider.api` value is an error.

## Module Changes

Recommended module layout:

```text
offline/
|-- analysis/
|   |-- trace_analyzer.py
|   |-- llm_agent.py
|   `-- schemas.py
`-- config_loader.py
```

### `offline/analysis/trace_analyzer.py`

Keep:

- `TraceAnalyzer`
- `AgenticTraceAnalyzer`
- `TraceBundle`
- `TraceWindowSelector`
- `TraceWindowInspector`

Change:

- Remove direct finding synthesis responsibility from the current deterministic synthesizer.
- Replace it with a call into `OpenAILLMFindingAgent`.

### `offline/analysis/llm_agent.py`

New responsibilities:

- Build OpenAI client from loaded config.
- Read API key from the configured environment variable.
- Build system and user messages from trace summary and selected windows.
- Call the Responses API.
- Parse structured output.
- Return a strongly shaped intermediate result to the adapter.

### `offline/analysis/schemas.py`

New responsibilities:

- Define the expected LLM structured output shape.
- Validate required fields before adaptation to the legacy `list[dict]` result.

### `offline/config_loader.py`

New responsibilities:

- Load and validate offline config YAMLs.
- Provide a typed config object or validated dict to the analyzer.

## LLM Input Design

Do not send raw full trace files to the model.

Send only compressed structured context:

- `trace_summary.json` key metrics
- up to `runtime.max_windows` selected trace windows
- for each window:
  - `reason`
  - `center_timestamp_us`
  - `target_node_id`
  - `target_node_instance_id`
  - `critical_runnable_nodes`
  - `agent_runnable_nodes`
  - `critical_selected_nodes`
  - `agent_selected_nodes`
  - `running_agent_nodes`
  - `max_cpu_utilization`
  - `max_gpu_utilization`

This keeps the prompt bounded, reproducible, and directly tied to the inspected trace slices.

## LLM Output Contract

The model must return structured JSON compatible with the existing analyzer interface after adaptation.

Suggested LLM-native schema:

```json
{
  "findings": [
    {
      "defect_type": "critical_deadline_miss",
      "severity": "high",
      "affected_nodes": ["localization_node"],
      "root_cause_hypothesis": "Agent launches were admitted near missed critical deadlines under high CPU utilization.",
      "natural_language_advice": "Add a critical guard window and CPU headroom before admitting low-criticality agent nodes.",
      "window_refs": [0, 1]
    }
  ]
}
```

Then adapt into the current public result format:

```json
{
  "defect_type": "critical_deadline_miss",
  "severity": "high",
  "analysis_mode": "openai_llm_agent",
  "affected_nodes": ["localization_node"],
  "root_cause_hypothesis": "...",
  "evidence": [
    {
      "file": "trace_summary.json",
      "metric": "critical_task_metrics.*.missed_deadline_count",
      "value": 3
    },
    {
      "file": "selected_trace_windows",
      "windows": [...]
    }
  ],
  "natural_language_advice": "..."
}
```

## OpenAI API Choice

Use the OpenAI Responses API with structured outputs.

Reasons:

- It is the current API direction for advanced agentic workflows.
- Current GPT-5.4 and GPT-5.5 models support `v1/responses` and structured outputs.
- It keeps the implementation simple and avoids unnecessary framework coupling.

The analyzer should not depend on LangChain or another model wrapper. Use the official `openai` SDK directly.

## Failure Policy

This analyzer replacement should fail loudly rather than silently degrade.

Error cases that must fail fast:

- Missing offline config file.
- Invalid YAML shape.
- Missing `provider.base_url`.
- Missing `provider.api_key_env`.
- Environment variable not set.
- OpenAI API request failure.
- Timeout.
- Invalid JSON response.
- Structured output that does not satisfy the expected schema.

Rationale:

- Silent fallback would hide misconfiguration and make offline evolution runs non-reproducible.
- The user explicitly asked to replace the current analyzer with a real LLM-backed implementation.

## Testing Strategy

Do not use the real OpenAI API in tests.

### Unit Tests

- Config loader accepts valid offline config YAML.
- Config loader rejects missing `base_url`, missing `model.name`, or missing `api_key_env`.
- LLM agent raises when the configured environment variable is missing.
- LLM agent builds the expected prompt payload from summary and inspected windows.
- Adapter converts valid structured output into the legacy analyzer result shape.
- Analyzer raises on malformed model output.

### Integration Tests

- Inject a fake OpenAI client into `OpenAILLMFindingAgent`.
- Run `TraceAnalyzer.analyze(trace_run)` over a fixture trace.
- Assert:
  - interface remains `list[dict]`
  - `analysis_mode == "openai_llm_agent"`
  - evidence still includes `selected_trace_windows`
  - findings remain consumable by downstream offline stages

### Non-Tested In CI

- Real OpenAI network calls.
- Real credentialed execution.

Those should be covered by a manual smoke workflow.

## Manual Verification

With a valid config file and environment variable:

```text
OPENAI_API_KEY=... PYTHONPATH=src:. /Users/lcjd/miniconda3/envs/agent/bin/python -m offline.cli evolve --trace-run <trace-dir> --memory <db> --replay-output <dir> --max-candidates 2
```

Expected behavior:

- Offline evolution completes.
- `offline_evolution_result.json` contains findings with `analysis_mode: openai_llm_agent`.
- Advice branches and candidate generation continue to work with no interface changes.

## Backward Compatibility

The following must remain unchanged:

- `TraceAnalyzer.analyze(trace_run)` signature
- analyzer return type
- downstream offline graph state keys
- `offline.cli evolve` behavior from the caller perspective

Only the analyzer internals and new offline config loading are allowed to change.

## Risks

- Prompt drift can cause unstable finding phrasing.
- Structured output must be tightly validated or downstream logic will become fragile.
- Token costs can rise if too many windows are included.
- Non-default `base_url` endpoints may have partial compatibility with OpenAI structured outputs.

## Mitigations

- Cap prompt size with `max_windows`.
- Keep deterministic preprocessing.
- Validate model output strictly.
- Keep the adapter layer narrow and explicit.
- Require explicit config instead of implicit environment defaults.

## Acceptance Criteria

- Analyzer uses a real OpenAI model call for finding synthesis.
- `base_url`, `model`, and `api_key_env` come from `configs/offline/*.yaml`.
- Runtime reads the API key from the configured environment variable.
- Missing config or credentials fail fast.
- Public analyzer interface remains unchanged.
- Offline evolution pipeline continues to consume analyzer output without modification.
- Tests use a fake client rather than live API calls.

