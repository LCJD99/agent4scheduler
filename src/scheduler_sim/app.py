import argparse
from datetime import datetime
from pathlib import Path

from scheduler_sim.config.loader import load_scenario_bundle
from scheduler_sim.runtime.control_plane import SchedulerControlPlane
from scheduler_sim.runtime.engine import RuntimeEngine
from scheduler_sim.scheduler.base import RunningNode, RunnableNode, SchedulerObservation
from scheduler_sim.scheduler.heuristic import HeuristicScheduler
from scheduler_sim.trace.writer import TraceWriter
from scheduler_sim.workload.generator import WorkloadGenerator
from scheduler_sim.workload.instances import (
    AgentArrivalSpec,
    CriticalTaskSpec,
    ToolExecutionSpec,
    WorkloadRelease,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scheduler-sim")
    parser.add_argument("--scenario")
    parser.add_argument("--trace-output")
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv == ["--help"]:
        return 0

    args = build_parser().parse_args(argv)
    bundle = load_scenario_bundle(args.scenario)
    trace_run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    trace_output_dir = Path(args.trace_output) / trace_run_id
    generator = _build_workload_generator(bundle)
    scheduler = HeuristicScheduler()
    runtime = RuntimeEngine(
        tick_us=bundle.scenario.tick_us,
        system_capacity=bundle.scenario.system_capacity,
    )
    control_plane = SchedulerControlPlane(runtime=runtime)

    writer = TraceWriter(output_dir=trace_output_dir)
    writer.write_experiment_meta(
        {
            "scenario_name": bundle.scenario.metadata.name,
            "scenario_path": str(Path(args.scenario).resolve()),
            "trace_run_id": trace_run_id,
            "trace_output_dir": str(trace_output_dir.resolve()),
            "task_names": sorted(bundle.tasks),
            "tool_names": sorted(bundle.tools),
            "agent_request_ids": [
                request.request_id for request in bundle.scenario.agent_requests
            ],
            "critical_task_count": sum(
                len(task.critical_nodes) for task in bundle.tasks.values()
            ),
            "agent_request_count": len(bundle.scenario.agent_requests),
            "tick_us": bundle.scenario.tick_us,
            "duration_us": bundle.scenario.duration_us,
            "system_capacity": bundle.scenario.system_capacity.to_dict(),
        }
    )
    for payload in _scenario_task_definition_payloads(bundle):
        writer.write_task_definition(payload)

    pending_releases: list[WorkloadRelease] = []
    critical_release_state: dict[str, dict[str, object]] = {}
    for timestamp_us in range(0, bundle.scenario.duration_us, bundle.scenario.tick_us):
        releases = generator.release(timestamp_us=timestamp_us)
        pending_releases.extend(releases)
        for release in releases:
            writer.write_workload_event(_workload_event_payload(release))
            _track_critical_release(critical_release_state, release)
        for payload in generator.drain_task_definitions():
            writer.write_task_definition(payload)

        observation = SchedulerObservation(
            timestamp_us=timestamp_us,
            available_resources=runtime.available_resources,
            runnable_nodes=[
                RunnableNode(
                    node_id=release.node_id,
                    node_instance_id=release.node_instance_id,
                    task_instance_id=release.task_instance_id,
                    source=release.source,
                    criticality=release.criticality,
                    predicted_latency_us=release.predicted_latency_us,
                    timestamp_us=release.timestamp_us,
                    resource_demand=release.resource_demand,
                )
                for release in pending_releases
            ],
            running_nodes=[
                RunningNode(
                    node_id=node.node_id,
                    node_instance_id=node.node_instance_id,
                    task_instance_id=node.task_instance_id,
                    source=node.source,
                    criticality=node.criticality,
                    predicted_latency_us=node.predicted_latency_us,
                    resource_demand=node.resource_demand,
                    started_at_us=node.started_at_us,
                )
                for node in runtime.running_nodes
            ],
        )
        writer.write_scheduler_observation(
            {
                "event_type": "scheduler_observation",
                "timestamp_us": timestamp_us,
                "available_resources": observation.available_resources.to_dict(),
                "runnable_nodes": [
                    {
                        "node_id": node.node_id,
                        "node_instance_id": node.node_instance_id,
                        "task_instance_id": node.task_instance_id,
                        "source": node.source,
                        "criticality": node.criticality,
                        "predicted_latency_us": node.predicted_latency_us,
                        "released_at_us": node.timestamp_us,
                        "resource_demand": node.resource_demand.to_dict(),
                    }
                    for node in observation.runnable_nodes
                ],
                "running_nodes": [
                    {
                        "node_id": node.node_id,
                        "node_instance_id": node.node_instance_id,
                        "task_instance_id": node.task_instance_id,
                        "source": node.source,
                        "criticality": node.criticality,
                        "predicted_latency_us": node.predicted_latency_us,
                        "started_at_us": node.started_at_us,
                        "resource_demand": node.resource_demand.to_dict(),
                    }
                    for node in observation.running_nodes
                ],
            }
        )

        decision = scheduler.decide(observation=observation)
        started_nodes = control_plane.apply(decision=decision)
        writer.write_scheduler_decision(
            {
                "event_type": "scheduler_decision",
                "timestamp_us": timestamp_us,
                "selected_nodes": [
                    {
                        "node_id": node.node_id,
                        "node_instance_id": node.node_instance_id,
                        "task_instance_id": node.task_instance_id,
                        "source": node.source,
                        "criticality": node.criticality,
                        "predicted_latency_us": node.predicted_latency_us,
                        "resource_demand": node.resource_demand.to_dict(),
                    }
                    for node in started_nodes
                ],
            }
        )
        pending_releases = _remove_started_releases(
            pending_releases=pending_releases,
            started_nodes=started_nodes,
        )

        runtime_payload = runtime.advance_tick(timestamp_us=timestamp_us)
        writer.write_runtime_execution(runtime_payload)
        for completed_node in runtime_payload["completed_nodes"]:
            outcome_payload = _critical_outcome_payload(
                critical_release_state=critical_release_state,
                completed_node=completed_node,
            )
            if outcome_payload is not None:
                writer.write_task_outcome(outcome_payload)
        completed_at_us = timestamp_us + bundle.scenario.tick_us
        completion_releases = generator.release_on_completions(
            timestamp_us=completed_at_us,
            completed_node_instance_ids=runtime_payload["completed_node_instance_ids"],
        )
        pending_releases.extend(completion_releases)
        for release in completion_releases:
            writer.write_workload_event(_workload_event_payload(release))
            _track_critical_release(critical_release_state, release)
        for payload in generator.drain_task_outcomes():
            writer.write_task_outcome(payload)
    for payload in _incomplete_critical_outcome_payloads(
        critical_release_state=critical_release_state,
        simulation_end_us=bundle.scenario.duration_us,
    ):
        writer.write_task_outcome(payload)
    return 0


def _build_workload_generator(bundle) -> WorkloadGenerator:
    critical_tasks = [
        CriticalTaskSpec(
            node_id=node.node_id,
            period_us=node.period_us,
            criticality=node.criticality,
            predicted_latency_us=node.predicted_latency_us,
            resource_demand=node.resource_demand,
            task_instance_id=task.metadata.name,
        )
        for task in bundle.tasks.values()
        for node in task.critical_nodes
    ]
    agent_arrivals = [
        AgentArrivalSpec(
            request_id=request.request_id,
            user_request=request.user_request,
            arrival_time_us=request.arrival_time_us,
            criticality=request.criticality,
        )
        for request in bundle.scenario.agent_requests
    ]
    tool_execution_specs = {
        tool_name: ToolExecutionSpec(
            predicted_latency_us=tool.default_predicted_latency_us,
            resource_demand=tool.default_resource_demand,
        )
        for tool_name, tool in bundle.tools.items()
    }
    return WorkloadGenerator(
        critical_tasks=critical_tasks,
        agent_arrivals=agent_arrivals,
        tool_execution_specs=tool_execution_specs,
    )


def _remove_started_releases(
    *,
    pending_releases: list[WorkloadRelease],
    started_nodes: list[RunnableNode],
) -> list[WorkloadRelease]:
    remaining = list(pending_releases)
    for node in started_nodes:
        for index, release in enumerate(remaining):
            if release.node_instance_id == node.node_instance_id:
                remaining.pop(index)
                break
    return remaining


def _workload_event_payload(release: WorkloadRelease) -> dict[str, object]:
    return {
        "event_type": "workload_release",
        "timestamp_us": release.timestamp_us,
        "node_id": release.node_id,
        "node_instance_id": release.node_instance_id,
        "task_instance_id": release.task_instance_id,
        "source": release.source,
        "criticality": release.criticality,
        "predicted_latency_us": release.predicted_latency_us,
        "period_us": release.period_us,
        "resource_demand": release.resource_demand.to_dict(),
        "predecessor_instance_ids": release.predecessor_instance_ids,
    }


def _scenario_task_definition_payloads(bundle) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for task in bundle.tasks.values():
        for critical_node in task.critical_nodes:
            payloads.append(
                {
                    "event_type": "task_definition",
                    "definition_type": "scenario_critical_task",
                    "task_instance_id": task.metadata.name,
                    "task_name": task.metadata.name,
                    "node_id": critical_node.node_id,
                    "criticality": critical_node.criticality,
                    "period_us": critical_node.period_us,
                    "predicted_latency_us": critical_node.predicted_latency_us,
                    "resource_demand": critical_node.resource_demand.to_dict(),
                }
            )
    return payloads


def _track_critical_release(
    critical_release_state: dict[str, dict[str, object]],
    release: WorkloadRelease,
) -> None:
    if release.source != "critical" or release.period_us is None:
        return
    critical_release_state[release.node_instance_id] = {
        "task_instance_id": release.task_instance_id,
        "node_id": release.node_id,
        "node_instance_id": release.node_instance_id,
        "criticality": release.criticality,
        "released_at_us": release.timestamp_us,
        "deadline_us": release.timestamp_us + release.period_us,
        "period_us": release.period_us,
    }


def _critical_outcome_payload(
    *,
    critical_release_state: dict[str, dict[str, object]],
    completed_node: dict[str, object],
) -> dict[str, object] | None:
    state = critical_release_state.pop(str(completed_node["node_instance_id"]), None)
    if state is None:
        return None

    completed_at_us = int(completed_node["completed_at_us"])
    deadline_us = int(state["deadline_us"])
    return {
        "event_type": "task_outcome",
        "outcome_type": "critical_release",
        "task_instance_id": state["task_instance_id"],
        "node_id": state["node_id"],
        "node_instance_id": state["node_instance_id"],
        "criticality": state["criticality"],
        "released_at_us": state["released_at_us"],
        "completed_at_us": completed_at_us,
        "deadline_us": deadline_us,
        "period_us": state["period_us"],
        "completed": True,
        "missed_deadline": completed_at_us > deadline_us,
    }


def _incomplete_critical_outcome_payloads(
    *,
    critical_release_state: dict[str, dict[str, object]],
    simulation_end_us: int,
) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for state in critical_release_state.values():
        deadline_us = int(state["deadline_us"])
        payloads.append(
            {
                "event_type": "task_outcome",
                "outcome_type": "critical_release",
                "task_instance_id": state["task_instance_id"],
                "node_id": state["node_id"],
                "node_instance_id": state["node_instance_id"],
                "criticality": state["criticality"],
                "released_at_us": state["released_at_us"],
                "completed_at_us": None,
                "deadline_us": deadline_us,
                "period_us": state["period_us"],
                "completed": False,
                "missed_deadline": simulation_end_us > deadline_us,
            }
        )
    return payloads
