"""Controllable scheduler wrapper for the autonomy MVP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from autonomy.execution_loop import AutonomyExecutionLoop, TickResult


@dataclass(slots=True)
class SchedulerResult:
    ran: bool
    reason: str
    tick_result: TickResult | None = None


class AutonomyScheduler:
    def __init__(
        self,
        *,
        loop: AutonomyExecutionLoop,
        interval_seconds: int = 300,
        runtime_ceiling_seconds: int = 3600,
        started_at: datetime | None = None,
    ):
        self.loop = loop
        self.interval_seconds = interval_seconds
        self.runtime_ceiling_seconds = runtime_ceiling_seconds
        self.started_at = started_at or datetime.now(timezone.utc)
        self.last_tick_started_at: datetime | None = None
        self.global_paused = False
        self.paused_domains: set[str] = set()

    def pause(self) -> None:
        self.global_paused = True

    def resume(self) -> None:
        self.global_paused = False

    def pause_domain(self, domain: str) -> None:
        self.paused_domains.add(domain)

    def resume_domain(self, domain: str) -> None:
        self.paused_domains.discard(domain)

    def trigger(
        self,
        *,
        domain: str,
        repo_path: Path | None = None,
        metadata: dict | None = None,
        manual: bool = False,
        now: datetime | None = None,
    ) -> SchedulerResult:
        current_time = now or datetime.now(timezone.utc)

        if self.global_paused:
            return SchedulerResult(ran=False, reason='global_paused')
        if domain in self.paused_domains:
            return SchedulerResult(ran=False, reason='domain_paused')
        if current_time - self.started_at >= timedelta(seconds=self.runtime_ceiling_seconds):
            return SchedulerResult(ran=False, reason='runtime_ceiling_exceeded')
        if not manual and self.last_tick_started_at is not None:
            if current_time - self.last_tick_started_at < timedelta(seconds=self.interval_seconds):
                return SchedulerResult(ran=False, reason='interval_not_elapsed')

        self.last_tick_started_at = current_time
        tick_result = self.loop.tick(domain=domain, repo_path=repo_path, metadata=metadata)
        return SchedulerResult(ran=True, reason='manual_trigger' if manual else 'interval_trigger', tick_result=tick_result)
