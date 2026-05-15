import argparse
from datetime import datetime
from pathlib import Path

from offline.graph import nodes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="offline-evolution")
    subparsers = parser.add_subparsers(dest="command", required=True)
    evolve = subparsers.add_parser("evolve")
    evolve.add_argument("--trace-run", required=True)
    evolve.add_argument("--memory", required=True)
    evolve.add_argument("--replay-output", required=True)
    evolve.add_argument(
        "--analyzer-config",
        default="configs/offline/trace_analyzer_openai.yaml",
    )
    evolve.add_argument("--max-candidates", type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "evolve":
        Path(args.replay_output).mkdir(parents=True, exist_ok=True)
        return _run_evolve(args)
    return 1


def _run_evolve(args: argparse.Namespace) -> int:
    evolution_run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    evolution_output_dir = Path(args.replay_output) / evolution_run_id
    evolution_output_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "trace_run_path": args.trace_run,
        "memory_path": args.memory,
        "replay_output_root": args.replay_output,
        "replay_output": str(evolution_output_dir),
        "evolution_run_id": evolution_run_id,
        "analyzer_config_path": args.analyzer_config,
        "max_candidates": args.max_candidates,
    }
    steps = [
        ("load_trace", nodes.load_trace),
        ("profile_workload", nodes.profile_workload),
        ("retrieve_similar_workloads", nodes.retrieve_similar_workloads),
        ("analyze_scheduler_defects", nodes.analyze_scheduler_defects),
        ("generate_advice_branches", nodes.generate_advice_branches),
        ("generate_scheduler_candidates", nodes.generate_scheduler_candidates),
        ("replay_candidates", nodes.replay_candidates),
        ("compare_candidates", nodes.compare_candidates),
        ("persist_memory", nodes.persist_memory),
    ]
    for step_name, step in steps:
        try:
            state.update(step(state))
        except Exception as exc:
            nodes.record_offline_case(
                state,
                status="failed",
                failed_stage=step_name,
                error=exc,
            )
            raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
