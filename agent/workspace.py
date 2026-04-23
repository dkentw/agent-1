"""Read-only workspace detection."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class GitContext:
    root: Path | None = None
    branch: str | None = None
    is_repo: bool = False
    has_changes: bool = False
    status_summary: str = "not a git repo"


@dataclass(frozen=True)
class WorkspaceContext:
    path: Path
    git: GitContext = field(default_factory=GitContext)
    languages: tuple[str, ...] = ()
    package_manager: str | None = None
    test_commands: tuple[str, ...] = ()
    important_files: tuple[str, ...] = ()


IMPORTANT_FILES = (
    "agent.yaml",
    "pyproject.toml",
    "package.json",
    "requirements.txt",
    "setup.py",
    "pytest.ini",
    "Cargo.toml",
    "go.mod",
    "README.md",
)


def detect_workspace(path: str | Path | None = None) -> WorkspaceContext:
    workspace_path = Path(path or Path.cwd()).resolve()
    important_files = _existing_files(workspace_path, IMPORTANT_FILES)
    package_manager = _detect_package_manager(workspace_path)
    languages = _detect_languages(workspace_path, important_files)
    test_commands = _detect_test_commands(workspace_path, package_manager, important_files)

    return WorkspaceContext(
        path=workspace_path,
        git=_detect_git(workspace_path),
        languages=languages,
        package_manager=package_manager,
        test_commands=test_commands,
        important_files=important_files,
    )


def _existing_files(workspace_path: Path, names: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(name for name in names if (workspace_path / name).exists())


def _detect_package_manager(workspace_path: Path) -> str | None:
    if (workspace_path / "uv.lock").exists():
        return "uv"
    if (workspace_path / "poetry.lock").exists():
        return "poetry"
    if (workspace_path / "pdm.lock").exists():
        return "pdm"
    if (workspace_path / "package-lock.json").exists():
        return "npm"
    if (workspace_path / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (workspace_path / "yarn.lock").exists():
        return "yarn"
    if (workspace_path / "Cargo.toml").exists():
        return "cargo"
    if (workspace_path / "go.mod").exists():
        return "go"
    if (workspace_path / "pyproject.toml").exists():
        return "python"
    if (workspace_path / "package.json").exists():
        return "npm"
    return None


def _detect_languages(
    workspace_path: Path,
    important_files: tuple[str, ...],
) -> tuple[str, ...]:
    languages: list[str] = []
    if {"pyproject.toml", "requirements.txt", "setup.py", "pytest.ini"} & set(important_files):
        languages.append("python")
    if "package.json" in important_files:
        languages.append("javascript")
        if _package_json_has_typescript(workspace_path / "package.json"):
            languages.append("typescript")
    if "Cargo.toml" in important_files:
        languages.append("rust")
    if "go.mod" in important_files:
        languages.append("go")
    return tuple(languages)


def _package_json_has_typescript(package_json_path: Path) -> bool:
    try:
        package_data = json.loads(package_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    dependencies = {
        **package_data.get("dependencies", {}),
        **package_data.get("devDependencies", {}),
    }
    return "typescript" in dependencies


def _detect_test_commands(
    workspace_path: Path,
    package_manager: str | None,
    important_files: tuple[str, ...],
) -> tuple[str, ...]:
    commands: list[str] = []

    if "pyproject.toml" in important_files:
        if package_manager == "uv":
            commands.append("uv run --extra dev pytest")
        else:
            commands.append("pytest")

    if "package.json" in important_files:
        test_script = _package_json_test_script(workspace_path / "package.json")
        if test_script:
            if package_manager == "pnpm":
                commands.append("pnpm test")
            elif package_manager == "yarn":
                commands.append("yarn test")
            else:
                commands.append("npm test")

    if "Cargo.toml" in important_files:
        commands.append("cargo test")
    if "go.mod" in important_files:
        commands.append("go test ./...")

    return tuple(commands)


def _package_json_test_script(package_json_path: Path) -> str | None:
    try:
        package_data = json.loads(package_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    script = package_data.get("scripts", {}).get("test")
    return script if isinstance(script, str) and script else None


def _detect_git(workspace_path: Path) -> GitContext:
    root_result = _run_git(workspace_path, "rev-parse", "--show-toplevel")
    if root_result.returncode != 0:
        return GitContext()

    root_text = root_result.stdout.strip()
    root = Path(root_text).resolve() if root_text else None

    branch_result = _run_git(workspace_path, "branch", "--show-current")
    branch = branch_result.stdout.strip() or None

    status_result = _run_git(workspace_path, "status", "--short")
    status_lines = [line for line in status_result.stdout.splitlines() if line.strip()]
    has_changes = bool(status_lines)
    if has_changes:
        status_summary = f"{len(status_lines)} changed file(s)"
    else:
        status_summary = "clean"

    return GitContext(
        root=root,
        branch=branch,
        is_repo=True,
        has_changes=has_changes,
        status_summary=status_summary,
    )


def _run_git(workspace_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=workspace_path,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(["git", *args], 1, "", "")

