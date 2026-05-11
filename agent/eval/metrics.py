"""Evaluation run metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class TaskMetrics:
    task_input: str
    completed: bool
    steps_total: int
    steps_completed: int
    tool_failures: int
    approval_prompts: int
    memory_hits: int
    memories_learned: int
    duration_seconds: float


@dataclass
class EvalRunMetrics:
    run_id: str
    scenario_id: str
    with_memory: bool
    started_at: str
    finished_at: str
    task_metrics: list[TaskMetrics] = field(default_factory=list)

    @classmethod
    def new(cls, scenario_id: str, with_memory: bool) -> "EvalRunMetrics":
        now = _utc_now_iso()
        return cls(
            run_id=f"eval_{uuid4().hex[:12]}",
            scenario_id=scenario_id,
            with_memory=with_memory,
            started_at=now,
            finished_at=now,
        )

    @property
    def tasks_total(self) -> int:
        return len(self.task_metrics)

    @property
    def tasks_completed(self) -> int:
        return sum(1 for t in self.task_metrics if t.completed)

    @property
    def completion_rate(self) -> float:
        if not self.task_metrics:
            return 0.0
        return self.tasks_completed / self.tasks_total

    @property
    def total_tool_failures(self) -> int:
        return sum(t.tool_failures for t in self.task_metrics)

    @property
    def total_approval_prompts(self) -> int:
        return sum(t.approval_prompts for t in self.task_metrics)

    @property
    def total_memory_hits(self) -> int:
        return sum(t.memory_hits for t in self.task_metrics)

    @property
    def total_memories_learned(self) -> int:
        return sum(t.memories_learned for t in self.task_metrics)

    @property
    def total_duration_seconds(self) -> float:
        return sum(t.duration_seconds for t in self.task_metrics)
