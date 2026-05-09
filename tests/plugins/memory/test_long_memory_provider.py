import json
from pathlib import Path

from plugins.memory.long_memory import LongMemoryProvider


def _provider(tmp_path):
    hermes_home = tmp_path / "hermes"
    provider = LongMemoryProvider()
    provider.initialize("test-session", hermes_home=str(hermes_home))
    return provider, hermes_home


def test_add_search_list_round_trip(tmp_path):
    provider, hermes_home = _provider(tmp_path)

    result = json.loads(
        provider.handle_tool_call(
            "long_memory_add",
            {
                "content": "The deployment runbook uses the amber release checklist.",
                "title": "Deploy runbook",
                "kind": "project",
                "tags": ["deploy", "runbook"],
                "source": "test",
            },
        )
    )

    assert result["status"] == "added"
    assert result["note"]["kind"] == "project"
    assert (hermes_home / "long_memory" / "notes.jsonl").exists()

    search = json.loads(
        provider.handle_tool_call("long_memory_search", {"query": "amber checklist", "top_k": 3})
    )
    assert search["count"] == 1
    assert search["results"][0]["title"] == "Deploy runbook"

    listed = json.loads(provider.handle_tool_call("long_memory_list", {"limit": 5}))
    assert listed["count"] == 1
    assert listed["notes"][0]["id"] == result["note"]["id"]


def test_kind_and_tag_filtering_works_with_jsonl_scan(tmp_path):
    provider, _ = _provider(tmp_path)
    provider._fts_available = False

    provider.add_note(
        content="Project alpha uses SQLite migrations.",
        kind="project",
        tags=["alpha", "database"],
    )
    provider.add_note(
        content="User prefers terse status updates about alpha.",
        kind="user_detail",
        tags=["alpha", "preference"],
    )
    provider.add_note(
        content="Project beta uses a separate release train.",
        kind="project",
        tags=["beta"],
    )

    project_alpha = provider.search("alpha", kind="project", tags=["database"])
    assert len(project_alpha) == 1
    assert project_alpha[0]["kind"] == "project"
    assert project_alpha[0]["tags"] == ["alpha", "database"]

    user_alpha = provider.list_notes(kind="user_detail", tags=["alpha"], limit=10)
    assert len(user_alpha) == 1
    assert "terse status" in user_alpha[0]["content"]


def test_prefetch_is_concise_labeled_and_limited(tmp_path):
    provider, _ = _provider(tmp_path)
    long_tail = " ".join(["extra detail"] * 80)
    for idx in range(6):
        provider.add_note(
            content=f"sharedneedle note {idx}. {long_tail}",
            title=f"Note {idx}",
            kind="episodic",
            tags=["shared", f"t{idx}"],
            source=f"source-{idx}",
        )

    context = provider.prefetch("sharedneedle")

    assert context.startswith("## Retrieved Long Memory")
    assert context.count("id=") == 3
    assert "kind=episodic" in context
    assert "tags=shared" in context
    assert "source=source-" in context
    assert len(context) < 1400
    assert context.count("sharedneedle note") < 6


def test_queued_prefetch_returns_cached_context(tmp_path):
    provider, _ = _provider(tmp_path)
    provider.add_note(content="The cached recall marker is cerulean.", tags=["cache"])

    provider.queue_prefetch("cerulean", session_id="s1")
    provider._prefetch_threads["s1"].join(timeout=2)

    context = provider.prefetch("cerulean", session_id="s1")
    assert "## Retrieved Long Memory" in context
    assert "cerulean" in context


def test_provider_discovery_and_load_finds_long_memory():
    from plugins.memory import discover_memory_providers, load_memory_provider

    providers = discover_memory_providers()
    assert "long_memory" in {name for name, _, _ in providers}

    provider = load_memory_provider("long_memory")
    assert provider is not None
    assert provider.name == "long_memory"
    assert provider.is_available()


def test_storage_uses_hermes_home_not_real_home(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    hermes_home = tmp_path / "profile-home"
    fake_home.mkdir()
    hermes_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    provider = LongMemoryProvider()
    provider.initialize("profile-session")
    provider.add_note(content="Profile scoped storage marker.", tags=["profile"])

    assert (hermes_home / "long_memory" / "notes.jsonl").exists()
    assert not (fake_home / ".hermes" / "long_memory" / "notes.jsonl").exists()
