from __future__ import annotations

from agent.commands.base import SlashCommand


def cancel_command(repl, argument: str) -> ReplResult:
    return repl.control_commands.cancel_active_work()


def approve_command(repl, argument: str) -> ReplResult:
    return repl.control_commands.resolve_pending_approval(True)


def deny_command(repl, argument: str) -> ReplResult:
    return repl.control_commands.resolve_pending_approval(False)


COMMANDS = [
    SlashCommand("/cancel", "Cancel the current task or pending approval.", cancel_command),
    SlashCommand("/approve", "Approve the current pending action.", approve_command),
    SlashCommand("/deny", "Deny the current pending action.", deny_command),
]
