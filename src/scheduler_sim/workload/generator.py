from collections.abc import Callable
from dataclasses import dataclass, field
import re

from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.planner.agent import plan_request
from scheduler_sim.planner.templates import PlannedDag
from scheduler_sim.workload.instances import (
    AgentArrivalSpec,
    CriticalTaskSpec,
    ToolExecutionSpec,
    WorkloadRelease,
)


@dataclass(slots=True)
class AgentInstanceState:
    task_instance_id: str
    criticality: str
    arrival_time_us: int
    dag: PlannedDag
    completed_node_ids: set[str] = field(default_factory=set)
    released_node_ids: set[str] = field(default_factory=set)
    outcome_emitted: bool = False


@dataclass(slots=True)
class WorkloadGenerator:
    critical_tasks: list[CriticalTaskSpec] = field(default_factory=list)
    agent_arrivals: list[AgentArrivalSpec] = field(default_factory=list)
    tool_execution_specs: dict[str, ToolExecutionSpec] = field(default_factory=dict)
    planner: Callable[[str], PlannedDag] = plan_request
    _agent_instances: dict[str, AgentInstanceState] = field(default_factory=dict)
    _pending_task_definitions: list[dict[str, object]] = field(default_factory=list)
    _pending_task_outcomes: list[dict[str, object]] = field(default_factory=list)
    _critical_release_counts: dict[str, int] = field(default_factory=dict)
    _agent_arrival_counts: dict[str, int] = field(default_factory=dict)

    @classmethod
    def critical_only(cls, node_id: str, period_us: int) -> "WorkloadGenerator":
        return cls(
            critical_tasks=[
                CriticalTaskSpec(
                    node_id=node_id,
                    tool_name=node_id,
                    period_us=period_us,
                    criticality="high",
                    predicted_latency_us=period_us,
                    resource_demand=ResourceVector(cpu_cores=1.0),
                )
            ],
        )

    def release(self, timestamp_us: int) -> list[WorkloadRelease]:
        releases: list[WorkloadRelease] = []

        for task in self.critical_tasks:
            if timestamp_us % task.period_us == 0:
                task_key = task.task_instance_id or task.node_id
                release_count = self._critical_release_counts.get(task_key, 0) + 1
                self._critical_release_counts[task_key] = release_count
                task_instance_id = (
                    f"critical-{self._slug(task.node_id)}-{release_count:05d}"
                )
                releases.append(
                    WorkloadRelease(
                        node_id=task.node_id,
                        tool_name=task.tool_name,
                        node_instance_id=self._format_node_instance_id(
                            task_instance_id,
                            task.node_id,
                            0,
                        ),
                        task_instance_id=task_instance_id,
                        source="critical",
                        criticality=task.criticality,
                        predicted_latency_us=task.predicted_latency_us,
                        timestamp_us=timestamp_us,
                        resource_demand=task.resource_demand,
                        period_us=task.period_us,
                    )
                )

        for arrival in self.agent_arrivals:
            if arrival.arrival_time_us == timestamp_us:
                releases.extend(
                    self._release_agent_roots(
                        arrival=arrival,
                        timestamp_us=timestamp_us,
                    )
                )

        return releases

    def drain_task_definitions(self) -> list[dict[str, object]]:
        definitions = list(self._pending_task_definitions)
        self._pending_task_definitions.clear()
        return definitions

    def drain_task_outcomes(self) -> list[dict[str, object]]:
        outcomes = list(self._pending_task_outcomes)
        self._pending_task_outcomes.clear()
        return outcomes

    def release_on_completions(
        self,
        *,
        timestamp_us: int,
        completed_node_instance_ids: list[str],
    ) -> list[WorkloadRelease]:
        releases: list[WorkloadRelease] = []
        for node_instance_id in completed_node_instance_ids:
            task_instance_id, node_id = self._parse_node_instance_id(node_instance_id)
            agent_state = self._agent_instances.get(task_instance_id)
            if agent_state is None:
                continue

            agent_state.completed_node_ids.add(node_id)
            if (
                not agent_state.outcome_emitted
                and len(agent_state.completed_node_ids) == len(agent_state.dag.nodes)
            ):
                agent_state.outcome_emitted = True
                self._pending_task_outcomes.append(
                    {
                        "event_type": "task_outcome",
                        "outcome_type": "agent_task_instance",
                        "task_instance_id": agent_state.task_instance_id,
                        "source": "agent",
                        "completed_at_us": timestamp_us,
                        "total_completion_time_us": (
                            timestamp_us - agent_state.arrival_time_us
                        ),
                        "completed_node_ids": [
                            node.node_id
                            for node in agent_state.dag.nodes
                            if node.node_id in agent_state.completed_node_ids
                        ],
                    }
                )
            for successor in self._successors(agent_state.dag, node_id):
                if successor in agent_state.released_node_ids:
                    continue
                predecessors = self._predecessors(agent_state.dag, successor)
                if all(
                    predecessor in agent_state.completed_node_ids
                    for predecessor in predecessors
                ):
                    releases.append(
                        self._make_agent_release(
                            agent_state=agent_state,
                            node_id=successor,
                            timestamp_us=timestamp_us,
                            predecessor_node_ids=predecessors,
                        )
                    )
        return releases

    def _release_agent_roots(
        self,
        *,
        arrival: AgentArrivalSpec,
        timestamp_us: int,
    ) -> list[WorkloadRelease]:
        dag = self.planner(arrival.user_request)
        arrival_count = self._agent_arrival_counts.get(arrival.request_id, 0) + 1
        self._agent_arrival_counts[arrival.request_id] = arrival_count
        task_instance_id = (
            f"{self._slug(arrival.request_id)}-{timestamp_us:08d}-{arrival_count:03d}"
        )
        agent_state = AgentInstanceState(
            task_instance_id=task_instance_id,
            criticality=arrival.criticality,
            arrival_time_us=timestamp_us,
            dag=dag,
        )
        self._agent_instances[task_instance_id] = agent_state
        self._pending_task_definitions.append(
            {
                "event_type": "task_definition",
                "definition_type": "agent_task_instance",
                "task_instance_id": task_instance_id,
                "request_id": arrival.request_id,
                "arrival_time_us": timestamp_us,
                "criticality": arrival.criticality,
                "user_request": arrival.user_request,
                "node_ids": [node.node_id for node in dag.nodes],
                "edges": [list(edge) for edge in dag.edges],
                "tool_map": {node.node_id: node.tool_name for node in dag.nodes},
            }
        )
        root_nodes = [
            node.node_id
            for node in dag.nodes
            if not self._predecessors(dag, node.node_id)
        ]
        return [
            self._make_agent_release(
                agent_state=agent_state,
                node_id=node_id,
                timestamp_us=timestamp_us,
                predecessor_node_ids=[],
            )
            for node_id in root_nodes
        ]

    def _make_agent_release(
        self,
        *,
        agent_state: AgentInstanceState,
        node_id: str,
        timestamp_us: int,
        predecessor_node_ids: list[str],
    ) -> WorkloadRelease:
        execution_spec = self.tool_execution_specs[self._tool_name_for(agent_state.dag, node_id)]
        agent_state.released_node_ids.add(node_id)
        predecessor_instance_ids = [
            self._format_node_instance_id(
                agent_state.task_instance_id,
                predecessor_node_id,
                0,
            )
            for predecessor_node_id in predecessor_node_ids
        ]
        return WorkloadRelease(
            node_id=node_id,
            tool_name=self._tool_name_for(agent_state.dag, node_id),
            node_instance_id=self._format_node_instance_id(
                agent_state.task_instance_id,
                node_id,
                0,
            ),
            task_instance_id=agent_state.task_instance_id,
            source="agent",
            criticality=agent_state.criticality,
            predicted_latency_us=execution_spec.predicted_latency_us,
            timestamp_us=timestamp_us,
            resource_demand=execution_spec.resource_demand,
            period_us=None,
            predecessor_instance_ids=predecessor_instance_ids,
        )

    def _tool_name_for(self, dag: PlannedDag, node_id: str) -> str:
        for node in dag.nodes:
            if node.node_id == node_id:
                return node.tool_name
        raise KeyError(f"Unknown planner node {node_id}")

    def _predecessors(self, dag: PlannedDag, node_id: str) -> list[str]:
        return [source for source, target in dag.edges if target == node_id]

    def _successors(self, dag: PlannedDag, node_id: str) -> list[str]:
        return [target for source, target in dag.edges if source == node_id]

    def _format_node_instance_id(
        self,
        task_instance_id: str,
        node_id: str,
        release_index: int,
    ) -> str:
        return f"{task_instance_id}--{self._slug(node_id)}"

    def _parse_node_instance_id(self, node_instance_id: str) -> tuple[str, str]:
        task_instance_id, node_id = node_instance_id.rsplit("--", 1)
        return task_instance_id, node_id

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9_]+", "-", value.strip().lower()).strip("-")
