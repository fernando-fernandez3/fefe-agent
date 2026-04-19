from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from tests.e2e.conftest import (
    make_adapter,
    make_session_entry,
    make_source,
    make_runner,
    send_and_capture,
)


@pytest.fixture()
def source():
    return make_source()


@pytest.fixture()
def session_entry(source):
    return make_session_entry(source)


@pytest.fixture()
def runner(session_entry):
    return make_runner(session_entry)


@pytest.fixture()
def adapter(runner):
    return make_adapter(runner)


@pytest.mark.asyncio
async def test_review_command_returns_rendered_cards(adapter, monkeypatch):
    monkeypatch.setattr(
        "gateway.run._load_autoworkflow_review_runtime_config",
        lambda: {
            "enabled": True,
            "base_url": "http://autoworkflow.test",
            "api_token": "token",
            "digest_limit": 5,
        },
    )
    monkeypatch.setattr(
        "gateway.autoworkflow_review.list_review_items",
        AsyncMock(
            return_value=[
                {
                    "id": "ri_12",
                    "title": "Embarka onboarding gap",
                    "summary": "Add a tighter onboarding draft",
                    "priority": 90,
                    "confidence": 0.81,
                    "risk_level": "low",
                }
            ]
        ),
    )

    send = await send_and_capture(adapter, "/review")
    send.assert_called_once()
    response_text = send.call_args[1].get("content") or send.call_args[0][1]
    assert "Review queue:" in response_text
    assert "ri_12" in response_text
    assert "/approve <id>" in response_text


@pytest.mark.asyncio
async def test_approve_command_submits_decision(adapter, monkeypatch):
    monkeypatch.setattr(
        "gateway.run._load_autoworkflow_review_runtime_config",
        lambda: {
            "enabled": True,
            "base_url": "http://autoworkflow.test",
            "api_token": "token",
            "digest_limit": 5,
        },
    )
    submit = AsyncMock(return_value={"review_item_id": "ri_12", "status": "approved"})
    monkeypatch.setattr("gateway.autoworkflow_review.submit_review_decision", submit)

    send = await send_and_capture(adapter, "/approve ri_12 looks good")
    send.assert_called_once()
    submit.assert_awaited_once_with(
        "http://autoworkflow.test",
        "token",
        "ri_12",
        "approve",
        "looks good",
    )
    response_text = send.call_args[1].get("content") or send.call_args[0][1]
    assert "approved ri_12" in response_text


@pytest.mark.asyncio
async def test_reject_raw_text_submits_decision(adapter, monkeypatch):
    monkeypatch.setattr(
        "gateway.run._load_autoworkflow_review_runtime_config",
        lambda: {
            "enabled": True,
            "base_url": "http://autoworkflow.test",
            "api_token": "token",
            "digest_limit": 5,
        },
    )
    submit = AsyncMock(return_value={"review_item_id": "ri_13", "status": "rejected"})
    monkeypatch.setattr("gateway.autoworkflow_review.submit_review_decision", submit)

    send = await send_and_capture(adapter, "reject ri_13 too broad")
    send.assert_called_once()
    submit.assert_awaited_once_with(
        "http://autoworkflow.test",
        "token",
        "ri_13",
        "reject",
        "too broad",
    )
    response_text = send.call_args[1].get("content") or send.call_args[0][1]
    assert "rejected ri_13" in response_text


@pytest.mark.asyncio
async def test_edit_command_submits_instruction(adapter, monkeypatch):
    monkeypatch.setattr(
        "gateway.run._load_autoworkflow_review_runtime_config",
        lambda: {
            "enabled": True,
            "base_url": "http://autoworkflow.test",
            "api_token": "token",
            "digest_limit": 5,
        },
    )
    submit = AsyncMock(return_value={"review_item_id": "ri_16", "status": "needs_redraft"})
    monkeypatch.setattr("gateway.autoworkflow_review.submit_review_decision", submit)

    send = await send_and_capture(adapter, "/edit ri_16 focus only on onboarding")
    send.assert_called_once()
    submit.assert_awaited_once_with(
        "http://autoworkflow.test",
        "token",
        "ri_16",
        "edit",
        "focus only on onboarding",
    )
    response_text = send.call_args[1].get("content") or send.call_args[0][1]
    assert "needs_redraft ri_16" in response_text
