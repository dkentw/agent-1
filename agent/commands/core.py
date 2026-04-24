from __future__ import annotations

from agent.commands.base import SlashCommand
from agent.style import Style, paint


def help_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.core_commands.write_help()
    return ReplResult()


def exit_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.write(paint("Session ended.", Style.gray, enabled=repl.color))
    repl.logger.write("session_ended", {"session_id": repl.session.id})
    return ReplResult(should_exit=True)


def clear_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.core_commands.clear_context()
    return ReplResult()


def setup_pin_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.model_commands.start_pin_setup()
    return ReplResult()


def logs_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.core_commands.write_logs_path()
    return ReplResult()


COMMANDS = [
    SlashCommand("/help", "Show this help.", help_command),
    SlashCommand("/exit", "End the session.", exit_command),
    SlashCommand("/clear", "Clear visible conversation context.", clear_command),
    SlashCommand("/setup-pin", "Create the global credential PIN.", setup_pin_command),
    SlashCommand("/logs", "Show the current session log path.", logs_command),
]
