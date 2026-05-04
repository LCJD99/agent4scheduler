from scheduler_sim.planner.templates import (
    KNOWN_TABLE_OBJECT_QUERY,
    PlannedDag,
    build_table_object_query_template,
)


def _normalize_request(user_request: str) -> str:
    return " ".join(user_request.strip().lower().split())


def plan_request(user_request: str) -> PlannedDag:
    if _normalize_request(user_request) == KNOWN_TABLE_OBJECT_QUERY:
        return build_table_object_query_template()
    raise ValueError("unsupported request")
