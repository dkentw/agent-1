"""Local SQLite-backed memory service."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    type: str
    scope: str
    content: str
    summary: str
    source_task_id: str
    confidence: float
    reliability_score: float
    created_at: str
    updated_at: str
    use_count: int
    tags: tuple[str, ...]


class MemoryService:
    def __init__(self, db_path: str | Path = "data/memory.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_task_id TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    reliability_score REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    use_count INTEGER NOT NULL DEFAULT 0,
                    tags TEXT NOT NULL DEFAULT ''
                )
                """
            )

    def create(
        self,
        *,
        type: str,
        scope: str,
        content: str,
        summary: str,
        source_task_id: str = "",
        confidence: float = 0.5,
        reliability_score: float = 0.5,
        tags: tuple[str, ...] = (),
    ) -> MemoryRecord:
        now = utc_now_iso()
        record = MemoryRecord(
            id=f"mem_{uuid4().hex[:12]}",
            type=type,
            scope=scope,
            content=content,
            summary=summary,
            source_task_id=source_task_id,
            confidence=confidence,
            reliability_score=reliability_score,
            created_at=now,
            updated_at=now,
            use_count=0,
            tags=tags,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO memories (
                    id, type, scope, content, summary, source_task_id,
                    confidence, reliability_score, created_at, updated_at,
                    use_count, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.type,
                    record.scope,
                    record.content,
                    record.summary,
                    record.source_task_id,
                    record.confidence,
                    record.reliability_score,
                    record.created_at,
                    record.updated_at,
                    record.use_count,
                    ",".join(record.tags),
                ),
            )
        return record

    def create_or_update(
        self,
        *,
        type: str,
        scope: str,
        content: str,
        summary: str,
        source_task_id: str = "",
        confidence: float = 0.5,
        reliability_score: float = 0.5,
        tags: tuple[str, ...] = (),
    ) -> MemoryRecord:
        existing = self.find_by_summary(type=type, scope=scope, summary=summary)
        if existing is None:
            return self.create(
                type=type,
                scope=scope,
                content=content,
                summary=summary,
                source_task_id=source_task_id,
                confidence=confidence,
                reliability_score=reliability_score,
                tags=tags,
            )

        merged_tags = tuple(sorted(set(existing.tags) | set(tags)))
        now = utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE memories
                SET content = ?,
                    source_task_id = ?,
                    confidence = ?,
                    reliability_score = ?,
                    updated_at = ?,
                    tags = ?
                WHERE id = ?
                """,
                (
                    content,
                    source_task_id or existing.source_task_id,
                    max(existing.confidence, confidence),
                    max(existing.reliability_score, reliability_score),
                    now,
                    ",".join(merged_tags),
                    existing.id,
                ),
            )
        refreshed = self.get(existing.id)
        assert refreshed is not None
        return refreshed

    def list(self, limit: int = 50) -> list[MemoryRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM memories
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def search(self, query: str, limit: int = 10) -> list[MemoryRecord]:
        tokens = [token.lower() for token in query.replace('"', " ").split() if len(token) >= 2]
        if not tokens:
            tokens = [query.lower()]
        clauses = []
        parameters: list[object] = []
        for token in tokens:
            normalized = f"%{token}%"
            clauses.append(
                "(lower(content) LIKE ? OR lower(summary) LIKE ? OR lower(tags) LIKE ? OR lower(scope) LIKE ?)"
            )
            parameters.extend([normalized, normalized, normalized, normalized])
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM memories
                WHERE {" OR ".join(clauses)}
                ORDER BY use_count DESC, updated_at DESC
                LIMIT ?
                """,
                [*parameters, limit],
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, memory_id: str) -> MemoryRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def find_by_summary(self, *, type: str, scope: str, summary: str) -> MemoryRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM memories
                WHERE type = ? AND scope = ? AND summary = ?
                """,
                (type, scope, summary),
            ).fetchone()
        return self._from_row(row) if row else None

    def delete(self, memory_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE id = ?",
                (memory_id,),
            )
        return cursor.rowcount > 0

    def mark_used(self, memory_ids: list[str]) -> None:
        if not memory_ids:
            return
        now = utc_now_iso()
        placeholders = ",".join("?" for _ in memory_ids)
        with self._connect() as connection:
            connection.execute(
                f"""
                UPDATE memories
                SET use_count = use_count + 1,
                    updated_at = ?
                WHERE id IN ({placeholders})
                """,
                [now, *memory_ids],
            )

    def apply_feedback(self, memory_ids: list[str], positive: bool) -> list[MemoryRecord]:
        if not memory_ids:
            return []
        now = utc_now_iso()
        placeholders = ",".join("?" for _ in memory_ids)
        confidence_delta = 0.1 if positive else -0.15
        reliability_delta = 0.05 if positive else -0.1
        with self._connect() as connection:
            connection.execute(
                f"""
                UPDATE memories
                SET confidence = min(1.0, max(0.0, confidence + ?)),
                    reliability_score = min(1.0, max(0.0, reliability_score + ?)),
                    updated_at = ?
                WHERE id IN ({placeholders})
                """,
                [confidence_delta, reliability_delta, now, *memory_ids],
            )
        updated: list[MemoryRecord] = []
        for memory_id in memory_ids:
            record = self.get(memory_id)
            if record is not None:
                updated.append(record)
        return updated

    def _from_row(self, row: sqlite3.Row) -> MemoryRecord:
        tags = tuple(tag for tag in row["tags"].split(",") if tag)
        return MemoryRecord(
            id=row["id"],
            type=row["type"],
            scope=row["scope"],
            content=row["content"],
            summary=row["summary"],
            source_task_id=row["source_task_id"],
            confidence=float(row["confidence"]),
            reliability_score=float(row["reliability_score"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            use_count=int(row["use_count"]),
            tags=tags,
        )
