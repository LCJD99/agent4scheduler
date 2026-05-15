import json

import pytest

from offline.config_loader import OfflineAnalyzerConfig
from offline.evolution.llm_codegen import OpenAISchedulerCodegenAgent
from offline.evolution.proposal import CandidateGenerator


VALID_SOURCE = """
from scheduler_sim.scheduler.base import Scheduler, SchedulerDecision, SchedulerObservation


class EvolvedScheduler(Scheduler):
    def __init__(self, *, parameters=None):
        self.parameters = parameters or {}

    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        return SchedulerDecision(allocations=[], timestamp_us=observation.timestamp_us)


def create_scheduler(parameters=None):
    return EvolvedScheduler(parameters=parameters)
"""


class FakeResponsesAPI:
    def __init__(self, payload):
        self.payload = payload
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return type("FakeResponse", (), {"output_text": json.dumps(self.payload)})()


class FakeOpenAIClient:
    def __init__(self, payload):
        self.responses = FakeResponsesAPI(payload)


def config():
    return OfflineAnalyzerConfig(
        metadata_name="trace_analyzer_openai",
        provider_api="openai",
        base_url="https://api.openai.com/v1",
        api_key_env="SCHEDULER_CODEGEN_TEST_KEY",
        model_name="gpt-5.4",
        reasoning_effort="medium",
        timeout_s=60,
        max_windows=5,
    )


def test_openai_scheduler_codegen_sends_protocol_and_constraints_context(monkeypatch):
    fake_client = FakeOpenAIClient(
        {
            "scheduler_source": VALID_SOURCE,
            "rationale": "Use an empty safe scheduler for the unit test.",
            "constraints_satisfied": ["defines create_scheduler", "no file IO"],
        }
    )
    monkeypatch.setenv("SCHEDULER_CODEGEN_TEST_KEY", "test-key")

    agent = OpenAISchedulerCodegenAgent(
        config=config(),
        client_factory=lambda **_: fake_client,
    )

    result = agent.generate(
        candidate_id="candidate_1_branch",
        advice_branch={
            "branch_id": "branch",
            "proposed_heuristic_change": "Reserve CPU headroom.",
            "parameters": {"agent_cpu_reservation_cores": 1.0},
        },
        workload_signature={"scene_complexity": "large"},
        trace_findings=[{"defect_type": "critical_deadline_miss"}],
        similar_cases=[],
    )

    kwargs = fake_client.responses.last_kwargs
    system_prompt = kwargs["input"][0]["content"]
    user_payload = kwargs["input"][1]["content"]

    assert result["scheduler_source"] == VALID_SOURCE
    assert kwargs["text"]["format"]["type"] == "json_schema"
    assert kwargs["text"]["format"]["strict"] is True
    assert "Scheduler.decide(observation) -> SchedulerDecision" in system_prompt
    assert "create_scheduler(parameters=None)" in system_prompt
    assert "Do not read or write files" in system_prompt
    assert "scheduler_sim.scheduler.base" in system_prompt
    assert "Allowed API symbols:" in system_prompt
    assert "Allowed observation fields:" in system_prompt
    assert "If you are not certain an API or field exists, do not use it." in system_prompt
    assert "Current scheduler implementation context:" in system_prompt
    assert "Reference scheduler API context:" in system_prompt
    assert "class HeuristicScheduler" in system_prompt
    assert "class SchedulerDecision" in system_prompt
    assert "Reserve CPU headroom" in user_payload
    assert "critical_deadline_miss" in user_payload


def test_openai_scheduler_codegen_writes_prompt_markdown_before_request(
    monkeypatch, tmp_path
):
    fake_client = FakeOpenAIClient(
        {
            "scheduler_source": VALID_SOURCE,
            "rationale": "Use an empty safe scheduler for the unit test.",
            "constraints_satisfied": ["defines create_scheduler", "no file IO"],
        }
    )
    monkeypatch.setenv("SCHEDULER_CODEGEN_TEST_KEY", "test-key")

    agent = OpenAISchedulerCodegenAgent(
        config=config(),
        client_factory=lambda **_: fake_client,
    )

    result = agent.generate(
        candidate_id="candidate_1_branch",
        advice_branch={"branch_id": "branch", "parameters": {}},
        workload_signature={"scene_complexity": "large"},
        trace_findings=[{"defect_type": "critical_deadline_miss"}],
        similar_cases=[],
        prompt_output_dir=tmp_path,
    )

    prompt_path = tmp_path / "candidate_1_branch_scheduler_codegen_prompt.md"
    markdown = prompt_path.read_text(encoding="utf-8")

    assert result["prompt_markdown_path"] == str(prompt_path)
    assert prompt_path.exists()
    assert "# Scheduler Codegen Prompt" in markdown
    assert "## System Prompt" in markdown
    assert "## User Payload" in markdown
    assert "## Current Scheduler Source" in markdown
    assert "## Reference Scheduler Base Source" in markdown
    assert "class HeuristicScheduler" in markdown
    assert "class SchedulerDecision" in markdown
    assert "critical_deadline_miss" in markdown


def test_candidate_generator_uses_llm_codegen_agent_for_scheduler_source():
    class FakeCodegenAgent:
        def generate(self, **kwargs):
            return {
                "scheduler_source": VALID_SOURCE,
                "rationale": "Generated by fake LLM.",
                "constraints_satisfied": ["defines create_scheduler"],
                "prompt_markdown_path": "/tmp/prompt.md",
            }

    candidates = CandidateGenerator(codegen_agent=FakeCodegenAgent()).generate(
        advice_branches=[
            {
                "branch_id": "branch",
                "parameters": {"agent_cpu_reservation_cores": 1.0},
                "proposed_heuristic_change": "Reserve CPU headroom.",
            }
        ],
        max_candidates=1,
        workload_signature={"scene_complexity": "large"},
        trace_findings=[{"defect_type": "critical_deadline_miss"}],
        similar_cases=[],
    )

    assert candidates[0]["scheduler_source"] == VALID_SOURCE
    assert candidates[0]["codegen_rationale"] == "Generated by fake LLM."
    assert candidates[0]["constraints_satisfied"] == ["defines create_scheduler"]
    assert candidates[0]["prompt_markdown_path"] == "/tmp/prompt.md"


def test_openai_scheduler_codegen_rejects_code_that_violates_constraints(monkeypatch):
    fake_client = FakeOpenAIClient(
        {
            "scheduler_source": "def create_scheduler(parameters=None):\n    return open('/tmp/x')\n",
            "rationale": "Bad code.",
            "constraints_satisfied": [],
        }
    )
    monkeypatch.setenv("SCHEDULER_CODEGEN_TEST_KEY", "test-key")

    agent = OpenAISchedulerCodegenAgent(
        config=config(),
        client_factory=lambda **_: fake_client,
    )

    with pytest.raises(ValueError, match="forbidden pattern"):
        agent.generate(
            candidate_id="candidate_1_branch",
            advice_branch={"branch_id": "branch", "parameters": {}},
            workload_signature={},
            trace_findings=[],
            similar_cases=[],
        )


def test_scheduler_codegen_rejects_unknown_resource_vector_fields():
    from offline.evolution.schemas import validate_scheduler_source

    bad_source = """
from scheduler_sim.scheduler.base import Scheduler, SchedulerDecision


class EvolvedScheduler(Scheduler):
    def decide(self, observation):
        _ = observation.available_resources.gpu_units
        return SchedulerDecision(allocations=[], timestamp_us=observation.timestamp_us)


def create_scheduler(parameters=None):
    return EvolvedScheduler()
"""

    with pytest.raises(ValueError, match="forbidden pattern"):
        validate_scheduler_source(bad_source)


def test_scheduler_codegen_allows_valid_memory_mb_field():
    from offline.evolution.schemas import validate_scheduler_source

    valid_source = """
from scheduler_sim.scheduler.base import Scheduler, SchedulerDecision


class EvolvedScheduler(Scheduler):
    def decide(self, observation):
        _ = observation.available_resources.memory_mb
        return SchedulerDecision(allocations=[], timestamp_us=observation.timestamp_us)


def create_scheduler(parameters=None):
    return EvolvedScheduler()
"""

    validate_scheduler_source(valid_source)


def test_scheduler_codegen_reports_runtime_validation_for_unknown_memory_field():
    from offline.evolution.schemas import validate_scheduler_source

    bad_source = """
from scheduler_sim.scheduler.base import Scheduler, SchedulerDecision


class EvolvedScheduler(Scheduler):
    def decide(self, observation):
        _ = observation.available_resources.memory
        return SchedulerDecision(allocations=[], timestamp_us=observation.timestamp_us)


def create_scheduler(parameters=None):
    return EvolvedScheduler()
"""

    with pytest.raises(ValueError, match="Generated scheduler decide failed"):
        validate_scheduler_source(bad_source)
