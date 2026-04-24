from __future__ import annotations

from agent.commands.base import SlashCommand


def status_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.status_commands.write_status()
    return ReplResult()


def plan_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.status_commands.write_plan()
    return ReplResult()


def permissions_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.status_commands.write_permissions()
    return ReplResult()


COMMANDS = [
    SlashCommand("/status", "Show workspace, session, mode, and loop state.", status_command),
    SlashCommand("/plan", "Show the current task plan.", plan_command),
    SlashCommand("/permissions", "Show the current approval policy.", permissions_command),
]
