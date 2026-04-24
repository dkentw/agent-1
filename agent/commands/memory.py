from __future__ import annotations

from agent.commands.base import SlashCommand


def memory_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    if argument.startswith("search "):
        repl.memory_commands.write_memory_search(argument.removeprefix("search ").strip())
    else:
        repl.memory_commands.write_loaded_memories()
    return ReplResult()


def feedback_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.memory_commands.apply_feedback(argument)
    return ReplResult()


def history_command(repl, argument: str) -> ReplResult:
    from agent.repl import ReplResult

    repl.memory_commands.write_history()
    return ReplResult()


COMMANDS = [
    SlashCommand("/memory", "Show loaded memories or search stored memories.", memory_command),
    SlashCommand("/feedback", "Apply good or bad feedback to current task memories.", feedback_command),
    SlashCommand("/history", "Show recent input history.", history_command),
]
