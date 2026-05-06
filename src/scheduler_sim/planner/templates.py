from dataclasses import dataclass, field


KNOWN_TABLE_OBJECT_QUERY = "what objects are on the table?"


@dataclass(slots=True)
class PlannedNode:
    node_id: str
    tool_name: str


@dataclass(slots=True)
class PlannedDag:
    nodes: list[PlannedNode]
    edges: list[tuple[str, str]] = field(default_factory=list)


def build_table_object_query_template() -> PlannedDag:
    return PlannedDag(
        nodes=[
            PlannedNode(node_id="detect_table", tool_name="object_detection"),
            PlannedNode(node_id="identify_objects", tool_name="object_detection"),
        ],
        edges=[("detect_table", "identify_objects")],
    )
