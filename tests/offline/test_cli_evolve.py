import json
import re

from offline.cli import main as offline_main
from scheduler_sim.app import main as app_main


def write_offline_analyzer_config(path, *, api_key_env):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "metadata:",
                "  name: trace_analyzer_openai",
                "",
                "provider:",
                "  api: openai",
                "  base_url: https://api.openai.com/v1",
                f"  api_key_env: {api_key_env}",
                "",
                "model:",
                "  name: gpt-5.4",
                "  reasoning_effort: medium",
                "",
                "runtime:",
                "  timeout_s: 60",
                "  max_windows: 5",
                "",
            ]
        ),
        encoding="utf-8",
    )


class FakeResponsesAPI:
    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return type(
            "FakeResponse",
            (),
            {
                "output_text": json.dumps(
                    {
                        "findings": [
                            {
                                "defect_type": "critical_deadline_miss",
                                "severity": "high",
                                "affected_nodes": ["localization_node"],
                                "root_cause_hypothesis": "agent launches were admitted near the missed critical deadline",
                                "natural_language_advice": "reserve CPU headroom before low-criticality launches",
                                "window_refs": [0],
                            }
                        ]
                    }
                )
            },
        )()


class FakeOpenAIClient:
    def __init__(self):
        self.responses = FakeResponsesAPI()


class FakeCodegenResponsesAPI:
    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return type(
            "FakeResponse",
            (),
            {
                "output_text": json.dumps(
                    {
                        "scheduler_source": "\n".join(
                            [
                                "from scheduler_sim.scheduler.base import Scheduler, SchedulerDecision, SchedulerObservation",
                                "",
                                "",
                                "class EvolvedScheduler(Scheduler):",
                                "    def __init__(self, *, parameters=None):",
                                "        self.parameters = parameters or {}",
                                "",
                                "    def decide(self, observation: SchedulerObservation) -> SchedulerDecision:",
                                "        return SchedulerDecision(allocations=[], timestamp_us=observation.timestamp_us)",
                                "",
                                "",
                                "def create_scheduler(parameters=None):",
                                "    return EvolvedScheduler(parameters=parameters)",
                                "",
                            ]
                        ),
                        "rationale": "Fake generated scheduler for CLI integration.",
                        "constraints_satisfied": ["defines create_scheduler"],
                    }
                )
            },
        )()


class FakeCodegenOpenAIClient:
    def __init__(self):
        self.responses = FakeCodegenResponsesAPI()


def test_offline_cli_evolves_trace_run_and_persists_replay_result(tmp_path, monkeypatch):
    baseline_root = tmp_path / "baseline"
    replay_root = tmp_path / "replays"
    memory_path = tmp_path / "offline.db"
    config_path = tmp_path / "configs" / "offline" / "trace_analyzer_openai.yaml"
    write_offline_analyzer_config(config_path, api_key_env="TRACE_ANALYZER_TEST_KEY")
    monkeypatch.setenv("TRACE_ANALYZER_TEST_KEY", "test-key")
    monkeypatch.setattr(
        "offline.analysis.llm_agent.DEFAULT_OPENAI_CLIENT_FACTORY",
        lambda **_: FakeOpenAIClient(),
    )
    monkeypatch.setattr(
        "offline.evolution.llm_codegen.DEFAULT_OPENAI_CLIENT_FACTORY",
        lambda **_: FakeCodegenOpenAIClient(),
    )

    assert (
        app_main(
            [
                "--scenario",
                "configs/scenarios/home_eqa_scenario_001.yaml",
                "--trace-output",
                str(baseline_root),
            ]
        )
        == 0
    )
    trace_run = next(path for path in baseline_root.iterdir() if path.is_dir())

    code = offline_main(
        [
            "evolve",
            "--trace-run",
            str(trace_run),
            "--memory",
            str(memory_path),
            "--replay-output",
            str(replay_root),
            "--analyzer-config",
            str(config_path),
            "--max-candidates",
            "2",
        ]
    )

    run_dirs = [path for path in replay_root.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    assert re.fullmatch(r"\d{8}-\d{6}", run_dirs[0].name)
    run_dir = run_dirs[0]
    result_path = run_dir / "offline_evolution_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert code == 0
    assert result["evolution_run_id"] == run_dir.name
    assert result["trace_findings"]
    assert result["trace_findings"][0]["analysis_mode"] == "openai_llm_agent"
    assert len(result["advice_branches"]) >= 2
    assert len(result["candidate_schedulers"]) == 2
    assert result["candidate_schedulers"][0]["scheduler_type"] == (
        "generated_python_scheduler"
    )
    scheduler_source = result["candidate_schedulers"][0]["scheduler_source"]
    assert "class EvolvedScheduler" in scheduler_source
    prompt_path = result["candidate_schedulers"][0]["prompt_markdown_path"]
    assert prompt_path.endswith("_scheduler_codegen_prompt.md")
    assert run_dir.joinpath("prompt_debug").exists()
    assert result["replay_results"]
    assert result["replay_results"][0]["scheduler_code"].endswith(
        "scheduler_candidate.py"
    )
    assert run_dir.name in result["replay_results"][0]["scheduler_code"]
    assert run_dir.name in result["replay_results"][0]["trace_run"]
    assert (run_dir / "offline_case.json").exists()
    assert result["selected_candidate"] is not None
    assert memory_path.exists()
