"""Non-interactive evaluation runner for agent scenarios."""

from __future__ import annotations

import tempfile
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Generator

from agent.config import AgentConfig
from agent.eval.fixtures import BASIC_FILES, temp_workspace
from agent.eval.metrics import EvalRunMetrics, TaskMetrics
from agent.eval.scenario import EvalScenario
from agent.loop import AgentLoop
from agent.memory import MemoryService
from agent.session import create_session
from agent.tool_models import ApprovalRequest, ToolRequest, ToolResult
from agent.tool_router import ToolRouter


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class EvalToolRouter(ToolRouter):
    """ToolRouter that auto-approves all requests for non-interactive evaluation."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.approval_prompts: int = 0
        self.tool_failures: int = 0

    def reset(self) -> None:
        self.approval_prompts = 0
        self.tool_failures = 0

    def route(self, request: ToolRequest) -> ToolResult:
        try:
            result_or_approval = super().route(request)
        except Exception as exc:
            self.tool_failures += 1
            return self._error_result(request, str(exc))

        if isinstance(result_or_approval, ApprovalRequest):
            self.approval_prompts += 1
            try:
                result = self.execute(request)
            except Exception as exc:
                self.tool_failures += 1
                return self._error_result(request, str(exc))
        else:
            result = result_or_approval

        if result.status == "error":
            self.tool_failures += 1
        return result

    def _error_result(self, request: ToolRequest, message: str) -> ToolResult:
        now = _utc_now_iso()
        return ToolResult(
            tool_name=request.tool_name,
            input=dict(request.args),
            status="error",
            stdout="",
            stderr=message,
            artifacts={},
            started_at=now,
            finished_at=now,
            risk_level=request.risk_level,
            requires_approval=False,
        )


class EvalRunner:
    def __init__(self, config: AgentConfig, workspace_path: Path | None = None):
        self.config = config
        self.workspace_path = workspace_path

    def run(self, scenario: EvalScenario, with_memory: bool = True) -> EvalRunMetrics:
        run = EvalRunMetrics.new(scenario_id=scenario.id, with_memory=with_memory)
        with self._workspace_ctx(scenario) as workspace:
            with self._memory_ctx(workspace, with_memory) as memory_service:
                self._execute_tasks(run, scenario, workspace, memory_service)
        run.finished_at = _utc_now_iso()
        return run

    @contextmanager
    def _workspace_ctx(self, scenario: EvalScenario) -> Generator[Path, None, None]:
        if scenario.workspace:
            yield Path(scenario.workspace)
        elif self.workspace_path:
            yield self.workspace_path
        else:
            with temp_workspace(BASIC_FILES) as workspace:
                yield workspace

    @contextmanager
    def _memory_ctx(self, workspace: Path, with_memory: bool) -> Generator[MemoryService, None, None]:
        if with_memory:
            yield MemoryService(workspace / "data" / "eval_memory.sqlite")
        else:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
                yield MemoryService(Path(tmpdir) / "eval_memory.sqlite")

    def _execute_tasks(
        self,
        run: EvalRunMetrics,
        scenario: EvalScenario,
        workspace: Path,
        memory_service: MemoryService,
    ) -> None:
        router = EvalToolRouter(self.config)
        loop = AgentLoop(router, memory_service)

        for task_input in scenario.tasks:
            router.reset()
            memory_hits: list = []
            memories_learned: list = []
            plan_ref: list = []

            session = create_session(
                workspace_path=workspace,
                mode="eval",
                model_provider=self.config.models.provider,
                selected_model=self.config.models.default,
            )

            t0 = time.monotonic()
            result = loop.run_task(
                session=session,
                task_input=task_input,
                on_plan=plan_ref.append,
                on_tool_result=lambda _r: None,
                on_approval=lambda _a: None,
                on_summary=lambda _s: None,
                on_state_change=lambda _s: None,
                on_heartbeat=lambda _e: None,
                on_memories_loaded=memory_hits.extend,
                on_memories_learned=memories_learned.extend,
            )
            duration = time.monotonic() - t0

            plan = plan_ref[0] if plan_ref else None
            steps_total = len(plan.steps) if plan else 0
            steps_completed = (
                sum(1 for s in plan.steps if s.status == "completed") if plan else 0
            )

            run.task_metrics.append(
                TaskMetrics(
                    task_input=task_input,
                    completed=result.completed,
                    steps_total=steps_total,
                    steps_completed=steps_completed,
                    tool_failures=router.tool_failures,
                    approval_prompts=router.approval_prompts,
                    memory_hits=len(memory_hits),
                    memories_learned=len(memories_learned),
                    duration_seconds=round(duration, 3),
                )
            )
