from scheduler_sim.domain.tasks import TaskGraph


KNOWN_TABLE_OBJECT_QUERY = "what objects are on the table?"


def build_table_object_query_template() -> TaskGraph:
    return TaskGraph(
        nodes=["detect_table", "identify_objects"],
        edges=[("detect_table", "identify_objects")],
    )
