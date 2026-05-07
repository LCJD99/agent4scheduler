import json
import sqlite3
from pathlib import Path
from typing import Any

from offline.io import read_json, validate_trace_run


class TraceMemoryDB:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def ingest_trace_run(
        self, trace_run: str | Path, *, signature: dict[str, Any]
    ) -> str:
        trace_path = Path(trace_run)
        validate_trace_run(trace_path)
        meta = read_json(trace_path / "experiment_meta.json")
        trace_run_id = str(meta.get("trace_run_id") or trace_path.name)
        with self._connect() as connection:
            connection.execute(
                """
                insert or replace into trace_runs(
                    trace_run_id, trace_path, scenario_path, scene_complexity,
                    signature_json, summary_json
                ) values (?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_run_id,
                    str(trace_path),
                    str(meta.get("scenario_path", "")),
                    str(meta.get("scene_complexity", "")),
                    json.dumps(signature, sort_keys=True),
                    (trace_path / "trace_summary.json").read_text(encoding="utf-8"),
                ),
            )
        return trace_run_id

    def store_evolution_result(self, result: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                insert into evolution_results(trace_run_id, result_json)
                values (?, ?)
                """,
                (
                    result.get("trace_run_id", ""),
                    json.dumps(result, sort_keys=True),
                ),
            )

    def upsert_case(
        self,
        *,
        workload_signature: dict[str, Any],
        scheduler_version: str,
        trace_run: str,
        metrics: dict[str, Any],
        advice: list[dict[str, Any]],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                insert into workload_cases(
                    scheduler_version, trace_run, signature_json, metrics_json, advice_json
                ) values (?, ?, ?, ?, ?)
                """,
                (
                    scheduler_version,
                    trace_run,
                    json.dumps(workload_signature, sort_keys=True),
                    json.dumps(metrics, sort_keys=True),
                    json.dumps(advice, sort_keys=True),
                ),
            )

    def list_cases(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select scheduler_version, trace_run, signature_json, metrics_json, advice_json
                from workload_cases
                """
            ).fetchall()
        return [
            {
                "scheduler_version": row[0],
                "trace_run": row[1],
                "workload_signature": json.loads(row[2]),
                "metrics": json.loads(row[3]),
                "advice": json.loads(row[4]),
            }
            for row in rows
        ]

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                create table if not exists trace_runs(
                    trace_run_id text primary key,
                    trace_path text not null,
                    scenario_path text not null,
                    scene_complexity text not null,
                    signature_json text not null,
                    summary_json text not null
                )
                """
            )
            connection.execute(
                """
                create table if not exists workload_cases(
                    id integer primary key autoincrement,
                    scheduler_version text not null,
                    trace_run text not null,
                    signature_json text not null,
                    metrics_json text not null,
                    advice_json text not null
                )
                """
            )
            connection.execute(
                """
                create table if not exists evolution_results(
                    id integer primary key autoincrement,
                    trace_run_id text not null,
                    result_json text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)
