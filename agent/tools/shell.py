"""Shell tools with cooperative cancellation support."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Callable


CancelCheck = Callable[[], bool]


def run_shell_command(
    workspace_path: Path,
    command: str,
    is_cancelled: CancelCheck | None = None,
) -> dict[str, object]:
    process = subprocess.Popen(
        command,
        cwd=workspace_path,
        shell=True,
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
            time.sleep(0.05)
        stdout, stderr = process.communicate()
        return {
            "stdout": stdout,
            "stderr": stderr,
            "artifacts": {
                "command": command,
                "returncode": process.returncode,
                "cancelled": False,
            },
        }
    finally:
        if process.poll() is None:
            process.kill()
