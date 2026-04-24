from __future__ import annotations

from agent.commands.base import SlashCommand


def model_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.model_commands.handle_command(argument)
    return ReplResult()


COMMANDS = [
    SlashCommand("/model", "Show or switch the current model.", model_command),
]
