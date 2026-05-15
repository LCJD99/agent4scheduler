#!/usr/bin/env bash
set -e

mkdir -p case

PYTHONPATH=src /home/dawnat9/miniconda3/envs/agent/bin/python -m scheduler_sim.app \
  --scenario configs/scenarios/home_eqa_scenario_001.yaml \
  --trace-output case/baseline

TRACE_RUN=$(find case/baseline -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)

PYTHONPATH=src /home/dawnat9/miniconda3/envs/agent/bin/python -m offline.cli evolve \
  --trace-run "$TRACE_RUN" \
  --memory case/offline.db \
  --replay-output case/replays \
  --analyzer-config configs/offline/trace_analyzer_openai.yaml \
  --max-candidates 1
