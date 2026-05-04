import argparse
from pathlib import Path

from scheduler_sim.config.loader import load_scenario_bundle
from scheduler_sim.trace.writer import TraceWriter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scheduler-sim")
    parser.add_argument("--scenario")
    parser.add_argument("--trace-output")
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv == ["--help"]:
        return 0

    args = build_parser().parse_args(argv)
    bundle = load_scenario_bundle(args.scenario)

    writer = TraceWriter(output_dir=Path(args.trace_output))
    writer.write_experiment_meta({"scenario_name": bundle.scenario.metadata.name})
    return 0
