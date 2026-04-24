from __future__ import annotations

from difflib import get_close_matches

from agent.commands.base import SlashCommand
from agent.commands.control import COMMANDS as CONTROL_COMMANDS
from agent.commands.core import COMMANDS as CORE_COMMANDS
from agent.commands.editing import COMMANDS as EDITING_COMMANDS
from agent.commands.memory import COMMANDS as MEMORY_COMMANDS
from agent.commands.model import COMMANDS as MODEL_COMMANDS
from agent.commands.status import COMMANDS as STATUS_COMMANDS


class SlashCommandRegistry:
    def __init__(self, commands: list[SlashCommand] | None = None):
        self._commands: dict[str, SlashCommand] = {}
        for command in commands or self.default_commands():
            self.register(command)

    @staticmethod
    def default_commands() -> list[SlashCommand]:
        return [
            *CORE_COMMANDS,
            *STATUS_COMMANDS,
            *MEMORY_COMMANDS,
            *MODEL_COMMANDS,
            *CONTROL_COMMANDS,
            *EDITING_COMMANDS,
        ]

    def register(self, command: SlashCommand) -> None:
        self._commands[command.name] = command

    def find(self, name: str) -> SlashCommand | None:
        return self._commands.get(name)

    def suggest(self, name: str) -> str | None:
        matches = get_close_matches(name, list(self._commands), n=1, cutoff=0.6)
        return matches[0] if matches else None

    def items(self) -> list[SlashCommand]:
        return [self._commands[name] for name in sorted(self._commands)]

