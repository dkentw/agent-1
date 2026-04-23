"""Interactive CLI skeleton for Phase 1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TextIO

from agent.config import AgentConfig
from agent.heartbeat import HeartbeatEvent
from agent.loop import AgentLoop
from agent.logging import SessionLogger, log_session_started
from agent.memory import MemoryRecord, MemoryService
from agent.session import SessionState, create_session
from agent.style import Style, paint, supports_color
from agent.tool_models import AppliedEdit, ApprovalRequest, PendingEdit, ToolResult
from agent.tool_router import ToolRouter


HELP_COMMANDS = [
    ("/help", "Show this help."),
    ("/exit", "End the session."),
    ("/clear", "Clear visible conversation context."),
    ("/status", "Show workspace, session, mode, and loop state."),
    ("/plan", "Show the current task plan."),
    ("/memory", "Show loaded memories or search stored memories."),
    ("/feedback", "Apply good or bad feedback to current task memories."),
    ("/permissions", "Show the current approval policy."),
    ("/approve", "Approve the current pending action."),
    ("/deny", "Deny the current pending action."),
    ("/diff", "Show the current pending or last applied diff."),
    ("/undo", "Undo the last agent-applied edit."),
    ("/logs", "Show the current session log path."),
]


@dataclass(frozen=True)
class ReplResult:
    should_exit: bool = False


class Repl:
    def __init__(
        self,
        config: AgentConfig,
        session: SessionState | None = None,
        logger: SessionLogger | None = None,
        output: TextIO | None = None,
        color: bool | None = None,
    ):
        self.config = config
        self.session = session or create_session()
        self.logger = logger or SessionLogger(self.session.log_path)
        self.output = output
        self.color = supports_color() if color is None else color
        self.memory_service = MemoryService(self.session.workspace_path / "data" / "memory.sqlite")
        self.tool_router = ToolRouter(config)
        self.agent_loop = AgentLoop(self.tool_router, self.memory_service)
        log_session_started(self.logger, self.session)

    def write(self, message: str = "") -> None:
        if self.output is None:
            print(message)
        else:
            print(message, file=self.output)

    def print_banner(self) -> None:
        title = paint("Self-Learning Agent", Style.bold, Style.cyan, enabled=self.color)
        workspace = paint(self.session.workspace_name, Style.green, enabled=self.color)
        hint = paint("Type /help for commands.", Style.gray, enabled=self.color)
        self.write(title)
        self.write(f"workspace {workspace}")
        if self.session.workspace_context and self.session.workspace_context.package_manager:
            package = paint(
                self.session.workspace_context.package_manager,
                Style.magenta,
                enabled=self.color,
            )
            self.write(f"package   {package}")
        self.write(hint)

    def handle_line(self, line: str) -> ReplResult:
        stripped = line.strip()
        if not stripped:
            return ReplResult()

        self.session.append_turn("user", stripped)
        self.logger.write(
            "user_input",
            {
                "session_id": self.session.id,
                "input": stripped,
            },
        )

        if stripped.startswith("/"):
            return self.handle_slash_command(stripped)

        self.logger.write(
            "task_received",
            {
                "session_id": self.session.id,
                "task": stripped,
                "loop_state": self.session.loop_state,
            },
        )
        self.write(paint("task", Style.cyan, enabled=self.color) + " received.")
        self.agent_loop.run_task(
            session=self.session,
            task_input=stripped,
            on_plan=self.render_plan,
            on_tool_result=self.handle_tool_result,
            on_approval=self.prompt_approval,
            on_summary=self.render_summary,
            on_state_change=self.set_loop_state,
            on_heartbeat=self.handle_heartbeat,
            on_memories_loaded=self.handle_loaded_memories,
            on_memories_learned=self.handle_learned_memories,
        )
        return ReplResult()

    def handle_slash_command(self, command_line: str) -> ReplResult:
        command, _, rest = command_line.partition(" ")
        command = command.lower()
        argument = rest.strip()

        self.logger.write(
            "slash_command",
            {
                "session_id": self.session.id,
                "command": command,
                "argument": argument,
            },
        )

        if command == "/help":
            self.write_help()
            return ReplResult()

        if command == "/exit":
            self.write(paint("Session ended.", Style.gray, enabled=self.color))
            self.logger.write("session_ended", {"session_id": self.session.id})
            return ReplResult(should_exit=True)

        if command == "/clear":
            self.session.clear_visible_context()
            self.write(
                paint("cleared", Style.green, enabled=self.color)
                + " visible conversation context."
            )
            self.logger.write("context_cleared", {"session_id": self.session.id})
            return ReplResult()

        if command == "/status":
            self.write_status()
            return ReplResult()

        if command == "/plan":
            self.write_plan()
            return ReplResult()

        if command == "/memory":
            if argument.startswith("search "):
                self.write_memory_search(argument.removeprefix("search ").strip())
            else:
                self.write_loaded_memories()
            return ReplResult()

        if command == "/feedback":
            self.apply_feedback(argument)
            return ReplResult()

        if command == "/permissions":
            self.write_permissions()
            return ReplResult()

        if command == "/approve":
            return self.resolve_pending_approval(True)

        if command == "/deny":
            return self.resolve_pending_approval(False)

        if command == "/diff":
            self.write_diff()
            return ReplResult()

        if command == "/undo":
            return self.undo_last_edit()

        if command == "/logs":
            self.write(paint(str(self.session.log_path), Style.gray, enabled=self.color))
            return ReplResult()

        self.write(
            paint("Unknown command:", Style.yellow, enabled=self.color)
            + f" {command}. Type /help for commands."
        )
        return ReplResult()

    def write_help(self) -> None:
        self.write(paint("Commands", Style.bold, Style.cyan, enabled=self.color))
        for command, description in HELP_COMMANDS:
            styled_command = paint(command.ljust(8), Style.green, enabled=self.color)
            self.write(f"  {styled_command} {description}")

    def write_status(self) -> None:
        self.write(paint("Status", Style.bold, Style.cyan, enabled=self.color))
        self.write_status_row("session", self.session.id)
        self.write_status_row("prompt", self.session.prompt.strip())
        self.write_status_row("workspace", str(self.session.workspace_path))
        self.write_status_row("mode", self.session.mode)
        self.write_status_row("loop", self.session.loop_state)
        self.write_status_row("task", self.session.active_task or "none")
        self.write_status_row("log", str(self.session.log_path))
        self.write_status_row("credential", self.config.permissions.credential_access)
        self.write_status_row("risk", self.config.security.unknown_risk)
        self.write_workspace_status()
        if self.session.pending_approval:
            self.write_status_row("approval", self.session.pending_approval.action_type)
        if self.session.pending_edit:
            self.write_status_row("pending_edit", self.session.pending_edit.path)
        if self.session.last_applied_edit:
            self.write_status_row("last_edit", self.session.last_applied_edit.path)
        if self.session.current_plan:
            self.write_status_row("plan", self.session.current_plan.status)
        if self.session.loaded_memories:
            self.write_status_row("memories", str(len(self.session.loaded_memories)))
        if self.session.learned_memories:
            self.write_status_row("learned", str(len(self.session.learned_memories)))
        if self.session.latest_heartbeat:
            self.write_status_row("heartbeat", self.describe_heartbeat(self.session.latest_heartbeat))

    def write_workspace_status(self) -> None:
        workspace = self.session.workspace_context
        if workspace is None:
            return

        self.write_status_row("git", workspace.git.status_summary)
        if workspace.git.branch:
            self.write_status_row("branch", workspace.git.branch)
        if workspace.git.root:
            self.write_status_row("git_root", str(workspace.git.root))
        self.write_status_row("package", workspace.package_manager or "none")
        self.write_status_row("languages", ", ".join(workspace.languages) or "none")
        self.write_status_row("tests", ", ".join(workspace.test_commands) or "none")
        self.write_status_row("files", ", ".join(workspace.important_files) or "none")

    def write_status_row(self, label: str, value: str) -> None:
        styled_label = paint(label.rjust(10), Style.gray, enabled=self.color)
        self.write(f"  {styled_label}  {value}")

    def write_permissions(self) -> None:
        self.write(paint("Permissions", Style.bold, Style.cyan, enabled=self.color))
        self.write_status_row("shell", self.config.permissions.shell.default)
        self.write_status_row("fs.read", self.config.permissions.filesystem.read)
        self.write_status_row("fs.write", self.config.permissions.filesystem.write)
        self.write_status_row("fs.delete", self.config.permissions.filesystem.delete)
        self.write_status_row("network", self.config.permissions.network.default)
        self.write_status_row("high_priv", self.config.permissions.high_privilege)
        self.write_status_row("creds", self.config.permissions.credential_access)

    def write_plan(self) -> None:
        plan = self.session.current_plan
        if plan is None:
            self.write(paint("No active plan.", Style.gray, enabled=self.color))
            return
        self.render_plan(plan)

    def write_loaded_memories(self) -> None:
        if not self.session.loaded_memories:
            self.write(paint("No loaded memories.", Style.gray, enabled=self.color))
            return
        self.write(paint("Loaded memories", Style.bold, Style.cyan, enabled=self.color))
        for record in self.session.loaded_memories:
            self.write(f"  {paint(record.id, Style.green, enabled=self.color)} {record.summary}")

    def write_memory_search(self, query: str) -> None:
        if not query:
            self.write(paint("Usage: /memory search <query>", Style.gray, enabled=self.color))
            return
        records = self.memory_service.search(query, limit=10)
        if not records:
            self.write(paint("No memories found.", Style.gray, enabled=self.color))
            return
        self.write(paint("Memory search", Style.bold, Style.cyan, enabled=self.color))
        for record in records:
            self.write(f"  {paint(record.id, Style.green, enabled=self.color)} {record.summary}")

    def render_plan(self, plan) -> None:
        self.write(paint("Plan", Style.bold, Style.cyan, enabled=self.color))
        self.write_status_row("status", plan.status)
        for index, step in enumerate(plan.steps, start=1):
            title = paint(f"{index}. {step.title}", Style.green, enabled=self.color)
            self.write(f"  {title}")
            self.write_status_row("tool", step.tool_name)
            self.write_status_row("step", step.status)
            self.write_status_row("why", step.rationale)

    def render_summary(self, summary: str) -> None:
        self.write(paint("Summary", Style.bold, Style.cyan, enabled=self.color))
        self.write(summary)

    def set_loop_state(self, state: str) -> None:
        self.session.loop_state = state
        self.logger.write(
            "loop_state_changed",
            {
                "session_id": self.session.id,
                "state": state,
            },
        )

    def handle_heartbeat(self, event: HeartbeatEvent) -> None:
        self.session.latest_heartbeat = event
        self.write(
            paint("heartbeat", Style.gray, enabled=self.color)
            + " "
            + self.describe_heartbeat(event)
        )
        if event.log_to_file:
            self.logger.write(
                "heartbeat",
                {
                    "session_id": event.session_id,
                    "task_id": event.task_id,
                    "loop_state": event.loop_state,
                    "active_step_title": event.active_step_title,
                    "active_tool": event.active_tool,
                    "elapsed_ms": event.elapsed_ms,
                    "cancellable": event.cancellable,
                    "message": event.message,
                    "unhealthy": event.unhealthy,
                },
            )

    def describe_heartbeat(self, event: HeartbeatEvent) -> str:
        detail = event.active_step_title or event.active_tool or event.message or event.loop_state
        return f"{event.loop_state} {detail} {event.elapsed_ms}ms"

    def prompt_approval(self, approval: ApprovalRequest) -> None:
        self.session.pending_approval = approval
        if approval.action_type == "filesystem.write":
            self.session.pending_edit = PendingEdit(
                path=approval.command_or_path,
                diff=approval.preview_diff,
                previous_content=str(approval.tool_request.args.get("__previous_content", "")),
                new_content=str(approval.tool_request.args.get("content", "")),
                tool_request=approval.tool_request,
            )
        self.write(paint("Approval required", Style.yellow, Style.bold, enabled=self.color))
        self.write_status_row("action", approval.action_type)
        self.write_status_row("target", approval.command_or_path)
        self.write_status_row("risk", approval.risk_level)
        self.write_status_row("reason", approval.reason)
        self.write_status_row("effect", approval.expected_effect)
        self.write(
            paint("/approve", Style.green, enabled=self.color)
            + " or "
            + paint("/deny", Style.yellow, enabled=self.color)
        )
        if approval.preview_diff:
            self.write(paint("Preview diff", Style.bold, Style.cyan, enabled=self.color))
            self.write(approval.preview_diff.rstrip() or "(no visible diff)")
        self.logger.write(
            "approval_required",
            {
                "session_id": self.session.id,
                "approval_id": approval.id,
                "action_type": approval.action_type,
                "target": approval.command_or_path,
                "risk_level": approval.risk_level,
                "reason": approval.reason,
            },
        )

    def resolve_pending_approval(self, approved: bool) -> ReplResult:
        approval = self.session.pending_approval
        if approval is None:
            self.write(paint("No pending approval.", Style.gray, enabled=self.color))
            return ReplResult()

        self.logger.write(
            "approval_decision",
            {
                "session_id": self.session.id,
                "approval_id": approval.id,
                "decision": "approved" if approved else "denied",
                "action_type": approval.action_type,
                "target": approval.command_or_path,
                "risk_level": approval.risk_level,
            },
        )

        self.session.pending_approval = None
        if not approved:
            self.session.pending_edit = None
            self.write(paint("Denied.", Style.yellow, enabled=self.color))
            return ReplResult()

        result = self.tool_router.execute(approval.tool_request)
        self.capture_applied_edit(result)
        if self.session.current_plan is None:
            self.handle_tool_result(result)
            return ReplResult()

        self.agent_loop.resume_after_approval(
            session=self.session,
            result=result,
            on_tool_result=self.handle_tool_result,
            on_summary=self.render_summary,
            on_state_change=self.set_loop_state,
            on_heartbeat=self.handle_heartbeat,
            on_memories_learned=self.handle_learned_memories,
        )
        return ReplResult()

    def record_tool_result(self, result: ToolResult) -> None:
        self.session.recent_tool_results.append(result)
        self.logger.write(
            "tool_result",
            {
                "session_id": self.session.id,
                "tool_name": result.tool_name,
                "status": result.status,
                "risk_level": result.risk_level,
                "requires_approval": result.requires_approval,
                "artifacts": result.artifacts,
            },
        )

    def render_tool_result(self, result: ToolResult) -> None:
        self.write(
            paint(result.tool_name, Style.cyan, enabled=self.color)
            + " "
            + paint(result.status, Style.green if result.status == "success" else Style.yellow, enabled=self.color)
        )
        if result.stdout:
            self.write(result.stdout.rstrip())
        elif result.artifacts:
            self.write(str(result.artifacts))

    def handle_tool_result(self, result: ToolResult) -> None:
        self.record_tool_result(result)
        self.render_tool_result(result)

    def handle_loaded_memories(self, records: list[MemoryRecord]) -> None:
        if not records:
            return
        self.logger.write(
            "memories_loaded",
            {
                "session_id": self.session.id,
                "task_id": self.session.current_task_id,
                "memory_ids": [record.id for record in records],
            },
        )
        self.write(
            paint("memory", Style.magenta, enabled=self.color)
            + f" loaded {len(records)} relevant item(s)."
        )

    def handle_learned_memories(self, records: list[MemoryRecord]) -> None:
        if not records:
            return
        self.logger.write(
            "memories_learned",
            {
                "session_id": self.session.id,
                "task_id": self.session.current_task_id,
                "memory_ids": [record.id for record in records],
            },
        )
        self.write(
            paint("learned", Style.magenta, enabled=self.color)
            + f" stored {len(records)} safe memory item(s)."
        )

    def apply_feedback(self, argument: str) -> None:
        action, _, reason = argument.partition(" ")
        action = action.strip().lower()
        reason = reason.strip()
        if action not in {"good", "bad"}:
            self.write(paint("Usage: /feedback good|bad <reason>", Style.gray, enabled=self.color))
            return
        target_ids = [record.id for record in (self.session.learned_memories or self.session.loaded_memories)]
        if not target_ids:
            self.write(paint("No task memories available for feedback.", Style.gray, enabled=self.color))
            return
        updated = self.memory_service.apply_feedback(target_ids, positive=action == "good")
        self.logger.write(
            "feedback_applied",
            {
                "session_id": self.session.id,
                "task_id": self.session.current_task_id,
                "action": action,
                "reason": reason,
                "memory_ids": target_ids,
            },
        )
        self.write(
            paint("feedback", Style.cyan, enabled=self.color)
            + f" applied to {len(updated)} memory item(s)."
        )

    def capture_applied_edit(self, result: ToolResult) -> None:
        if result.tool_name != "filesystem.write":
            return
        diff = str(result.artifacts.get("diff", ""))
        path = str(result.artifacts.get("path", result.input.get("path", "")))
        previous_content = str(result.artifacts.get("previous_content", ""))
        new_content = str(result.artifacts.get("new_content", result.input.get("content", "")))
        self.session.last_applied_edit = AppliedEdit(
            path=path,
            diff=diff,
            previous_content=previous_content,
            new_content=new_content,
        )
        self.session.pending_edit = None

    def write_diff(self) -> None:
        if self.session.pending_edit:
            self.write(paint("Pending diff", Style.bold, Style.cyan, enabled=self.color))
            self.write(self.session.pending_edit.diff.rstrip() or "(no visible diff)")
            return
        if self.session.last_applied_edit:
            self.write(paint("Last applied diff", Style.bold, Style.cyan, enabled=self.color))
            self.write(self.session.last_applied_edit.diff.rstrip() or "(no visible diff)")
            return
        self.write(paint("No diff available.", Style.gray, enabled=self.color))

    def undo_last_edit(self) -> ReplResult:
        edit = self.session.last_applied_edit
        if edit is None:
            self.write(paint("No applied edit to undo.", Style.gray, enabled=self.color))
            return ReplResult()

        path = Path(edit.path)
        if not path.is_absolute():
            path = self.session.workspace_path / path
        path.write_text(edit.previous_content, encoding="utf-8")
        self.logger.write(
            "edit_undone",
            {
                "session_id": self.session.id,
                "path": edit.path,
            },
        )
        self.write(paint("Undo applied.", Style.green, enabled=self.color))
        self.session.last_applied_edit = None
        return ReplResult()


def run_repl(
    config: AgentConfig,
    input_func: Callable[[str], str] = input,
    output: TextIO | None = None,
    color: bool | None = None,
) -> int:
    repl = Repl(config=config, output=output, color=color)
    repl.print_banner()

    while True:
        try:
            line = input_func(repl.session.styled_prompt(repl.color))
        except EOFError:
            repl.logger.write("session_ended", {"session_id": repl.session.id})
            return 0
        except KeyboardInterrupt:
            repl.write()
            repl.write(
                paint("Interrupted.", Style.yellow, enabled=repl.color)
                + " Type /exit to quit or continue with another prompt."
            )
            repl.logger.write("keyboard_interrupt", {"session_id": repl.session.id})
            continue

        result = repl.handle_line(line)
        if result.should_exit:
            return 0
