"""Minimal agent loop for Phase 4."""

from __future__ import annotations

from dataclasses import dataclass

from agent.heartbeat import HeartbeatMonitor
from agent.memory import MemoryService
from agent.observer import Observer
from agent.planner import Plan, Planner, TaskRequest
from agent.reflector import ReflectionService
from agent.session import SessionState
from agent.tool_models import ApprovalRequest, ToolResult
from agent.tool_router import ToolRouter


@dataclass(frozen=True)
class LoopRunResult:
    paused_for_approval: bool = False
    completed: bool = False
    summary: str = ""


class AgentLoop:
    def __init__(self, tool_router: ToolRouter, memory_service: MemoryService | None = None):
        self.tool_router = tool_router
        self.planner = Planner()
        self.observer = Observer()
        self.heartbeat = HeartbeatMonitor()
        self.memory_service = memory_service or MemoryService()
        self.reflector = ReflectionService()

    def run_task(
        self,
        session: SessionState,
        task_input: str,
        on_plan,
        on_tool_result,
        on_approval,
        on_summary,
        on_state_change,
        on_heartbeat,
        on_memories_loaded,
        on_memories_learned,
    ) -> LoopRunResult:
        task = TaskRequest(
            input=task_input,
            mode=session.mode,
            workspace_path=session.workspace_path,
        )
        session.active_task = task.input
        session.current_task_id = task.id
        session.cancellation_requested = False

        on_state_change("loading_context")
        on_heartbeat(
            self.heartbeat.start(
                session.id,
                task.id,
                "loading_context",
                message="loading context",
            )
        )
        on_state_change("planning")
        on_heartbeat(
            self.heartbeat.beat(
                "planning",
                message="building plan",
                force_log=True,
            )
        )
        session.loaded_memories = self.memory_service.search(task.input, limit=5)
        if session.loaded_memories:
            self.memory_service.mark_used([memory.id for memory in session.loaded_memories])
            on_memories_loaded(session.loaded_memories)
        plan = self.planner.create_plan(
            task,
            session.workspace_context,
            last_active_path=session.references.last_active_path,
            last_shell_command=session.references.last_shell_command,
            last_test_command=session.references.last_test_command,
        )
        session.current_plan = plan
        on_plan(plan)

        for step in plan.steps:
            if step.status != "pending":
                continue
            if session.cancellation_requested:
                return self._cancel(plan, on_summary, on_state_change, on_heartbeat, step.title, step.tool_name)

            request = self.tool_router.create_request(
                tool_name=step.tool_name,
                args=step.args,
                reason=step.rationale,
                workspace_path=session.workspace_path,
                step_id=step.id,
            )
            step.risk_level = request.risk_level
            on_state_change("executing_tool")
            on_heartbeat(
                self.heartbeat.beat(
                    "executing_tool",
                    active_step_title=step.title,
                    active_tool=step.tool_name,
                    message=f"running {step.tool_name}",
                    force_log=True,
                )
            )
            routed = self.tool_router.route(request)

            if isinstance(routed, ApprovalRequest):
                step.status = "waiting_for_approval"
                plan.status = "waiting_for_approval"
                on_state_change("waiting_for_approval")
                on_heartbeat(
                    self.heartbeat.beat(
                        "waiting_for_approval",
                        active_step_title=step.title,
                        active_tool=step.tool_name,
                        message="waiting for approval",
                        force_log=True,
                    )
                )
                on_approval(routed)
                return LoopRunResult(paused_for_approval=True)

            step.status = "completed" if routed.status == "success" else ("cancelled" if routed.cancelled else "failed")
            on_state_change("observing")
            on_heartbeat(
                self.heartbeat.beat(
                    "observing",
                    active_step_title=step.title,
                    active_tool=step.tool_name,
                    message="observing tool result",
                    force_log=True,
                )
            )
            observation = self.observer.observe(routed)
            on_tool_result(routed)
            if session.cancellation_requested:
                return self._cancel(plan, on_summary, on_state_change, on_heartbeat, step.title, step.tool_name)
            if routed.cancelled:
                return self._cancel(plan, on_summary, on_state_change, on_heartbeat, step.title, step.tool_name)
            if not observation.success:
                plan.status = "failed"
                on_state_change("failed")
                on_heartbeat(
                    self.heartbeat.stop(
                        "failed",
                        active_step_title=step.title,
                        active_tool=step.tool_name,
                        message=observation.summary,
                    )
                )
                on_summary(observation.summary)
                return LoopRunResult(completed=False, summary=observation.summary)

        plan.status = "completed"
        session.learned_memories = []
        learned, _rejected = self.reflector.store_safe_proposals(
            memory_service=self.memory_service,
            task_id=task.id,
            task_input=task.input,
            plan=plan,
            workspace_context=session.workspace_context,
        )
        if learned:
            session.learned_memories = learned
            on_memories_learned(learned)
        on_state_change("completed")
        on_heartbeat(
            self.heartbeat.stop(
                "completed",
                message="task completed",
            )
        )
        summary = self._build_summary(plan)
        on_summary(summary)
        return LoopRunResult(completed=True, summary=summary)

    def resume_after_approval(
        self,
        session: SessionState,
        result: ToolResult,
        on_tool_result,
        on_summary,
        on_state_change,
        on_heartbeat,
        on_memories_learned,
    ) -> LoopRunResult:
        plan = session.current_plan
        if plan is None:
            on_state_change("idle")
            return LoopRunResult(summary="")
        if session.cancellation_requested:
            return self._cancel(plan, on_summary, on_state_change, on_heartbeat, None, result.tool_name)

        step = self._find_step(plan, result.input.get("__step_id"))
        if step:
            step.status = "completed" if result.status == "success" else "failed"

        on_state_change("observing")
        on_heartbeat(
            self.heartbeat.beat(
                "observing",
                active_step_title=step.title if step else None,
                active_tool=result.tool_name,
                message="observing approved result",
                force_log=True,
            )
        )
        observation = self.observer.observe(result)
        on_tool_result(result)
        if not observation.success:
            plan.status = "failed"
            on_state_change("failed")
            on_heartbeat(
                self.heartbeat.stop(
                    "failed",
                    active_step_title=step.title if step else None,
                    active_tool=result.tool_name,
                    message=observation.summary,
                )
            )
            on_summary(observation.summary)
            return LoopRunResult(completed=False, summary=observation.summary)

        for pending_step in plan.steps:
            if pending_step.status == "pending":
                if session.cancellation_requested:
                    return self._cancel(
                        plan,
                        on_summary,
                        on_state_change,
                        on_heartbeat,
                        pending_step.title,
                        pending_step.tool_name,
                    )
                request = self.tool_router.create_request(
                    tool_name=pending_step.tool_name,
                    args=pending_step.args,
                    reason=pending_step.rationale,
                    workspace_path=session.workspace_path,
                    step_id=pending_step.id,
                )
                pending_step.risk_level = request.risk_level
                on_state_change("executing_tool")
                on_heartbeat(
                    self.heartbeat.beat(
                        "executing_tool",
                        active_step_title=pending_step.title,
                        active_tool=pending_step.tool_name,
                        message=f"running {pending_step.tool_name}",
                        force_log=True,
                    )
                )
                routed = self.tool_router.route(request)
                if isinstance(routed, ApprovalRequest):
                    pending_step.status = "waiting_for_approval"
                    plan.status = "waiting_for_approval"
                    on_state_change("waiting_for_approval")
                    on_heartbeat(
                        self.heartbeat.beat(
                            "waiting_for_approval",
                            active_step_title=pending_step.title,
                            active_tool=pending_step.tool_name,
                            message="waiting for approval",
                            force_log=True,
                        )
                    )
                    session.pending_approval = routed
                    return LoopRunResult(paused_for_approval=True)

                pending_step.status = "completed" if routed.status == "success" else ("cancelled" if routed.cancelled else "failed")
                on_state_change("observing")
                on_heartbeat(
                    self.heartbeat.beat(
                        "observing",
                        active_step_title=pending_step.title,
                        active_tool=pending_step.tool_name,
                        message="observing tool result",
                        force_log=True,
                    )
                )
                observation = self.observer.observe(routed)
                on_tool_result(routed)
                if routed.cancelled:
                    return self._cancel(
                        plan,
                        on_summary,
                        on_state_change,
                        on_heartbeat,
                        pending_step.title,
                        pending_step.tool_name,
                    )
                if not observation.success:
                    plan.status = "failed"
                    on_state_change("failed")
                    on_heartbeat(
                        self.heartbeat.stop(
                            "failed",
                            active_step_title=pending_step.title,
                            active_tool=pending_step.tool_name,
                            message=observation.summary,
                        )
                    )
                    on_summary(observation.summary)
                    return LoopRunResult(completed=False, summary=observation.summary)

        plan.status = "completed"
        session.learned_memories = []
        learned, _rejected = self.reflector.store_safe_proposals(
            memory_service=self.memory_service,
            task_id=session.current_task_id or "",
            task_input=session.active_task or "",
            plan=plan,
            workspace_context=session.workspace_context,
        )
        if learned:
            session.learned_memories = learned
            on_memories_learned(learned)
        on_state_change("completed")
        on_heartbeat(
            self.heartbeat.stop(
                "completed",
                message="task completed",
            )
        )
        summary = self._build_summary(plan)
        on_summary(summary)
        return LoopRunResult(completed=True, summary=summary)

    def _find_step(self, plan: Plan, step_id: object) -> object:
        if not isinstance(step_id, str):
            return None
        for step in plan.steps:
            if step.id == step_id:
                return step
        return None

    def _build_summary(self, plan: Plan) -> str:
        completed = sum(1 for step in plan.steps if step.status == "completed")
        return f"Completed {completed}/{len(plan.steps)} planned step(s)."

    def _cancel(
        self,
        plan: Plan,
        on_summary,
        on_state_change,
        on_heartbeat,
        active_step_title: str | None,
        active_tool: str | None,
    ) -> LoopRunResult:
        plan.status = "cancelled"
        on_state_change("cancelled")
        on_heartbeat(
            self.heartbeat.stop(
                "cancelled",
                active_step_title=active_step_title,
                active_tool=active_tool,
                message="task cancelled",
            )
        )
        on_summary("Task cancelled.")
        return LoopRunResult(completed=False, summary="Task cancelled.")
