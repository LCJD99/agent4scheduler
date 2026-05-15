from offline.evolution.proposal import CandidateGenerator
from offline.replay.runner import ReplayRunner


VALID_SOURCE = """
from scheduler_sim.scheduler.base import Scheduler, SchedulerDecision, SchedulerObservation


class EvolvedScheduler(Scheduler):
    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:
        return SchedulerDecision(allocations=[], timestamp_us=observation.timestamp_us)


def create_scheduler(parameters=None):
    return EvolvedScheduler()
"""


class FakeCodegenAgent:
    def generate(self, **kwargs):
        return {
            "scheduler_source": VALID_SOURCE,
            "rationale": "Fake generated scheduler.",
            "constraints_satisfied": ["defines create_scheduler"],
        }


def test_candidate_generator_emits_scheduler_source_code():
    candidates = CandidateGenerator(codegen_agent=FakeCodegenAgent()).generate(
        advice_branches=[
            {
                "branch_id": "branch_critical_headroom",
                "parameters": {"agent_cpu_reservation_cores": 1.0},
                "proposed_heuristic_change": "Reserve CPU headroom before agent launches.",
            }
        ],
        max_candidates=1,
    )

    candidate = candidates[0]

    assert candidate["scheduler_type"] == "generated_python_scheduler"
    assert candidate["scheduler_entrypoint"] == "create_scheduler"
    assert "scheduler_source" in candidate
    assert "class EvolvedScheduler" in candidate["scheduler_source"]
    assert candidate["codegen_rationale"] == "Fake generated scheduler."


def test_replay_runner_writes_generated_scheduler_code_and_uses_scheduler_code_arg(
    tmp_path, monkeypatch
):
    calls = []

    def fake_scheduler_app_main(argv):
        calls.append(argv)
        output_dir = tmp_path / "replays" / "20260512-150000" / "candidate_1_branch" / "run-001"
        output_dir.mkdir(parents=True)
        return 0

    monkeypatch.setattr(
        "offline.replay.runner.scheduler_app_main",
        fake_scheduler_app_main,
    )
    candidate = CandidateGenerator(codegen_agent=FakeCodegenAgent()).generate(
        advice_branches=[
            {
                "branch_id": "branch",
                "parameters": {"agent_cpu_reservation_cores": 1.0},
                "proposed_heuristic_change": "Reserve CPU headroom before agent launches.",
            }
        ],
        max_candidates=1,
    )[0]

    result = ReplayRunner().run(
        candidate=candidate,
        scenario_path="configs/scenarios/home_eqa_scenario_001.yaml",
        replay_output=tmp_path / "replays" / "20260512-150000",
    )

    scheduler_code_path = (
        tmp_path
        / "replays"
        / "20260512-150000"
        / candidate["candidate_id"]
        / "scheduler_candidate.py"
    )
    assert scheduler_code_path.exists()
    assert "class EvolvedScheduler" in scheduler_code_path.read_text(encoding="utf-8")
    assert "--scheduler-code" in calls[0]
    assert str(scheduler_code_path) in calls[0]
    assert result["scheduler_code"] == str(scheduler_code_path)
