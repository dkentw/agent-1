"""Minimal sensitive-data checks for memory writes."""

from __future__ import annotations

import re


SENSITIVE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
    re.compile(r"\b(?:sk|rk)-[A-Za-z0-9]{16,}\b"),
    re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*\S+"),
)


def contains_sensitive_data(*values: str) -> bool:
    for value in values:
        if not value:
            continue
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(value):
                return True
    return False
