import re
from typing import Any

from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import RunnableNode, Scheduler, SchedulerObservation


SCHEDULER_CODEGEN_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "scheduler_source": {"type": "string"},
        "rationale": {"type": "string"},
        "constraints_satisfied": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["scheduler_source", "rationale", "constraints_satisfied"],
}


FORBIDDEN_SOURCE_PATTERNS = [
    "open(",
    "exec(",
    "eval(",
    "compile(",
    "__import__",
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "http.client",
    "os.environ",
    "pathlib",
    "shutil",
    "super().__init__(",
    "requested_resources",
    "gpu_units",
]

FORBIDDEN_SOURCE_REGEX_PATTERNS = [
    r"\.gpu_memory_mb\b",
    r"\.network_bandwidth_mbps\b",
]


def validate_scheduler_codegen_response(payload: dict[str, Any]) -> dict[str, Any]:
    scheduler_source = payload.get("scheduler_source")
    rationale = payload.get("rationale")
    constraints_satisfied = payload.get("constraints_satisfied")
    if not isinstance(scheduler_source, str) or not scheduler_source.strip():
        raise ValueError("LLM scheduler codegen response must contain scheduler_source")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("LLM scheduler codegen response must contain rationale")
    if not isinstance(constraints_satisfied, list) or not all(
        isinstance(item, str) for item in constraints_satisfied
    ):
        raise ValueError("LLM scheduler codegen response constraints_satisfied must be a list of strings")
    validate_scheduler_source(scheduler_source)
    return payload


def validate_scheduler_source(source: str) -> None:
    for pattern in FORBIDDEN_SOURCE_PATTERNS:
        if pattern in source:
            raise ValueError(f"Generated scheduler source contains forbidden pattern: {pattern}")
    for pattern in FORBIDDEN_SOURCE_REGEX_PATTERNS:
        if re.search(pattern, source):
            raise ValueError(
                f"Generated scheduler source contains forbidden pattern: {pattern}"
            )
    if "def create_scheduler" not in source:
        raise ValueError("Generated scheduler source must define create_scheduler")
    if "SchedulerDecision" not in source:
        raise ValueError("Generated scheduler source must construct SchedulerDecision")
    if "def decide" not in source or "observation" not in source:
        raise ValueError("Generated scheduler source must define decide with observation")
    code = compile(source, "<generated_scheduler>", "exec")
    namespace: dict[str, Any] = {}
    exec(code, namespace)
    factory = namespace.get("create_scheduler")
    if not callable(factory):
        raise ValueError("Generated scheduler source create_scheduler must be callable")
    scheduler = factory(parameters={})
    if not isinstance(scheduler, Scheduler):
        raise ValueError("Generated scheduler source must create a Scheduler instance")
    observation = SchedulerObservation(
        timestamp_us=1_000,
        available_resources=ResourceVector(cpu_cores=2.0, memory_mb=1024),
        runnable_nodes=[
            RunnableNode(
                node_id="critical-node",
                node_instance_id="critical-node:0",
                task_instance_id="critical-task",
                tool_name="localization_node",
                source="critical",
                criticality="high",
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
            )
        ],
    )
    try:
        decision = scheduler.decide(observation=observation)
    except Exception as exc:
        raise ValueError(
            f"Generated scheduler decide failed on validation observation: {exc}"
        ) from exc
    if not hasattr(decision, "allocations"):
        raise ValueError("Generated scheduler decide must return SchedulerDecision")
