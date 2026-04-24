"""Interactive CLI skeleton for Phase 1."""

from __future__ import annotations

from dataclasses import dataclass
import getpass
from pathlib import Path
from typing import Callable, TextIO

from agent.commands import SlashCommandRegistry
from agent.commands.services import (
    CoreCommandService,
    ControlCommandService,
    EditCommandService,
    FollowUpService,
    MemoryCommandService,
    ModelCommandService,
    SecurePromptService,
    StatusCommandService,
    TaskInteractionService,
)
from agent.config import AgentConfig
from agent.credentials import CredentialStore
from agent.heartbeat import HeartbeatEvent
from agent.llm import ModelService
from agent.loop import AgentLoop
from agent.logging import SessionLogger, log_session_started
from agent.memory import MemoryRecord, MemoryService
from agent.models import ModelRegistry
from agent.rendering import Renderer
from agent.session import SessionState, create_session
from agent.style import Style, paint, supports_color
from agent.tool_models import AppliedEdit, ApprovalRequest, PendingEdit, ToolResult
from agent.tool_router import ToolRouter


@dataclass(frozen=True)
class ReplResult:
    should_exit: bool = False


@dataclass
class SecurePromptState:
    mode: str
    provider: str
    secret_value: str = ""
    pin_value: str = ""


class Repl:
    def __init__(
        self,
        config: AgentConfig,
        session: SessionState | None = None,
        logger: SessionLogger | None = None,
        output: TextIO | None = None,
        color: bool | None = None,
        model_override: str | None = None,
    ):
        self.config = config
        self.model_registry = ModelRegistry()
        selected_model = model_override or config.models.default
        self.session = session or create_session(
            model_provider=config.models.provider,
            selected_model=selected_model,
        )
        self.logger = logger or SessionLogger(self.session.log_path)
        self.output = output
        self.color = supports_color() if color is None else color
        self.renderer = Renderer(color=self.color)
        self.memory_service = MemoryService(self.session.workspace_path / "data" / "memory.sqlite")
        self.credential_store = CredentialStore(self.session.workspace_path / "data" / "credentials.sqlite")
        self.model_service = ModelService(config)
        self.tool_router = ToolRouter(config)
        self.agent_loop = AgentLoop(self.tool_router, self.memory_service)
        self.command_registry = SlashCommandRegistry()
        self.core_commands = CoreCommandService(self)
        self.status_commands = StatusCommandService(self)
        self.memory_commands = MemoryCommandService(self)
        self.model_commands = ModelCommandService(self)
        self.control_commands = ControlCommandService(self)
        self.edit_commands = EditCommandService(self)
        self.secure_prompt_service = SecurePromptService(self)
        self.follow_up_service = FollowUpService(self)
        self.task_interaction = TaskInteractionService(self)
        self.unlocked_model_api_key: str | None = None
        self.secure_prompt_state: SecurePromptState | None = None
        self._last_heartbeat_line: str | None = None
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
        model = paint(self.session.selected_model, Style.magenta, enabled=self.color)
        self.write(f"model     {model}")
        self.write(hint)

    def handle_line(self, line: str) -> ReplResult:
        stripped = line.strip()
        if not stripped:
            return ReplResult()

        if self.secure_prompt_state is not None:
            return self.secure_prompt_service.handle_input(stripped)

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

        follow_up = self.follow_up_service.resolve(stripped)
        if follow_up is not None:
            return follow_up

        return self.task_interaction.start_task(stripped)

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

        registered = self.command_registry.find(command)
        if registered is not None:
            return registered.handler(self, argument)

        self.write(
            paint("Unknown command:", Style.yellow, enabled=self.color)
            + f" {command}."
            + (
                f" Did you mean {self.suggest_command(command)}?"
                if self.suggest_command(command)
                else " Type /help for commands."
            )
        )
        return ReplResult()

    def render_plan(self, plan) -> None:
        self.task_interaction.render_plan(plan)

    def render_summary(self, summary: str) -> None:
        self.task_interaction.render_summary(summary)

    def set_loop_state(self, state: str) -> None:
        self.task_interaction.set_loop_state(state)

    def handle_heartbeat(self, event: HeartbeatEvent) -> None:
        self.task_interaction.handle_heartbeat(event)

    def describe_heartbeat(self, event: HeartbeatEvent) -> str:
        state = self.renderer.heartbeat_state_label(event.loop_state)
        detail = self.renderer.describe_heartbeat(event)
        return f"{state} {detail}".strip()

    def prompt_approval(self, approval: ApprovalRequest) -> None:
        self.task_interaction.prompt_approval(approval)

    def record_tool_result(self, result: ToolResult) -> None:
        self.task_interaction.record_tool_result(result)

    def render_tool_result(self, result: ToolResult) -> None:
        self.task_interaction.render_tool_result(result)

    def handle_tool_result(self, result: ToolResult) -> None:
        self.task_interaction.handle_tool_result(result)

    def handle_loaded_memories(self, records: list[MemoryRecord]) -> None:
        self.task_interaction.handle_loaded_memories(records)

    def handle_learned_memories(self, records: list[MemoryRecord]) -> None:
        self.task_interaction.handle_learned_memories(records)

    def suggest_command(self, command: str) -> str | None:
        return self.command_registry.suggest(command)

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


def run_repl(
    config: AgentConfig,
    input_func: Callable[[str], str] = input,
    output: TextIO | None = None,
    color: bool | None = None,
    model_override: str | None = None,
) -> int:
    repl = Repl(config=config, output=output, color=color, model_override=model_override)
    repl.print_banner()

    while True:
        try:
            if repl.secure_prompt_state is not None and input_func is input:
                line = getpass.getpass("")
            else:
                line = input_func(repl.session.styled_prompt(repl.color))
            while line.endswith("\\"):
                if repl.secure_prompt_state is not None and input_func is input:
                    continuation = getpass.getpass("")
                else:
                    continuation = input_func(paint("... ", Style.gray, enabled=repl.color))
                line = line[:-1] + "\n" + continuation
        except EOFError:
            repl.logger.write("session_ended", {"session_id": repl.session.id})
            return 0
        except KeyboardInterrupt:
            repl.write()
            repl.session.cancellation_requested = True
            repl.write(
                paint("Interrupted.", Style.yellow, enabled=repl.color)
                + " Cancellation requested. Type /exit to quit or continue with another prompt."
            )
            repl.logger.write(
                "keyboard_interrupt",
                {
                    "session_id": repl.session.id,
                    "cancellation_requested": repl.session.cancellation_requested,
                },
            )
            continue

        result = repl.handle_line(line)
        if result.should_exit:
            return 0
