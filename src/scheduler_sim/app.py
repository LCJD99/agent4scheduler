import argparse
from pathlib import Path

from scheduler_sim.config.loader import load_scenario_bundle
from scheduler_sim.runtime.control_plane import SchedulerControlPlane
from scheduler_sim.runtime.engine import RuntimeEngine
from scheduler_sim.scheduler.base import RunnableNode, SchedulerObservation
from scheduler_sim.scheduler.heuristic import HeuristicScheduler
from scheduler_sim.trace.writer import TraceWriter
from scheduler_sim.workload.generator import WorkloadGenerator
from scheduler_sim.workload.instances import AgentArrivalSpec, CriticalTaskSpec, WorkloadRelease


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
    generator = _build_workload_generator(bundle)
    scheduler = HeuristicScheduler()
    runtime = RuntimeEngine(tick_us=bundle.scenario.tick_us)
    control_plane = SchedulerControlPlane(runtime=runtime)

    writer = TraceWriter(output_dir=Path(args.trace_output))
    writer.write_experiment_meta(
        {
            "scenario_name": bundle.scenario.metadata.name,
            "tick_us": bundle.scenario.tick_us,
            "duration_us": bundle.scenario.duration_us,
        }
    )

    pending_releases: list[WorkloadRelease] = []
    for timestamp_us in range(0, bundle.scenario.duration_us, bundle.scenario.tick_us):
        releases = generator.release(timestamp_us=timestamp_us)
        pending_releases.extend(releases)
        for release in releases:
            writer.write_workload_event(
                {
                    "event_type": "workload_release",
                    "timestamp_us": release.timestamp_us,
                    "node_id": release.node_id,
                    "source": release.source,
                    "criticality": release.criticality,
                    "predicted_latency_us": release.predicted_latency_us,
                }
            )

        observation = SchedulerObservation(
            timestamp_us=timestamp_us,
            runnable_nodes=[
                RunnableNode(
                    node_id=release.node_id,
                    source=release.source,
                    criticality=release.criticality,
                    predicted_latency_us=release.predicted_latency_us,
                    timestamp_us=release.timestamp_us,
                )
                for release in pending_releases
            ],
        )
        writer.write_scheduler_observation(
            {
                "event_type": "scheduler_observation",
                "timestamp_us": timestamp_us,
                "runnable_nodes": [
                    {
                        "node_id": node.node_id,
                        "source": node.source,
                        "criticality": node.criticality,
                        "predicted_latency_us": node.predicted_latency_us,
                        "released_at_us": node.timestamp_us,
                    }
                    for node in observation.runnable_nodes
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
                        "source": node.source,
                        "criticality": node.criticality,
                        "predicted_latency_us": node.predicted_latency_us,
                    }
                    for node in started_nodes
                ],
            }
        )
        pending_releases = _remove_started_releases(
            pending_releases=pending_releases,
            started_nodes=started_nodes,
        )

        writer.write_runtime_execution(runtime.advance_tick(timestamp_us=timestamp_us))
    return 0


def _build_workload_generator(bundle) -> WorkloadGenerator:
    critical_tasks = [
        CriticalTaskSpec(
            node_id=node.node_id,
            period_us=node.period_us,
            criticality=node.criticality,
            predicted_latency_us=node.predicted_latency_us,
        )
        for task in bundle.tasks.values()
        for node in task.critical_nodes
    ]
    agent_arrivals = [
        AgentArrivalSpec(
            node_id=request.node_id,
            arrival_time_us=request.arrival_time_us,
            criticality=request.criticality,
            predicted_latency_us=request.predicted_latency_us,
        )
        for request in bundle.scenario.agent_requests
    ]
    return WorkloadGenerator(
        critical_tasks=critical_tasks,
        agent_arrivals=agent_arrivals,
    )


def _remove_started_releases(
    *,
    pending_releases: list[WorkloadRelease],
    started_nodes: list[RunnableNode],
) -> list[WorkloadRelease]:
    remaining = list(pending_releases)
    for node in started_nodes:
        for index, release in enumerate(remaining):
            if release.node_id == node.node_id and release.source == node.source:
                remaining.pop(index)
                break
    return remaining
