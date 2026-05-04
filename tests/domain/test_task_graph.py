from scheduler_sim.domain.tasks import TaskGraph


def test_task_graph_rejects_cycles():
    graph = TaskGraph(
        nodes=["a", "b"],
        edges=[("a", "b"), ("b", "a")],
    )
    assert graph.validate().is_ok is False
