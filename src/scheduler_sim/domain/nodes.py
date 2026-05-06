from dataclasses import dataclass, field
from enum import Enum

from scheduler_sim.domain.resources import ResourceVector


class NodeState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class NodeSpec:
    node_id: str
    resources: ResourceVector = field(default_factory=ResourceVector)


@dataclass(slots=True)
class NodeInstance:
    spec: NodeSpec
    state: NodeState = NodeState.PENDING
