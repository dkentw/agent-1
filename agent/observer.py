"""Observation helpers for tool execution."""

from __future__ import annotations

from dataclasses import dataclass

from agent.tool_models import ToolResult


@dataclass(frozen=True)
class Observation:
    success: bool
    summary: str


class Observer:
    def observe(self, result: ToolResult) -> Observation:
        if result.status == "success":
            if result.stdout:
                return Observation(True, f"{result.tool_name} returned output.")
            return Observation(True, f"{result.tool_name} completed.")
        return Observation(False, f"{result.tool_name} failed: {result.stderr or 'unknown error'}")

