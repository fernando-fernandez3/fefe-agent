from datetime import datetime, timedelta, timezone
from pathlib import Path

from autonomy.execution_loop import TickResult
from autonomy.scheduler import AutonomyScheduler


class FakeLoop:
    def __init__(self):
        self.calls: list[dict] = []

    def tick(self, *, domain: str, repo_path: Path | None = None, metadata: dict | None = None) -> TickResult:
        self.calls.append({'domain': domain, 'repo_path': repo_path, 'metadata': metadata})
        return TickResult(domain=domain, status='executed', goals_considered=1)


def test_scheduler_runs_on_interval(tmp_path):
    loop = FakeLoop()
    start = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
    scheduler = AutonomyScheduler(loop=loop, interval_seconds=60, started_at=start)
    repo_path = tmp_path / 'repo'

    first = scheduler.trigger(domain='code_projects', repo_path=repo_path, now=start)
    second = scheduler.trigger(domain='code_projects', repo_path=repo_path, now=start + timedelta(seconds=30))
    third = scheduler.trigger(domain='code_projects', repo_path=repo_path, now=start + timedelta(seconds=61))

    assert first.ran is True
    assert first.reason == 'interval_trigger'
    assert second.ran is False
    assert second.reason == 'interval_not_elapsed'
    assert third.ran is True
    assert len(loop.calls) == 2


def test_scheduler_manual_trigger_bypasses_interval(tmp_path):
    loop = FakeLoop()
    start = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
    scheduler = AutonomyScheduler(loop=loop, interval_seconds=300, started_at=start)
    repo_path = tmp_path / 'repo'

    scheduler.trigger(domain='code_projects', repo_path=repo_path, now=start)
    manual = scheduler.trigger(
        domain='code_projects',
        repo_path=repo_path,
        manual=True,
        now=start + timedelta(seconds=10),
    )

    assert manual.ran is True
    assert manual.reason == 'manual_trigger'
    assert len(loop.calls) == 2


def test_scheduler_honors_global_pause(tmp_path):
    loop = FakeLoop()
    start = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
    scheduler = AutonomyScheduler(loop=loop, started_at=start)
    scheduler.pause()

    result = scheduler.trigger(domain='code_projects', repo_path=tmp_path / 'repo', now=start)

    assert result.ran is False
    assert result.reason == 'global_paused'
    assert loop.calls == []


def test_scheduler_honors_per_domain_pause(tmp_path):
    loop = FakeLoop()
    start = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
    scheduler = AutonomyScheduler(loop=loop, started_at=start)
    scheduler.pause_domain('code_projects')

    result = scheduler.trigger(domain='code_projects', repo_path=tmp_path / 'repo', now=start)

    assert result.ran is False
    assert result.reason == 'domain_paused'
    assert loop.calls == []


def test_scheduler_honors_runtime_ceiling(tmp_path):
    loop = FakeLoop()
    start = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
    scheduler = AutonomyScheduler(loop=loop, runtime_ceiling_seconds=120, started_at=start)

    result = scheduler.trigger(
        domain='code_projects',
        repo_path=tmp_path / 'repo',
        now=start + timedelta(seconds=121),
    )

    assert result.ran is False
    assert result.reason == 'runtime_ceiling_exceeded'
    assert loop.calls == []
