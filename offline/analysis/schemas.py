from typing import Any


TRACE_FINDING_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "defect_type": {"type": "string"},
                    "severity": {"type": "string"},
                    "affected_nodes": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "root_cause_hypothesis": {"type": "string"},
                    "natural_language_advice": {"type": "string"},
                    "window_refs": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                },
                "required": [
                    "defect_type",
                    "severity",
                    "affected_nodes",
                    "root_cause_hypothesis",
                    "natural_language_advice",
                    "window_refs",
                ],
            },
        }
    },
    "required": ["findings"],
}


def validate_trace_finding_response(payload: dict[str, Any]) -> dict[str, Any]:
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise ValueError("LLM response must contain a findings list")
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("Each finding must be a mapping")
        _require_str(finding, "defect_type")
        _require_str(finding, "severity")
        _require_str(finding, "root_cause_hypothesis")
        _require_str(finding, "natural_language_advice")
        affected_nodes = finding.get("affected_nodes")
        if not isinstance(affected_nodes, list) or not all(
            isinstance(node, str) for node in affected_nodes
        ):
            raise ValueError("Finding affected_nodes must be a list of strings")
        window_refs = finding.get("window_refs")
        if not isinstance(window_refs, list) or not all(
            isinstance(index, int) for index in window_refs
        ):
            raise ValueError("Finding window_refs must be a list of integers")
    return payload


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Finding field {key} must be a non-empty string")
    return value
