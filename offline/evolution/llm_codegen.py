import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from offline.config_loader import OfflineAnalyzerConfig
from offline.evolution.schemas import (
    SCHEDULER_CODEGEN_RESPONSE_SCHEMA,
    validate_scheduler_codegen_response,
)


DEFAULT_OPENAI_CLIENT_FACTORY = OpenAI
REPO_ROOT = Path(__file__).resolve().parents[2]
HEURISTIC_SCHEDULER_PATH = REPO_ROOT / "src/scheduler_sim/scheduler/heuristic.py"
SCHEDULER_BASE_PATH = REPO_ROOT / "src/scheduler_sim/scheduler/base.py"


class OpenAISchedulerCodegenAgent:
    def __init__(
        self,
        *,
        config: OfflineAnalyzerConfig,
        client_factory=None,
    ) -> None:
        self.config = config
        self.client_factory = client_factory or DEFAULT_OPENAI_CLIENT_FACTORY

    def generate(
        self,
        *,
        candidate_id: str,
        advice_branch: dict[str, Any],
        workload_signature: dict[str, Any],
        trace_findings: list[dict[str, Any]],
        similar_cases: list[dict[str, Any]],
        prompt_output_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        load_dotenv(dotenv_path=self._dotenv_path(), override=False)
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            raise ValueError(
                f"Environment variable {self.config.api_key_env} is required for the OpenAI scheduler code generator"
            )

        client = self.client_factory(
            api_key=api_key,
            base_url=self.config.base_url,
        )
        payload = {
            "candidate_id": candidate_id,
            "advice_branch": advice_branch,
            "workload_signature": workload_signature,
            "trace_findings": trace_findings,
            "similar_cases": similar_cases,
            "output_contract": {
                "scheduler_source": "Complete Python source for a scheduler candidate.",
                "rationale": "Short explanation of the scheduling heuristic encoded in the source.",
                "constraints_satisfied": "List of constraints the source satisfies.",
            },
        }
        prompt_markdown_path = self._write_prompt_markdown(
            candidate_id=candidate_id,
            payload=payload,
            prompt_output_dir=prompt_output_dir,
        )
        last_error: Exception | None = None
        for attempt in range(3):
            if last_error is not None:
                payload["previous_validation_error"] = str(last_error)
            if self.config.provider_api == "openai_chat_completions":
                response = client.chat.completions.create(
                    **self._chat_completions_request_kwargs(payload)
                )
            else:
                response = client.responses.create(**self._request_kwargs(payload))
            try:
                result = validate_scheduler_codegen_response(
                    self._parse_response_payload(response)
                )
                result["prompt_markdown_path"] = str(prompt_markdown_path)
                return result
            except ValueError as exc:
                last_error = exc
        raise ValueError(
            "OpenAI scheduler code generator returned invalid source after 3 attempts: "
            f"{last_error}. Prompt markdown: {prompt_markdown_path}"
        )

    def _request_kwargs(self, payload: dict[str, Any]) -> dict[str, Any]:
        system_prompt = self._system_prompt()
        kwargs: dict[str, Any] = {
            "model": self.config.model_name,
            "input": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, sort_keys=True),
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "scheduler_codegen",
                    "schema": SCHEDULER_CODEGEN_RESPONSE_SCHEMA,
                    "strict": True,
                }
            },
            "timeout": self.config.timeout_s,
        }
        if self.config.reasoning_effort:
            kwargs["reasoning"] = {"effort": self.config.reasoning_effort}
        return kwargs

    def _chat_completions_request_kwargs(self, payload: dict[str, Any]) -> dict[str, Any]:
        system_prompt = self._system_prompt()
        return {
            "model": self.config.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        system_prompt
                        + "\nReturn only valid JSON with this exact top-level shape: "
                        '{"scheduler_source":"raw Python source","rationale":"string",'
                        '"constraints_satisfied":["string"]}.'
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, sort_keys=True),
                },
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "timeout": self.config.timeout_s,
        }

    def _system_prompt(self) -> str:
        return "\n".join(
            [
                "You are an offline scheduler code generation agent.",
                "Return only valid JSON matching the provided schema.",
                "Generate complete Python source for one scheduler candidate.",
                "Input protocol: use the advice branch, workload signature, trace findings, and similar cases as context.",
                "Scheduler interface protocol: Scheduler.decide(observation) -> SchedulerDecision.",
                "The generated module must define create_scheduler(parameters=None).",
                "create_scheduler(parameters=None) must return an instance of scheduler_sim.scheduler.base.Scheduler.",
                "The Scheduler base class has no parameterized constructor; do not call super().__init__.",
                "Allowed scheduler imports: scheduler_sim.scheduler.base and scheduler_sim.domain.resources.",
                "Allowed API symbols: Scheduler, SchedulerDecision, SchedulerObservation, RunnableNode, ScheduledNodeAllocation, ResourceVector.",
                "Import Scheduler, SchedulerDecision, SchedulerObservation, RunnableNode, and ScheduledNodeAllocation from scheduler_sim.scheduler.base.",
                "Import only ResourceVector from scheduler_sim.domain.resources.",
                "Never import RunnableNode from scheduler_sim.domain.resources.",
                "Allowed observation fields: observation.timestamp_us, observation.available_resources, observation.runnable_nodes, observation.running_nodes.",
                "Allowed available_resources fields: cpu_cores, memory_mb, gpu_vram_mb, network_mbps.",
                "Allowed runnable node fields: node_id, node_instance_id, task_instance_id, tool_name, source, criticality, predicted_latency_us, timestamp_us, resource_demand.",
                "Allowed running node extra fields: started_at_us, allocated_resources.",
                "Allowed resource_demand and allocated_resources fields: cpu_cores, memory_mb, gpu_vram_mb, network_mbps.",
                "Do not use gpu_units, gpu_memory_mb, memory, or network_bandwidth_mbps; those fields do not exist.",
                "Use node.resource_demand for requested resources; requested_resources does not exist.",
                "If you are not certain an API or field exists, do not use it.",
                "The scheduler must allocate only resources that fit within remaining observation.available_resources.",
                "The scheduler must express explicit allocated_resources for every selected node.",
                "Do not read or write files.",
                "Do not access network, environment variables, subprocesses, dynamic imports, eval, exec, or compile.",
                "Do not import third-party packages.",
                "Do not mutate the observation or runnable nodes.",
                "Do not include markdown fences; scheduler_source must be raw Python source.",
                "Current scheduler implementation context:",
                self._read_prompt_context(HEURISTIC_SCHEDULER_PATH),
                "Reference scheduler API context:",
                self._read_prompt_context(SCHEDULER_BASE_PATH),
            ]
        )

    def _write_prompt_markdown(
        self,
        *,
        candidate_id: str,
        payload: dict[str, Any],
        prompt_output_dir: str | Path | None,
    ) -> Path:
        output_dir = Path(prompt_output_dir or Path.cwd())
        output_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = output_dir / f"{candidate_id}_scheduler_codegen_prompt.md"
        markdown = "\n".join(
            [
                "# Scheduler Codegen Prompt",
                "",
                f"- candidate_id: `{candidate_id}`",
                f"- provider_api: `{self.config.provider_api}`",
                f"- model: `{self.config.model_name}`",
                "",
                "## System Prompt",
                "",
                "```text",
                self._system_prompt(),
                "```",
                "",
                "## User Payload",
                "",
                "```json",
                json.dumps(payload, indent=2, sort_keys=True),
                "```",
                "",
                "## Current Scheduler Source",
                "",
                "```python",
                self._read_prompt_context(HEURISTIC_SCHEDULER_PATH),
                "```",
                "",
                "## Reference Scheduler Base Source",
                "",
                "```python",
                self._read_prompt_context(SCHEDULER_BASE_PATH),
                "```",
                "",
                "## Output Schema",
                "",
                "```json",
                json.dumps(SCHEDULER_CODEGEN_RESPONSE_SCHEMA, indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
        prompt_path.write_text(markdown, encoding="utf-8")
        return prompt_path

    @staticmethod
    def _read_prompt_context(path: Path) -> str:
        return path.read_text(encoding="utf-8").strip()

    def _parse_response_payload(self, response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            if "scheduler_source" in response:
                return response
            if "output_text" in response:
                return json.loads(str(response["output_text"]))
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text:
            return json.loads(output_text)
        choices = getattr(response, "choices", None)
        if choices:
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None)
            if isinstance(content, str) and content:
                return self._loads_json_content(content)
        raise ValueError("OpenAI scheduler codegen response did not include output_text")

    @staticmethod
    def _loads_json_content(content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                return json.loads(content[start : end + 1])
            raise

    def _dotenv_path(self) -> Path:
        configured_path = os.getenv("OFFLINE_ANALYZER_DOTENV_PATH")
        if configured_path:
            return Path(configured_path)
        return Path(__file__).resolve().parents[2] / ".env"
