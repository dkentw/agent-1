from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from agent.repl import Repl, ReplResult


SlashHandler = Callable[["Repl", str], "ReplResult"]


@dataclass(frozen=True)
class SlashCommand:
    name: str
    description: str
    handler: SlashHandler

