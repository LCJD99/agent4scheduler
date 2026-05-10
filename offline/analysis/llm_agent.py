import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI
from dotenv import load_dotenv

from offline.analysis.schemas import (
    TRACE_FINDING_RESPONSE_SCHEMA,
    validate_trace_finding_response,
)
from offline.config_loader import OfflineAnalyzerConfig


DEFAULT_OPENAI_CLIENT_FACTORY = OpenAI


class OpenAILLMFindingAgent:
    def __init__(
        self,
        *,
        config: OfflineAnalyzerConfig,
        client_factory=None,
    ) -> None:
        self.config = config
        self.client_factory = client_factory or DEFAULT_OPENAI_CLIENT_FACTORY

    def run(
        self,
        *,
        trace_summary: dict[str, Any],
        inspections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        load_dotenv(dotenv_path=self._dotenv_path(), override=False)
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            raise ValueError(
                f"Environment variable {self.config.api_key_env} is required for the OpenAI trace analyzer"
            )

        client = self.client_factory(
            api_key=api_key,
            base_url=self.config.base_url,
        )
        payload = {
            "trace_summary": trace_summary,
            "selected_trace_windows": inspections[: self.config.max_windows],
        }
        response = client.responses.create(**self._request_kwargs(payload))
        return validate_trace_finding_response(self._parse_response_payload(response))

    def _request_kwargs(self, payload: dict[str, Any]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.config.model_name,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are an offline scheduler trace analyzer. "
                        "Return only valid JSON matching the provided schema. "
                        "Use the trace summary and selected trace windows to produce findings."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, sort_keys=True),
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "trace_findings",
                    "schema": TRACE_FINDING_RESPONSE_SCHEMA,
                    "strict": True,
                }
            },
            "timeout": self.config.timeout_s,
        }
        if self.config.reasoning_effort:
            kwargs["reasoning"] = {"effort": self.config.reasoning_effort}
        return kwargs

    def _parse_response_payload(self, response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            if "findings" in response:
                return response
            if "output_text" in response:
                return json.loads(str(response["output_text"]))
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text:
            return json.loads(output_text)
        raise ValueError("OpenAI trace analyzer response did not include output_text")

    def _dotenv_path(self) -> Path:
        configured_path = os.getenv("OFFLINE_ANALYZER_DOTENV_PATH")
        if configured_path:
            return Path(configured_path)
        return Path(__file__).resolve().parents[2] / ".env"
