"""Repeatable test workspace fixtures for evaluation runs."""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


BASIC_FILES: dict[str, str] = {
    "README.md": "# Eval Fixture\n\nThis is a test workspace for evaluation.\n",
    "hello.py": 'print("hello")\n',
    "tests/test_hello.py": "def test_hello():\n    assert True\n",
}


@contextmanager
def temp_workspace(files: dict[str, str] | None = None) -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory(prefix="agent_eval_", ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        for rel_path, content in (files or BASIC_FILES).items():
            target = workspace / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        yield workspace
