from scheduler_sim.planner.templates import (
    PlannedDag,
    build_table_object_query_template,
)


def _normalize_request(user_request: str) -> str:
    return " ".join(user_request.strip().lower().split())


def plan_request(user_request: str) -> PlannedDag:
    if _normalize_request(user_request):
        return build_table_object_query_template()
    raise ValueError("unsupported request")
