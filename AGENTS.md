# AGENTS

## Environment

- All development, test, and verification commands for this repository must use the `conda` environment named `agent`.
- Use `/Users/lcjd/miniconda3/envs/agent/bin/python` as the Python interpreter for repository commands.
- Use `/Users/lcjd/miniconda3/envs/agent/bin/python -m <module>` for Python-based tooling such as `pytest`.
- Do not rely on bare `conda run -n agent python`, because it resolves to the wrong interpreter in this environment.
- If an interactive shell is required, activate `agent` and verify that `python --version` reports the environment interpreter before running repository commands.
