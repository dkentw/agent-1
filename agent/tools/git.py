"""Read-only Git tools."""

from __future__ import annotations

import subprocess
from pathlib import Path


def git_status(workspace_path: Path) -> dict[str, object]:
    result = _run_git(workspace_path, "status", "--short", "--branch")
    return {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "artifacts": {
            "returncode": result.returncode,
        },
    }


def git_diff(workspace_path: Path) -> dict[str, object]:
    result = _run_git(workspace_path, "diff", "--")
    return {
        "stdout": result.stdout,
        "stderr": result.stderr.strip(),
        "artifacts": {
            "returncode": result.returncode,
        },
    }


def _run_git(workspace_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=workspace_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

