import argparse
from pathlib import Path

from offline.graph.workflow import compile_workflow


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
        workflow = compile_workflow()
        workflow.invoke(
            {
                "trace_run_path": args.trace_run,
                "memory_path": args.memory,
                "replay_output": args.replay_output,
                "analyzer_config_path": args.analyzer_config,
                "max_candidates": args.max_candidates,
            }
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
