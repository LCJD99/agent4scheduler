from scheduler_sim.domain.tasks import TaskGraph
from scheduler_sim.planner.templates import (
    KNOWN_TABLE_OBJECT_QUERY,
    build_table_object_query_template,
)


def _normalize_request(user_request: str) -> str:
    return " ".join(user_request.strip().lower().split())


def plan_request(user_request: str) -> TaskGraph:
    if _normalize_request(user_request) == KNOWN_TABLE_OBJECT_QUERY:
        return build_table_object_query_template()
    raise ValueError("unsupported request")
