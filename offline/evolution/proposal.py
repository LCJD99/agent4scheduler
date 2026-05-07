from typing import Any


class CandidateGenerator:
    def generate(
        self, *, advice_branches: list[dict[str, Any]], max_candidates: int
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for index, branch in enumerate(advice_branches[:max_candidates], 1):
            candidates.append(
                {
                    "candidate_id": f"candidate_{index}_{branch['branch_id']}",
                    "scheduler_type": "parameterized_heuristic",
                    "parameters": dict(branch.get("parameters", {})),
                    "source_advice_branch": branch["branch_id"],
                }
            )
        return candidates
