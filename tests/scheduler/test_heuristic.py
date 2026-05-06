from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import RunningNode, RunnableNode, SchedulerObservation
from scheduler_sim.scheduler.heuristic import HeuristicScheduler


def build_observation_with_critical_and_agent() -> SchedulerObservation:
    return SchedulerObservation(
        available_resources=ResourceVector(cpu_cores=2.0, memory_mb=1024),
        runnable_nodes=[
            RunnableNode(
                node_id="agent-node",
                node_instance_id="req-1:agent-node:0",
                task_instance_id="req-1",
                source="agent",
                criticality="low",
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
            ),
            RunnableNode(
                node_id="critical-node",
                node_instance_id="critical-node:0",
                task_instance_id="critical-node",
                source="critical",
                criticality="high",
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
            ),
        ]
    )


def test_scheduler_prioritizes_critical_nodes_before_agent_nodes():
    scheduler = HeuristicScheduler()
    decision = scheduler.decide(observation=build_observation_with_critical_and_agent())
    assert decision.selected_nodes[0].criticality == "high"


def test_scheduler_selects_only_nodes_that_fit_remaining_capacity():
    scheduler = HeuristicScheduler()
    observation = SchedulerObservation(
        timestamp_us=1_000,
        available_resources=ResourceVector(cpu_cores=2.0, memory_mb=1024),
        runnable_nodes=[
            RunnableNode(
                node_id="critical-overflow",
                node_instance_id="critical-overflow:0",
                task_instance_id="critical-overflow",
                source="critical",
                criticality="high",
                resource_demand=ResourceVector(cpu_cores=3.0, memory_mb=128),
            ),
            RunnableNode(
                node_id="critical-fit",
                node_instance_id="critical-fit:0",
                task_instance_id="critical-fit",
                source="critical",
                criticality="high",
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
            ),
            RunnableNode(
                node_id="agent-fit",
                node_instance_id="req-2:agent-fit:0",
                task_instance_id="req-2",
                source="agent",
                criticality="low",
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
            ),
        ],
    )

    decision = scheduler.decide(observation=observation)

    assert [node.node_id for node in decision.selected_nodes] == [
        "critical-fit",
        "agent-fit",
    ]


def test_scheduler_observation_carries_running_nodes():
    observation = SchedulerObservation(
        timestamp_us=2_000,
        available_resources=ResourceVector(cpu_cores=2.0, memory_mb=1024),
        runnable_nodes=[],
        running_nodes=[
            RunningNode(
                node_id="running-critical",
                node_instance_id="critical-001--localization_node",
                task_instance_id="critical-localization-001",
                source="critical",
                criticality="high",
                started_at_us=1_500,
                resource_demand=ResourceVector(cpu_cores=0.5, memory_mb=128),
            )
        ],
    )

    assert observation.running_nodes[0].node_id == "running-critical"
    assert observation.running_nodes[0].started_at_us == 1_500
