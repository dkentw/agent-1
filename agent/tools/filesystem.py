"""Read-only filesystem tools."""

from __future__ import annotations

from difflib import unified_diff
from pathlib import Path


def read_file(workspace_path: Path, path: str) -> dict[str, object]:
    target = _resolve_workspace_path(workspace_path, path)
    return {
        "stdout": target.read_text(encoding="utf-8"),
        "stderr": "",
        "artifacts": {
            "path": str(target),
            "size": target.stat().st_size,
        },
    }


def list_directory(workspace_path: Path, path: str = ".") -> dict[str, object]:
    target = _resolve_workspace_path(workspace_path, path)
    entries = sorted(item.name for item in target.iterdir())
    return {
        "stdout": "\n".join(entries),
        "stderr": "",
        "artifacts": {
            "path": str(target),
            "entries": entries,
        },
    }


def stat_path(workspace_path: Path, path: str) -> dict[str, object]:
    target = _resolve_workspace_path(workspace_path, path)
    stat = target.stat()
    return {
        "stdout": "",
        "stderr": "",
        "artifacts": {
            "path": str(target),
            "is_dir": target.is_dir(),
            "size": stat.st_size,
        },
    }


def preview_write(workspace_path: Path, path: str, content: str) -> dict[str, object]:
    target = _resolve_workspace_path(workspace_path, path)
    previous_content = target.read_text(encoding="utf-8") if target.exists() else ""
    diff = _build_diff(path, previous_content, content)
    return {
        "stdout": diff,
        "stderr": "",
        "artifacts": {
            "path": str(target),
            "previous_content": previous_content,
            "new_content": content,
            "diff": diff,
        },
    }


def write_file(workspace_path: Path, path: str, content: str) -> dict[str, object]:
    preview = preview_write(workspace_path, path, content)
    target = _resolve_workspace_path(workspace_path, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {
        "stdout": "",
        "stderr": "",
        "artifacts": preview["artifacts"],
    }


def _build_diff(path: str, previous_content: str, new_content: str) -> str:
    before = previous_content.splitlines(keepends=True)
    after = new_content.splitlines(keepends=True)
    diff_lines = unified_diff(before, after, fromfile=f"a/{path}", tofile=f"b/{path}")
    return "".join(diff_lines)


def _resolve_workspace_path(workspace_path: Path, path: str) -> Path:
    candidate = (workspace_path / path).resolve()
    workspace_root = workspace_path.resolve()
    if candidate != workspace_root and workspace_root not in candidate.parents:
        raise PermissionError(f"path escapes workspace: {path}")
    return candidate
