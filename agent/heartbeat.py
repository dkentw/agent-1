"""Heartbeat and liveness helpers for the agent loop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class HeartbeatEvent:
    session_id: str
    task_id: str
    loop_state: str
    active_step_title: str | None
    active_tool: str | None
    started_at: str
    elapsed_ms: int
    cancellable: bool
    cancellation_requested: bool
    message: str
    log_to_file: bool = False
    unhealthy: bool = False


class HeartbeatMonitor:
    def __init__(
        self,
        ui_interval_s: float = 1.0,
        log_interval_s: float = 10.0,
        unhealthy_after_s: float = 15.0,
    ):
        self.ui_interval_s = ui_interval_s
        self.log_interval_s = log_interval_s
        self.unhealthy_after_s = unhealthy_after_s
        self.session_id: str | None = None
        self.task_id: str | None = None
        self.started_at: str | None = None
        self.started_monotonic: float | None = None
        self.last_emit_monotonic: float | None = None
        self.last_log_monotonic: float | None = None
        self.active = False

    def start(
        self,
        session_id: str,
        task_id: str,
        loop_state: str,
        *,
        active_step_title: str | None = None,
        active_tool: str | None = None,
        message: str = "task started",
    ) -> HeartbeatEvent:
        now = monotonic()
        self.session_id = session_id
        self.task_id = task_id
        self.started_at = utc_now_iso()
        self.started_monotonic = now
        self.last_emit_monotonic = now
        self.last_log_monotonic = now
        self.active = True
        return self._event(loop_state, active_step_title, active_tool, message, now, log_to_file=True)

    def beat(
        self,
        loop_state: str,
        *,
        active_step_title: str | None = None,
        active_tool: str | None = None,
        message: str = "",
        force_log: bool = False,
    ) -> HeartbeatEvent:
        now = monotonic()
        self.last_emit_monotonic = now
        log_to_file = force_log or self._should_log(now)
        if log_to_file:
            self.last_log_monotonic = now
        return self._event(loop_state, active_step_title, active_tool, message, now, log_to_file=log_to_file)

    def stop(
        self,
        final_state: str,
        *,
        active_step_title: str | None = None,
        active_tool: str | None = None,
        message: str = "task stopped",
    ) -> HeartbeatEvent:
        now = monotonic()
        event = self._event(final_state, active_step_title, active_tool, message, now, log_to_file=True)
        self.active = False
        self.last_emit_monotonic = now
        self.last_log_monotonic = now
        return event

    def is_unhealthy(self) -> bool:
        if not self.active or self.last_emit_monotonic is None:
            return False
        return (monotonic() - self.last_emit_monotonic) > self.unhealthy_after_s

    def _should_log(self, now: float) -> bool:
        if self.last_log_monotonic is None:
            return True
        return (now - self.last_log_monotonic) >= self.log_interval_s

    def _event(
        self,
        loop_state: str,
        active_step_title: str | None,
        active_tool: str | None,
        message: str,
        now: float,
        *,
        log_to_file: bool,
    ) -> HeartbeatEvent:
        if self.session_id is None or self.task_id is None or self.started_monotonic is None or self.started_at is None:
            raise RuntimeError("heartbeat monitor has not started")
        elapsed_ms = int((now - self.started_monotonic) * 1000)
        return HeartbeatEvent(
            session_id=self.session_id,
            task_id=self.task_id,
            loop_state=loop_state,
            active_step_title=active_step_title,
            active_tool=active_tool,
            started_at=self.started_at,
            elapsed_ms=elapsed_ms,
            cancellable=loop_state not in {"completed", "failed", "cancelled"},
            cancellation_requested=False,
            message=message,
            log_to_file=log_to_file,
            unhealthy=self.is_unhealthy(),
        )

