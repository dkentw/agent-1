from __future__ import annotations

from agent.commands.base import SlashCommand


def diff_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.edit_commands.write_diff()
    return ReplResult()


def undo_command(repl, argument: str) -> ReplResult:
    return repl.edit_commands.undo_last_edit()


COMMANDS = [
    SlashCommand("/diff", "Show the current pending or last applied diff.", diff_command),
    SlashCommand("/undo", "Undo the last agent-applied edit.", undo_command),
]
