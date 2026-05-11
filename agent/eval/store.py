"""SQLite-backed evaluation results store."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agent.eval.metrics import EvalRunMetrics, TaskMetrics


class EvalStore:
    def __init__(self, db_path: str | Path = "data/eval.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS eval_runs (
                    run_id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    with_memory INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    tasks_total INTEGER NOT NULL,
                    tasks_completed INTEGER NOT NULL,
                    completion_rate REAL NOT NULL,
                    total_tool_failures INTEGER NOT NULL,
                    total_approval_prompts INTEGER NOT NULL,
                    total_memory_hits INTEGER NOT NULL,
                    total_memories_learned INTEGER NOT NULL,
                    total_duration_seconds REAL NOT NULL,
                    task_metrics_json TEXT NOT NULL
                )
                """
            )

    def save(self, run: EvalRunMetrics) -> None:
        task_json = json.dumps(
            [
                {
                    "task_input": t.task_input,
                    "completed": t.completed,
                    "steps_total": t.steps_total,
                    "steps_completed": t.steps_completed,
                    "tool_failures": t.tool_failures,
                    "approval_prompts": t.approval_prompts,
                    "memory_hits": t.memory_hits,
                    "memories_learned": t.memories_learned,
                    "duration_seconds": t.duration_seconds,
                }
                for t in run.task_metrics
            ]
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO eval_runs (
                    run_id, scenario_id, with_memory, started_at, finished_at,
                    tasks_total, tasks_completed, completion_rate,
                    total_tool_failures, total_approval_prompts,
                    total_memory_hits, total_memories_learned,
                    total_duration_seconds, task_metrics_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.scenario_id,
                    1 if run.with_memory else 0,
                    run.started_at,
                    run.finished_at,
                    run.tasks_total,
                    run.tasks_completed,
                    run.completion_rate,
                    run.total_tool_failures,
                    run.total_approval_prompts,
                    run.total_memory_hits,
                    run.total_memories_learned,
                    run.total_duration_seconds,
                    task_json,
                ),
            )

    def list(self, limit: int = 50) -> list[EvalRunMetrics]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM eval_runs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, run_id: str) -> EvalRunMetrics | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM eval_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def _from_row(self, row: sqlite3.Row) -> EvalRunMetrics:
        task_metrics = [
            TaskMetrics(
                task_input=t["task_input"],
                completed=bool(t["completed"]),
                steps_total=int(t["steps_total"]),
                steps_completed=int(t["steps_completed"]),
                tool_failures=int(t["tool_failures"]),
                approval_prompts=int(t["approval_prompts"]),
                memory_hits=int(t["memory_hits"]),
                memories_learned=int(t["memories_learned"]),
                duration_seconds=float(t["duration_seconds"]),
            )
            for t in json.loads(row["task_metrics_json"])
        ]
        return EvalRunMetrics(
            run_id=row["run_id"],
            scenario_id=row["scenario_id"],
            with_memory=bool(row["with_memory"]),
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            task_metrics=task_metrics,
        )
