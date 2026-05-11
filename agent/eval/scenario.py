"""Evaluation scenario format and loader."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvalScenario:
    id: str
    name: str
    description: str
    tasks: list[str]
    workspace: str | None = None
    tags: list[str] = field(default_factory=list)


def load_scenario(path: str | Path) -> EvalScenario:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return EvalScenario(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        tasks=data["tasks"],
        workspace=data.get("workspace"),
        tags=data.get("tags", []),
    )


BUILTIN_SCENARIOS: list[EvalScenario] = [
    EvalScenario(
        id="basic_inspect",
        name="Basic Workspace Inspection",
        description="Agent lists workspace files and checks git status.",
        tasks=["list files", "git status"],
        tags=["smoke"],
    ),
    EvalScenario(
        id="file_read",
        name="File Read",
        description="Agent reads README.md from the workspace.",
        tasks=["read README.md"],
        tags=["smoke", "filesystem"],
    ),
    EvalScenario(
        id="memory_retention",
        name="Memory Retention",
        description="Runs workspace inspection twice to test memory retrieval on the second pass.",
        tasks=["list files", "git status", "list files"],
        tags=["memory"],
    ),
]


def get_builtin(scenario_id: str) -> EvalScenario | None:
    for scenario in BUILTIN_SCENARIOS:
        if scenario.id == scenario_id:
            return scenario
    return None


def resolve_scenario(id_or_path: str) -> EvalScenario | None:
    builtin = get_builtin(id_or_path)
    if builtin is not None:
        return builtin
    path = Path(id_or_path)
    if path.exists():
        return load_scenario(path)
    return None
