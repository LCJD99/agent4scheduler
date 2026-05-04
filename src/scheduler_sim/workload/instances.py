from dataclasses import dataclass


@dataclass(slots=True)
class WorkloadRelease:
    node_id: str
    source: str
    timestamp_us: int


@dataclass(slots=True)
class CriticalTaskSpec:
    node_id: str
    period_us: int


@dataclass(slots=True)
class AgentArrivalSpec:
    node_id: str
    arrival_time_us: int
