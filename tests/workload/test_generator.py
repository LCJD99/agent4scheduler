from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.workload.generator import WorkloadGenerator
from scheduler_sim.workload.instances import AgentArrivalSpec, ToolExecutionSpec


def test_generator_releases_periodic_critical_node_on_tick_boundary():
    generator = WorkloadGenerator.critical_only(
        node_id="local_planner_node",
        period_us=50_000,
    )

    events = generator.release(timestamp_us=50_000)

    assert any(event.node_id == "local_planner_node" for event in events)


def test_generator_releases_agent_roots_on_arrival_and_dependents_after_completion():
    generator = WorkloadGenerator(
        agent_arrivals=[
            AgentArrivalSpec(
                request_id="agent-home-eqa-request-001",
                user_request="What objects are on the table?",
                arrival_time_us=2_000,
                criticality="low",
            )
        ],
        tool_execution_specs={
            "object_detection": ToolExecutionSpec(
                predicted_latency_us=3_000,
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=256),
            )
        },
    )

    arrival_releases = generator.release(timestamp_us=2_000)

    assert [release.node_id for release in arrival_releases] == ["detect_table"]
    assert arrival_releases[0].task_instance_id == "agent-home-eqa-request-001"
    assert arrival_releases[0].node_instance_id == "agent-home-eqa-request-001:detect_table:0"
    assert arrival_releases[0].resource_demand == ResourceVector(
        cpu_cores=1.0,
        memory_mb=256,
    )

    dependent_releases = generator.release_on_completions(
        timestamp_us=5_000,
        completed_node_instance_ids=[arrival_releases[0].node_instance_id],
    )

    assert [release.node_id for release in dependent_releases] == ["identify_objects"]
    assert dependent_releases[0].task_instance_id == "agent-home-eqa-request-001"
    assert dependent_releases[0].node_instance_id == "agent-home-eqa-request-001:identify_objects:0"


def test_generator_exposes_agent_task_definition_and_completion_outcome():
    generator = WorkloadGenerator(
        agent_arrivals=[
            AgentArrivalSpec(
                request_id="agent-home-eqa-request-001",
                user_request="What objects are on the table?",
                arrival_time_us=2_000,
                criticality="low",
            )
        ],
        tool_execution_specs={
            "object_detection": ToolExecutionSpec(
                predicted_latency_us=3_000,
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=256),
            )
        },
    )

    root_releases = generator.release(timestamp_us=2_000)
    definitions = generator.drain_task_definitions()

    assert [definition["task_instance_id"] for definition in definitions] == [
        "agent-home-eqa-request-001"
    ]
    assert definitions[0]["node_ids"] == ["detect_table", "identify_objects"]
    assert definitions[0]["edges"] == [["detect_table", "identify_objects"]]

    next_releases = generator.release_on_completions(
        timestamp_us=5_000,
        completed_node_instance_ids=[root_releases[0].node_instance_id],
    )
    outcomes_before_finish = generator.drain_task_outcomes()

    assert [release.node_id for release in next_releases] == ["identify_objects"]
    assert outcomes_before_finish == []

    generator.release_on_completions(
        timestamp_us=8_000,
        completed_node_instance_ids=[next_releases[0].node_instance_id],
    )
    outcomes = generator.drain_task_outcomes()

    assert len(outcomes) == 1
    assert outcomes[0]["event_type"] == "task_outcome"
    assert outcomes[0]["outcome_type"] == "agent_task_instance"
    assert outcomes[0]["task_instance_id"] == "agent-home-eqa-request-001"
    assert outcomes[0]["source"] == "agent"
    assert outcomes[0]["completed_at_us"] == 8_000
    assert outcomes[0]["total_completion_time_us"] == 6_000
    assert outcomes[0]["completed_node_ids"] == ["detect_table", "identify_objects"]
