from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

import pytest

from gateway.config import Platform
from tests.e2e.conftest import (
    make_adapter,
    make_session_entry,
    make_source,
    make_runner,
    send_and_capture,
)


@pytest.fixture()
def source():
    return make_source(Platform.TELEGRAM)


@pytest.fixture()
def session_entry(source):
    return make_session_entry(Platform.TELEGRAM, source)


@pytest.fixture()
def runner(session_entry):
    return make_runner(Platform.TELEGRAM, session_entry)


@pytest.fixture()
def adapter(runner):
    return make_adapter(Platform.TELEGRAM, runner)


@pytest.mark.asyncio
@pytest.mark.parametrize('command_text', ['/autonomy-seed', '/autonomy_seed'])
async def test_autonomy_seed_command_works_in_telegram(adapter, command_text):
    send = await send_and_capture(adapter, command_text, Platform.TELEGRAM)
    send.assert_called_once()
    response_text = send.call_args[1].get('content') or send.call_args[0][1]
    assert 'Seeded repo-health autonomy goal/policy for code_projects.' in response_text
    assert 'run /autonomy-run' in response_text


@pytest.mark.asyncio
async def test_reviews_command_returns_autonomy_cards(adapter, monkeypatch):
    monkeypatch.setattr(
        'gateway.autonomy_review.list_reviews',
        lambda limit=5: [
            {
                'id': 'review_12',
                'title': 'Review required: Fix failing tests',
                'summary': 'Selected from the autonomy queue for domain code_projects.',
                'proposed_action': 'codex_task',
                'approval_effect': 'Execution exec_12 will run Codex inside /repo to: Fix the failing tests.',
            }
        ],
    )

    send = await send_and_capture(adapter, '/reviews', Platform.TELEGRAM)
    send.assert_called_once()
    response_text = send.call_args[1].get('content') or send.call_args[0][1]
    assert 'Autonomy review queue, 1 pending:' in response_text
    assert 'ID: review_12' in response_text
    assert 'Approve: /review-approve review_12' in response_text
    assert 'Reject: /review-reject review_12 why' in response_text


@pytest.mark.asyncio
async def test_review_approve_command_executes_autonomy_work(adapter, monkeypatch):
    monkeypatch.setattr(
        'gateway.autonomy_review.approve_review',
        lambda review_id: {
            'review_id': review_id,
            'status': 'approved',
            'execution_id': 'exec_12',
            'executor_type': 'codex_executor',
        },
    )

    send = await send_and_capture(adapter, '/review-approve review_12', Platform.TELEGRAM)
    send.assert_called_once()
    response_text = send.call_args[1].get('content') or send.call_args[0][1]
    assert 'approved review_12' in response_text
    assert 'exec_12' in response_text
    assert 'Run /reviews to refresh the queue.' in response_text


@pytest.mark.asyncio
async def test_review_reject_command_cancels_autonomy_work(adapter, monkeypatch):
    monkeypatch.setattr(
        'gateway.autonomy_review.reject_review',
        lambda review_id, reason='': {
            'review_id': review_id,
            'status': 'rejected',
            'reason': reason,
        },
    )

    send = await send_and_capture(adapter, '/review-reject review_12 too risky', Platform.TELEGRAM)
    send.assert_called_once()
    response_text = send.call_args[1].get('content') or send.call_args[0][1]
    assert 'rejected review_12' in response_text
    assert 'too risky' in response_text
    assert 'Run /reviews to refresh the queue.' in response_text


@pytest.mark.asyncio
async def test_autonomy_run_proactively_sends_review_packet(adapter, runner, monkeypatch):
    class FakeLoop:
        def tick(self, domain, repo_path=None, metadata=None):
            asyncio.get_running_loop().create_task(
                runner._notify_autonomy_review_created('review_42', source=make_source(Platform.TELEGRAM))
            )
            from autonomy.execution_loop import TickResult

            return TickResult(
                domain='code_projects',
                status='review_required',
                goals_considered=1,
                review_id='review_42',
                execution_id='exec_42',
            )

    monkeypatch.setattr(runner, '_build_gateway_autonomy_execution_loop', lambda store, source=None: FakeLoop())
    monkeypatch.setattr('gateway.autonomy_review.format_review_notification', lambda review_id: f'notification for {review_id}\nApprove: /review-approve {review_id}')

    send = await send_and_capture(adapter, '/autonomy-run', Platform.TELEGRAM)
    assert send.call_count == 2
    messages = [
        (call.kwargs.get('content') or call.args[1])
        for call in send.call_args_list
    ]
    assert any('Autonomy tick: review_required' in message for message in messages)
    assert any('notification for review_42' in message for message in messages)
    assert any('/review-approve review_42' in message for message in messages)


@pytest.mark.asyncio
async def test_autonomy_scheduler_tick_runs_allowed_domains(runner, monkeypatch):
    class FakeTickResult:
        review_id = 'review_99'

    class FakeScheduler:
        def __init__(self):
            self.calls = []

        def trigger(self, *, domain, repo_path=None):
            self.calls.append((domain, repo_path))
            return MagicMock(ran=True, tick_result=FakeTickResult())

    fake_scheduler = FakeScheduler()
    monkeypatch.setattr(runner, '_autonomy_enabled', lambda: True)
    monkeypatch.setattr(runner, '_autonomy_config', lambda: {
        'enabled': True,
        'tick_interval_minutes': 15,
        'allowed_domains': ['code_projects', 'lab'],
        'telegram_reviews_enabled': True,
    })
    monkeypatch.setattr(runner, '_get_or_create_autonomy_scheduler', lambda: fake_scheduler)

    review_ids = await runner._maybe_run_autonomy_scheduler_tick()

    assert review_ids == ['review_99', 'review_99']
    assert [call[0] for call in fake_scheduler.calls] == ['code_projects', 'lab']


def test_cron_ticker_invokes_autonomy_scheduler_tick(monkeypatch):
    from gateway.run import _start_cron_ticker

    stop_event = threading.Event()
    loop = MagicMock()
    loop.is_running.return_value = True
    runner = MagicMock()
    runner._maybe_run_autonomy_scheduler_tick = MagicMock(return_value='coro')
    future = Future()
    future.set_result([])

    def fake_cron_tick(**kwargs):
        stop_event.set()

    with patch('cron.scheduler.tick', side_effect=fake_cron_tick), \
         patch('gateway.run.asyncio.run_coroutine_threadsafe', return_value=future) as mock_run:
        _start_cron_ticker(stop_event, adapters={}, loop=loop, interval=60, runner=runner)

    mock_run.assert_called_once()
