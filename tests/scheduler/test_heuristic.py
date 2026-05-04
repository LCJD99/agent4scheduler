from scheduler_sim.scheduler.base import RunnableNode, SchedulerObservation
from scheduler_sim.scheduler.heuristic import HeuristicScheduler


def build_observation_with_critical_and_agent() -> SchedulerObservation:
    return SchedulerObservation(
        runnable_nodes=[
            RunnableNode(node_id="agent-node", source="agent", criticality="low"),
            RunnableNode(node_id="critical-node", source="critical", criticality="high"),
        ]
    )


def test_scheduler_prioritizes_critical_nodes_before_agent_nodes():
    scheduler = HeuristicScheduler()
    decision = scheduler.decide(observation=build_observation_with_critical_and_agent())
    assert decision.selected_nodes[0].criticality == "high"
