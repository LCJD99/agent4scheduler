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
    assert events[0].task_instance_id.startswith("critical-local_planner_node-")
    assert events[0].node_instance_id.startswith("critical-local_planner_node-")


def test_generator_releases_agent_roots_on_arrival_and_dependents_after_completion():
    generator = WorkloadGenerator(
        agent_arrivals=[
            AgentArrivalSpec(
                request_id="agent-caption-pipeline",
                user_request="Describe, translate, and speak the latest image.",
                arrival_time_us=2_000,
                criticality="low",
            )
        ],
        tool_execution_specs={
            "image_captioning": ToolExecutionSpec(
                predicted_latency_us=4_000,
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=512),
            ),
            "text_translation": ToolExecutionSpec(
                predicted_latency_us=2_000,
                resource_demand=ResourceVector(cpu_cores=0.5, memory_mb=128),
            ),
            "text_to_speech": ToolExecutionSpec(
                predicted_latency_us=3_000,
                resource_demand=ResourceVector(cpu_cores=0.5, memory_mb=256),
            )
        },
    )

    arrival_releases = generator.release(timestamp_us=2_000)

    assert [release.node_id for release in arrival_releases] == ["image_captioning"]
    assert arrival_releases[0].task_instance_id.startswith("agent-caption-pipeline-")
    assert arrival_releases[0].node_instance_id.endswith("--image_captioning")
    assert arrival_releases[0].resource_demand == ResourceVector(
        cpu_cores=1.0,
        memory_mb=512,
    )

    dependent_releases = generator.release_on_completions(
        timestamp_us=6_000,
        completed_node_instance_ids=[arrival_releases[0].node_instance_id],
    )

    assert [release.node_id for release in dependent_releases] == ["text_translation"]
    assert dependent_releases[0].task_instance_id == arrival_releases[0].task_instance_id
    assert dependent_releases[0].node_instance_id.endswith("--text_translation")

    final_releases = generator.release_on_completions(
        timestamp_us=8_000,
        completed_node_instance_ids=[dependent_releases[0].node_instance_id],
    )

    assert [release.node_id for release in final_releases] == ["text_to_speech"]
    assert final_releases[0].node_instance_id.endswith("--text_to_speech")


def test_generator_exposes_agent_task_definition_and_completion_outcome():
    generator = WorkloadGenerator(
        agent_arrivals=[
            AgentArrivalSpec(
                request_id="agent-caption-pipeline",
                user_request="Describe, translate, and speak the latest image.",
                arrival_time_us=2_000,
                criticality="low",
            )
        ],
        tool_execution_specs={
            "image_captioning": ToolExecutionSpec(
                predicted_latency_us=4_000,
                resource_demand=ResourceVector(cpu_cores=1.0, memory_mb=512),
            ),
            "text_translation": ToolExecutionSpec(
                predicted_latency_us=2_000,
                resource_demand=ResourceVector(cpu_cores=0.5, memory_mb=128),
            ),
            "text_to_speech": ToolExecutionSpec(
                predicted_latency_us=3_000,
                resource_demand=ResourceVector(cpu_cores=0.5, memory_mb=256),
            )
        },
    )

    root_releases = generator.release(timestamp_us=2_000)
    definitions = generator.drain_task_definitions()

    assert len(definitions) == 1
    assert definitions[0]["task_instance_id"].startswith("agent-caption-pipeline-")
    assert definitions[0]["node_ids"] == [
        "image_captioning",
        "text_translation",
        "text_to_speech",
    ]
    assert definitions[0]["edges"] == [
        ["image_captioning", "text_translation"],
        ["text_translation", "text_to_speech"],
    ]

    next_releases = generator.release_on_completions(
        timestamp_us=6_000,
        completed_node_instance_ids=[root_releases[0].node_instance_id],
    )
    outcomes_before_finish = generator.drain_task_outcomes()

    assert [release.node_id for release in next_releases] == ["text_translation"]
    assert outcomes_before_finish == []

    final_releases = generator.release_on_completions(
        timestamp_us=8_000,
        completed_node_instance_ids=[next_releases[0].node_instance_id],
    )
    assert [release.node_id for release in final_releases] == ["text_to_speech"]
    generator.release_on_completions(
        timestamp_us=11_000,
        completed_node_instance_ids=[final_releases[0].node_instance_id],
    )
    outcomes = generator.drain_task_outcomes()

    assert len(outcomes) == 1
    assert outcomes[0]["event_type"] == "task_outcome"
    assert outcomes[0]["outcome_type"] == "agent_task_instance"
    assert outcomes[0]["task_instance_id"].startswith("agent-caption-pipeline-")
    assert outcomes[0]["source"] == "agent"
    assert outcomes[0]["completed_at_us"] == 11_000
    assert outcomes[0]["total_completion_time_us"] == 9_000
    assert outcomes[0]["completed_node_ids"] == [
        "image_captioning",
        "text_translation",
        "text_to_speech",
    ]
