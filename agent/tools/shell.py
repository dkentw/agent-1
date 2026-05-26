"""Shell tools with cooperative cancellation support."""

from __future__ import annotations

import subprocess
import time
import shlex
from pathlib import Path
from typing import Callable


CancelCheck = Callable[[], bool]


def run_shell_command(
    workspace_path: Path,
    command: str,
    is_cancelled: CancelCheck | None = None,
    timeout_seconds: int = 30,
    use_shell: bool = False,
) -> dict[str, object]:
    started = time.monotonic()
    args: str | list[str]
    if use_shell:
        args = command
    else:
        args = _split_command(command)

    process = subprocess.Popen(
        args,
        cwd=workspace_path,
        shell=use_shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        while process.poll() is None:
            if is_cancelled and is_cancelled():
                process.terminate()
                try:
                    stdout, stderr = process.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                return {
                    "stdout": stdout,
                    "stderr": stderr,
                    "artifacts": {
                        "command": command,
                        "returncode": process.returncode,
                        "cancelled": True,
                    },
                }
            if time.monotonic() - started >= timeout_seconds:
                process.terminate()
                try:
                    stdout, stderr = process.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                return {
                    "stdout": stdout,
                    "stderr": stderr,
                    "artifacts": {
                        "command": command,
                        "returncode": process.returncode,
                        "cancelled": False,
                        "timed_out": True,
                        "timeout_seconds": timeout_seconds,
                    },
                }
            time.sleep(0.05)
        stdout, stderr = process.communicate()
        return {
            "stdout": stdout,
            "stderr": stderr,
            "artifacts": {
                "command": command,
                "returncode": process.returncode,
                "cancelled": False,
                "timed_out": False,
                "timeout_seconds": timeout_seconds,
                "use_shell": use_shell,
            },
        }
    finally:
        if process.poll() is None:
            process.kill()


def _split_command(command: str) -> list[str]:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"invalid shell command syntax: {exc}") from exc
    if not argv:
        raise ValueError("shell command must not be empty")
    return argv
