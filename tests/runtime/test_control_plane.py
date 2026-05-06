from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.runtime.control_plane import SchedulerControlPlane
from scheduler_sim.runtime.engine import RuntimeEngine
from scheduler_sim.scheduler.base import RunnableNode, SchedulerDecision


def build_decision_with_one_node() -> SchedulerDecision:
    return SchedulerDecision(
        selected_nodes=[
            RunnableNode(
                node_id="critical-node",
                node_instance_id="critical-node:0",
                task_instance_id="critical-node",
                source="critical",
                criticality="high",
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=128),
            )
        ]
    )


def test_control_plane_starts_selected_nodes_in_runtime():
    control_plane = SchedulerControlPlane(
        runtime=RuntimeEngine(
            tick_us=20,
            system_capacity=ResourceVector(cpu_cores=2.0, memory_mb=1024),
        )
    )
    control_plane.apply(decision=build_decision_with_one_node())

    assert control_plane.runtime.running_count == 1
