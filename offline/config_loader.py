from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class OfflineAnalyzerConfig:
    metadata_name: str
    provider_api: str
    base_url: str
    api_key_env: str
    model_name: str
    reasoning_effort: str | None
    timeout_s: int
    max_windows: int


def load_offline_analyzer_config(path: str | Path) -> OfflineAnalyzerConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping YAML in {config_path}")

    metadata = _require_mapping(data, "metadata")
    provider = _require_mapping(data, "provider")
    model = _require_mapping(data, "model")
    runtime = _require_mapping(data, "runtime")

    provider_api = _require_str(provider, "api")
    if provider_api != "openai":
        raise ValueError("Config field provider.api must be openai")

    return OfflineAnalyzerConfig(
        metadata_name=_require_str(metadata, "name"),
        provider_api=provider_api,
        base_url=_require_str(provider, "base_url"),
        api_key_env=_require_str(provider, "api_key_env"),
        model_name=_require_str(model, "name"),
        reasoning_effort=_optional_str(model, "reasoning_effort"),
        timeout_s=_require_int(runtime, "timeout_s"),
        max_windows=_require_int(runtime, "max_windows"),
    )


def _require_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Config field {key} must be a mapping")
    return value


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Config field {key} must be a non-empty string")
    return value


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"Config field {key} must be a non-empty string when set")
    return value


def _require_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Config field {key} must be an integer")
    return value
