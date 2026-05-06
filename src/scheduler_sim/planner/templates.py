from dataclasses import dataclass, field


FIXED_AGENT_PIPELINE_QUERY = "fixed-agent-pipeline"


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
            PlannedNode(node_id="image_captioning", tool_name="image_captioning"),
            PlannedNode(node_id="text_translation", tool_name="text_translation"),
            PlannedNode(node_id="text_to_speech", tool_name="text_to_speech"),
        ],
        edges=[
            ("image_captioning", "text_translation"),
            ("text_translation", "text_to_speech"),
        ],
    )
