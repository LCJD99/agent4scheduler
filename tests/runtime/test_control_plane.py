from scheduler_sim.runtime.control_plane import SchedulerControlPlane
from scheduler_sim.runtime.engine import RuntimeEngine
from scheduler_sim.scheduler.base import RunnableNode, SchedulerDecision


def build_decision_with_one_node() -> SchedulerDecision:
    return SchedulerDecision(
        selected_nodes=[
            RunnableNode(
                node_id="critical-node",
                source="critical",
                criticality="high",
            )
        ]
    )


def test_control_plane_starts_selected_nodes_in_runtime():
    control_plane = SchedulerControlPlane(runtime=RuntimeEngine(tick_us=20))
    control_plane.apply(decision=build_decision_with_one_node())

    assert control_plane.runtime.running_count == 1
