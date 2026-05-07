from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.scheduler.base import RunnableNode, SchedulerObservation
from scheduler_sim.scheduler.parameterized import ParameterizedHeuristicScheduler


def test_parameterized_scheduler_reserves_cpu_headroom_for_agent_nodes():
    scheduler = ParameterizedHeuristicScheduler(
        parameters={"agent_cpu_reservation_cores": 1.5}
    )
    observation = SchedulerObservation(
        timestamp_us=1_000,
        available_resources=ResourceVector(cpu_cores=2.0, memory_mb=1024),
        runnable_nodes=[
            RunnableNode(
                node_id="agent-node",
                node_instance_id="agent-node:0",
                task_instance_id="agent-task",
                tool_name="image_captioning",
                source="agent",
                criticality="low",
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
            ),
            RunnableNode(
                node_id="critical-node",
                node_instance_id="critical-node:0",
                task_instance_id="critical-task",
                tool_name="localization_node",
                source="critical",
                criticality="high",
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
            ),
        ],
    )

    decision = scheduler.decide(observation=observation)

    assert [allocation.node.node_id for allocation in decision.allocations] == [
        "critical-node"
    ]


def test_parameterized_scheduler_boosts_starved_agent_nodes_after_threshold():
    scheduler = ParameterizedHeuristicScheduler(
        parameters={"agent_starvation_boost_after_us": 500}
    )
    observation = SchedulerObservation(
        timestamp_us=2_000,
        available_resources=ResourceVector(cpu_cores=2.0, memory_mb=1024),
        runnable_nodes=[
            RunnableNode(
                node_id="fresh-critical",
                node_instance_id="fresh-critical:0",
                task_instance_id="critical-task",
                tool_name="navigation_algo_node",
                source="critical",
                criticality="medium",
                timestamp_us=1_900,
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
            ),
            RunnableNode(
                node_id="starved-agent",
                node_instance_id="starved-agent:0",
                task_instance_id="agent-task",
                tool_name="text_translation",
                source="agent",
                criticality="low",
                timestamp_us=1_000,
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
            ),
        ],
    )

    decision = scheduler.decide(observation=observation)

    assert decision.allocations[0].node.node_id == "starved-agent"
