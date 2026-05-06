from scheduler_sim.planner.agent import plan_request


def test_plan_request_returns_dag_template_for_known_prompt():
    dag = plan_request("What objects are on the table?")
    assert len(dag.nodes) >= 2
    assert dag.edges
