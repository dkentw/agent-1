"""Small ANSI styling helpers for the terminal UI."""

from __future__ import annotations

import os
import re
import sys


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class Style:
    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[2m"
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    blue = "\033[34m"
    magenta = "\033[35m"
    cyan = "\033[36m"
    gray = "\033[90m"


def supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


def paint(text: str, *styles: str, enabled: bool = True) -> str:
    if not enabled or not styles:
        return text
    return "".join(styles) + text + Style.reset


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)

