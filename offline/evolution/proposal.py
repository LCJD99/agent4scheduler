from typing import Any

from offline.config_loader import load_offline_analyzer_config
from offline.evolution.llm_codegen import OpenAISchedulerCodegenAgent


class CandidateGenerator:
    def __init__(self, *, codegen_agent: Any | None = None) -> None:
        self.codegen_agent = codegen_agent

    def generate(
        self,
        *,
        advice_branches: list[dict[str, Any]],
        max_candidates: int,
        workload_signature: dict[str, Any] | None = None,
        trace_findings: list[dict[str, Any]] | None = None,
        similar_cases: list[dict[str, Any]] | None = None,
        codegen_config_path: str | None = None,
        prompt_output_dir: str | None = None,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        codegen_agent = self.codegen_agent or self._build_default_codegen_agent(
            codegen_config_path=codegen_config_path
        )
        for index, branch in enumerate(advice_branches[:max_candidates], 1):
            parameters = dict(branch.get("parameters", {}))
            candidate_id = f"candidate_{index}_{branch['branch_id']}"
            generated = codegen_agent.generate(
                candidate_id=candidate_id,
                advice_branch=branch,
                workload_signature=workload_signature or {},
                trace_findings=trace_findings or [],
                similar_cases=similar_cases or [],
                prompt_output_dir=prompt_output_dir,
            )
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "scheduler_type": "generated_python_scheduler",
                    "scheduler_entrypoint": "create_scheduler",
                    "parameters": parameters,
                    "scheduler_source": generated["scheduler_source"],
                    "codegen_rationale": generated["rationale"],
                    "constraints_satisfied": generated["constraints_satisfied"],
                    "prompt_markdown_path": generated.get("prompt_markdown_path"),
                    "source_advice_branch": branch["branch_id"],
                }
            )
        return candidates

    @staticmethod
    def _build_default_codegen_agent(
        *, codegen_config_path: str | None
    ) -> OpenAISchedulerCodegenAgent:
        config = load_offline_analyzer_config(
            codegen_config_path or "configs/offline/trace_analyzer_openai.yaml"
        )
        return OpenAISchedulerCodegenAgent(config=config)
