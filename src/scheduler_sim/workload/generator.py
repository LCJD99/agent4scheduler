from dataclasses import dataclass, field

from scheduler_sim.workload.instances import (
    AgentArrivalSpec,
    CriticalTaskSpec,
    WorkloadRelease,
)


@dataclass(slots=True)
class WorkloadGenerator:
    critical_tasks: list[CriticalTaskSpec] = field(default_factory=list)
    agent_arrivals: list[AgentArrivalSpec] = field(default_factory=list)

    @classmethod
    def critical_only(cls, node_id: str, period_us: int) -> "WorkloadGenerator":
        return cls(
            critical_tasks=[CriticalTaskSpec(node_id=node_id, period_us=period_us)],
        )

    def release(self, timestamp_us: int) -> list[WorkloadRelease]:
        releases: list[WorkloadRelease] = []

        for task in self.critical_tasks:
            if timestamp_us > 0 and timestamp_us % task.period_us == 0:
                releases.append(
                    WorkloadRelease(
                        node_id=task.node_id,
                        source="critical",
                        timestamp_us=timestamp_us,
                    )
                )

        for arrival in self.agent_arrivals:
            if arrival.arrival_time_us == timestamp_us:
                releases.append(
                    WorkloadRelease(
                        node_id=arrival.node_id,
                        source="agent",
                        timestamp_us=timestamp_us,
                    )
                )

        return releases
