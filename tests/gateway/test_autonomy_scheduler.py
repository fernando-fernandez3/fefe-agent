from types import SimpleNamespace

import pytest

from gateway.config import HomeChannel, Platform
from gateway.run import GatewayRunner, _load_autonomy_runtime_config
from hermes_cli.config import DEFAULT_CONFIG, _KNOWN_ROOT_KEYS


def _autonomy_cfg(**overrides):
    cfg = {
        "enabled": True,
        "mode": "desired_state",
        "tick_interval_minutes": 1,
        "max_actions_per_tick": 3,
        "allowed_domains": ["code_projects"],
        "telegram_reviews_enabled": True,
        "fallback_to_legacy_on_error": True,
        "autoworkflow_base_url": "http://127.0.0.1:8882",
        "autoworkflow_api_token": "",
        "daily_digest": {"enabled": False},
    }
    cfg.update(overrides)
    return cfg


class _CaptureAdapter:
    def __init__(self):
        self.sent = []

    async def send(self, chat_id, message, **kwargs):
        self.sent.append((chat_id, message, kwargs))


async def _no_digest(cfg):
    return None


def test_default_config_includes_desired_state_autonomy_options():
    autonomy = DEFAULT_CONFIG["autonomy"]

    assert "autonomy" in _KNOWN_ROOT_KEYS
    assert autonomy["mode"] == "desired_state"
    assert autonomy["max_actions_per_tick"] == 3
    assert autonomy["fallback_to_legacy_on_error"] is True
    assert autonomy["autoworkflow"]["base_url"] == "http://127.0.0.1:8882"
    assert autonomy["autoworkflow"]["api_token"] == ""
    assert autonomy["daily_digest"] == {
        "enabled": False,
        "delivery_time": "08:00",
        "channel": "telegram",
    }


def test_load_autonomy_runtime_config_parses_desired_state_options(monkeypatch):
    monkeypatch.setattr(
        "gateway.run._load_gateway_config",
        lambda: {
            "autonomy": {
                "enabled": "true",
                "mode": "desired_state",
                "tick_interval_minutes": "7",
                "max_actions_per_tick": "5",
                "allowed_domains": ["code_projects", "", "docs"],
                "telegram_reviews_enabled": "false",
                "autoworkflow": {
                    "base_url": "http://aw.local/",
                    "api_token": "token-123",
                },
                "daily_digest": {
                    "enabled": "yes",
                    "delivery_time": "09:30",
                    "channel": "telegram",
                },
            }
        },
    )

    cfg = _load_autonomy_runtime_config()

    assert cfg["enabled"] is True
    assert cfg["mode"] == "desired_state"
    assert cfg["tick_interval_minutes"] == 7
    assert cfg["max_actions_per_tick"] == 5
    assert cfg["allowed_domains"] == ["code_projects", "docs"]
    assert cfg["telegram_reviews_enabled"] is False
    assert cfg["fallback_to_legacy_on_error"] is True
    assert cfg["autoworkflow_base_url"] == "http://aw.local"
    assert cfg["autoworkflow_api_token"] == "token-123"
    assert cfg["daily_digest"] == {
        "enabled": True,
        "delivery_time": "09:30",
        "channel": "telegram",
    }


def test_load_autonomy_runtime_config_uses_autoworkflow_env_fallback(monkeypatch):
    monkeypatch.setenv("AUTOWORKFLOW_BASE_URL", "http://aw-env.local/")
    monkeypatch.setenv("AUTOWORKFLOW_API_TOKEN", "env-token")
    monkeypatch.setattr(
        "gateway.run._load_gateway_config",
        lambda: {"autonomy": {"enabled": True, "autoworkflow": {}}},
    )

    cfg = _load_autonomy_runtime_config()

    assert cfg["autoworkflow_base_url"] == "http://aw-env.local"
    assert cfg["autoworkflow_api_token"] == "env-token"


@pytest.mark.asyncio
async def test_desired_state_mode_runs_sweep(monkeypatch):
    calls = []

    class _Sweep:
        def run(self):
            calls.append("run")
            return SimpleNamespace(status="ok", errors=[], goals_checked=2, actions_taken=1)

    runner = object.__new__(GatewayRunner)
    runner._autonomy_config = lambda: _autonomy_cfg()
    runner._get_or_create_desired_state_sweep = lambda: _Sweep()
    runner._maybe_generate_and_deliver_daily_digest = _no_digest

    assert await runner._maybe_run_autonomy_scheduler_tick() == [
        "Sweep: 2 goals, 1 actions"
    ]
    assert calls == ["run"]


@pytest.mark.asyncio
async def test_desired_state_interval_gate_prevents_second_run_but_still_checks_digest(monkeypatch):
    calls = []
    legacy_calls = []
    digest_calls = []

    class _Sweep:
        def run(self):
            calls.append("run")
            return SimpleNamespace(status="ok", errors=[], goals_checked=1, actions_taken=0)

    async def fake_legacy(cfg):
        legacy_calls.append(cfg)
        return ["legacy"]

    async def fake_digest(cfg):
        digest_calls.append(cfg)
        return "digest"

    runner = object.__new__(GatewayRunner)
    runner._autonomy_config = lambda: _autonomy_cfg(tick_interval_minutes=1)
    runner._get_or_create_desired_state_sweep = lambda: _Sweep()
    runner._run_legacy_autonomy_ticks = fake_legacy
    runner._maybe_generate_and_deliver_daily_digest = fake_digest

    assert await runner._maybe_run_autonomy_scheduler_tick() == [
        "Sweep: 1 goals, 0 actions",
        "digest",
    ]
    assert await runner._maybe_run_autonomy_scheduler_tick() == ["digest"]
    assert calls == ["run"]
    assert legacy_calls == []
    assert len(digest_calls) == 2


@pytest.mark.asyncio
async def test_desired_state_runs_again_after_interval_elapsed(monkeypatch):
    import gateway.run as gateway_run

    calls = []

    class _Sweep:
        def run(self):
            calls.append("run")
            return SimpleNamespace(status="ok", errors=[], goals_checked=1, actions_taken=0)

    runner = object.__new__(GatewayRunner)
    runner._autonomy_config = lambda: _autonomy_cfg(tick_interval_minutes=1)
    runner._get_or_create_desired_state_sweep = lambda: _Sweep()
    runner._maybe_generate_and_deliver_daily_digest = _no_digest

    assert await runner._maybe_run_autonomy_scheduler_tick() == [
        "Sweep: 1 goals, 0 actions"
    ]
    runner._last_desired_state_sweep_ts = gateway_run.time.monotonic() - 60
    assert await runner._maybe_run_autonomy_scheduler_tick() == [
        "Sweep: 1 goals, 0 actions"
    ]
    assert calls == ["run", "run"]


@pytest.mark.asyncio
async def test_desired_state_sweep_rebuilds_when_autoworkflow_token_rotates(monkeypatch):
    import autonomy.desired_state_sweep as sweep_mod
    import autonomy.executors.autoworkflow_executor as autoworkflow_executor_mod
    import autonomy.executors.codex_executor as codex_executor_mod
    import autonomy.executors.repo_executor as repo_executor_mod
    import autonomy.sensors.registry as registry_mod
    import autonomy.store as store_mod

    created_tokens = []

    class _Store:
        def close(self):
            pass

    class _Registry:
        @staticmethod
        def default(**kwargs):
            return SimpleNamespace(kwargs=kwargs)

    class _Sweep:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class _Executor:
        def __init__(self, **kwargs):
            created_tokens.append(kwargs.get("api_token"))

    monkeypatch.setattr(store_mod, "AutonomyStore", _Store)
    monkeypatch.setattr(registry_mod, "SensorRegistry", _Registry)
    monkeypatch.setattr(sweep_mod, "DesiredStateSweep", _Sweep)
    monkeypatch.setattr(repo_executor_mod, "RepoExecutor", lambda: object())
    monkeypatch.setattr(codex_executor_mod, "CodexExecutor", lambda: object())
    monkeypatch.setattr(autoworkflow_executor_mod, "AutoWorkflowExecutor", _Executor)

    runner = object.__new__(GatewayRunner)
    token = {"value": "token-a"}
    runner._autonomy_config = lambda: _autonomy_cfg(autoworkflow_api_token=token["value"])

    first = runner._get_or_create_desired_state_sweep()
    token["value"] = "token-b"
    second = runner._get_or_create_desired_state_sweep()

    assert first is not second
    assert created_tokens == ["token-a", "token-b"]


@pytest.mark.asyncio
async def test_legacy_mode_uses_independent_scheduler_per_allowed_domain(monkeypatch):
    calls = []

    class _Scheduler:
        def __init__(self, domain):
            self.domain = domain

        def trigger(self, *, domain, repo_path):
            calls.append((self.domain, domain))
            return SimpleNamespace(
                ran=True,
                tick_result=SimpleNamespace(review_id=f"review-{domain}"),
            )

    runner = object.__new__(GatewayRunner)
    runner._get_or_create_autonomy_scheduler = lambda *, domain: _Scheduler(domain)

    result = await runner._run_legacy_autonomy_ticks(
        _autonomy_cfg(mode="legacy_domain", allowed_domains=["code_projects", "docs"])
    )

    assert result == ["review-code_projects", "review-docs"]
    assert calls == [("code_projects", "code_projects"), ("docs", "docs")]


@pytest.mark.asyncio
async def test_desired_state_sweep_failure_falls_back_to_legacy_scheduler(monkeypatch):
    runner = object.__new__(GatewayRunner)
    runner._autonomy_config = lambda: _autonomy_cfg()
    runner._get_or_create_desired_state_sweep = lambda: (_ for _ in ()).throw(
        RuntimeError("boom")
    )

    async def fake_legacy(cfg):
        return ["legacy-review"]

    runner._run_legacy_autonomy_ticks = fake_legacy
    runner._maybe_generate_and_deliver_daily_digest = _no_digest

    assert await runner._maybe_run_autonomy_scheduler_tick() == ["legacy-review"]


@pytest.mark.asyncio
async def test_desired_state_sweep_failure_can_fail_closed_without_legacy_fallback(monkeypatch):
    legacy_calls = []
    runner = object.__new__(GatewayRunner)
    runner._autonomy_config = lambda: _autonomy_cfg(fallback_to_legacy_on_error=False)
    runner._get_or_create_desired_state_sweep = lambda: (_ for _ in ()).throw(
        RuntimeError("boom")
    )

    async def fake_legacy(cfg):
        legacy_calls.append(cfg)
        return ["legacy-review"]

    runner._run_legacy_autonomy_ticks = fake_legacy
    runner._maybe_generate_and_deliver_daily_digest = _no_digest

    assert await runner._maybe_run_autonomy_scheduler_tick() == []
    assert legacy_calls == []


@pytest.mark.asyncio
async def test_desired_state_error_result_does_not_advance_interval_gate(monkeypatch):
    legacy_calls = []

    class _Sweep:
        def run(self):
            return SimpleNamespace(
                status="error",
                errors=["load_goals_failed: boom"],
                goals_checked=0,
                actions_taken=0,
            )

    async def fake_legacy(cfg):
        legacy_calls.append(cfg)
        return []

    runner = object.__new__(GatewayRunner)
    runner._autonomy_config = lambda: _autonomy_cfg(fallback_to_legacy_on_error=True)
    runner._get_or_create_desired_state_sweep = lambda: _Sweep()
    runner._run_legacy_autonomy_ticks = fake_legacy
    runner._maybe_generate_and_deliver_daily_digest = _no_digest

    assert await runner._maybe_run_autonomy_scheduler_tick() == []
    assert legacy_calls
    assert getattr(runner, "_last_desired_state_sweep_ts", None) is None


@pytest.mark.asyncio
async def test_notify_autonomy_review_created_respects_telegram_gate(monkeypatch):
    import gateway.autonomy_review as autonomy_review

    adapter = _CaptureAdapter()
    runner = object.__new__(GatewayRunner)
    runner.adapters = {Platform.TELEGRAM: adapter}
    runner.config = SimpleNamespace(
        get_home_channel=lambda platform: HomeChannel(
            platform=platform,
            chat_id="chat-1",
            name="home",
        )
    )
    runner._autonomy_config = lambda: {"telegram_reviews_enabled": False}
    monkeypatch.setattr(
        autonomy_review,
        "format_review_notification",
        lambda review_id: "should not render",
    )

    await runner._notify_autonomy_review_created("review_1")

    assert adapter.sent == []

    runner._autonomy_config = lambda: {"telegram_reviews_enabled": True}
    monkeypatch.setattr(
        autonomy_review,
        "format_review_notification",
        lambda review_id: f"packet {review_id}",
    )

    await runner._notify_autonomy_review_created("review_2")

    assert adapter.sent == [("chat-1", "packet review_2", {})]


def test_cron_ticker_invokes_autonomy_tick(monkeypatch):
    import gateway.run as gateway_run

    class _StopAfterOne:
        def __init__(self):
            self.checked = 0

        def is_set(self):
            self.checked += 1
            return self.checked > 1

        def wait(self, timeout=None):
            return None

    class _Future:
        def __init__(self):
            self.timeouts = []

        def result(self, timeout=None):
            self.timeouts.append(timeout)
            return None

    calls = []
    future = _Future()

    async def fake_tick():
        return []

    def fake_run_coroutine_threadsafe(coro, loop):
        calls.append((coro, loop))
        coro.close()
        return future

    monkeypatch.setattr(
        "cron.scheduler.tick",
        lambda *, verbose, adapters, loop: None,
    )
    monkeypatch.setattr(
        gateway_run.asyncio,
        "run_coroutine_threadsafe",
        fake_run_coroutine_threadsafe,
    )

    runner = SimpleNamespace(_maybe_run_autonomy_scheduler_tick=fake_tick)
    loop = SimpleNamespace(is_running=lambda: True)

    gateway_run._start_cron_ticker(
        _StopAfterOne(),
        adapters={},
        loop=loop,
        interval=60,
        runner=runner,
    )

    assert len(calls) == 1
    assert calls[0][1] is loop
    assert future.timeouts == [30]
