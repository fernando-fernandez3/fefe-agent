"""Native local long-form memory provider for Hermes.

Stores durable notes in JSONL and optionally maintains a SQLite FTS5 index.
The JSONL file is the source of truth so the provider remains usable when
FTS5 is unavailable.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from agent.memory_provider import MemoryProvider
from tools.registry import tool_error, tool_result

logger = logging.getLogger(__name__)

VALID_KINDS = {"episodic", "source", "project", "user_detail"}
DEFAULT_KIND = "episodic"
DEFAULT_SEARCH_LIMIT = 5
DEFAULT_LIST_LIMIT = 20
PREFETCH_LIMIT = 3
PREFETCH_SNIPPET_CHARS = 280
TOOL_CONTENT_CHARS = 1400


LONG_MEMORY_ADD_SCHEMA = {
    "name": "long_memory_add",
    "description": (
        "Store rich local long-form memory that should be searchable later but "
        "not always injected into the system prompt. Use for episodic details, "
        "source notes, project context, or detailed user information."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Detailed note content to store."},
            "title": {"type": "string", "description": "Optional short title."},
            "kind": {
                "type": "string",
                "enum": ["episodic", "source", "project", "user_detail"],
                "description": "Memory kind. Defaults to episodic.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional searchable tags.",
            },
            "source": {"type": "string", "description": "Optional source, URL, file, or session reference."},
        },
        "required": ["content"],
    },
}


LONG_MEMORY_SEARCH_SCHEMA = {
    "name": "long_memory_search",
    "description": "Search native local long-form memory notes by keyword with optional kind and tag filters.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keyword query."},
            "top_k": {"type": "integer", "description": "Maximum results to return. Defaults to 5."},
            "kind": {
                "type": "string",
                "enum": ["episodic", "source", "project", "user_detail"],
                "description": "Optional memory kind filter.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags. Results must include all listed tags.",
            },
        },
        "required": ["query"],
    },
}


LONG_MEMORY_LIST_SCHEMA = {
    "name": "long_memory_list",
    "description": "List recent native local long-form memory notes with optional kind and tag filters.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Maximum notes to return. Defaults to 20."},
            "kind": {
                "type": "string",
                "enum": ["episodic", "source", "project", "user_detail"],
                "description": "Optional memory kind filter.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags. Notes must include all listed tags.",
            },
        },
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_kind(kind: Optional[str]) -> str:
    normalized = (kind or DEFAULT_KIND).strip().lower()
    if normalized not in VALID_KINDS:
        raise ValueError(f"kind must be one of: {', '.join(sorted(VALID_KINDS))}")
    return normalized


def _normalize_tags(tags: Any) -> List[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        raw = re.split(r"[,#\s]+", tags)
    elif isinstance(tags, Iterable):
        raw = [str(t) for t in tags]
    else:
        raw = [str(tags)]
    seen = set()
    normalized = []
    for tag in raw:
        tag = tag.strip().lower()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    return normalized


def _safe_int(value: Any, default: int, *, minimum: int = 1, maximum: int = 100) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _snippet(text: str, limit: int) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def _tokenize_query(query: str) -> List[str]:
    return [t.lower() for t in re.findall(r"[\w-]+", query or "") if t.strip()]


def _fts_query(query: str) -> str:
    tokens = _tokenize_query(query)
    return " OR ".join(f'"{token.replace(chr(34), chr(34) + chr(34))}"' for token in tokens)


def _matches_filters(note: Dict[str, Any], *, kind: Optional[str], tags: List[str]) -> bool:
    if kind and note.get("kind") != kind:
        return False
    note_tags = set(_normalize_tags(note.get("tags", [])))
    return all(tag in note_tags for tag in tags)


def _public_note(note: Dict[str, Any], *, content_limit: int = TOOL_CONTENT_CHARS) -> Dict[str, Any]:
    result = dict(note)
    result["content"] = _snippet(result.get("content", ""), content_limit)
    return result


class LongMemoryProvider(MemoryProvider):
    """Local JSONL-backed long-form episodic memory."""

    def __init__(self) -> None:
        self._session_id = ""
        self._base_dir: Optional[Path] = None
        self._notes_path: Optional[Path] = None
        self._index_path: Optional[Path] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._fts_available = False
        self._lock = threading.RLock()
        self._prefetch_threads: Dict[str, threading.Thread] = {}
        self._prefetch_cache: Dict[str, Dict[str, str]] = {}

    @property
    def name(self) -> str:
        return "long_memory"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        hermes_home = kwargs.get("hermes_home")
        if hermes_home:
            home = Path(hermes_home)
        else:
            from hermes_constants import get_hermes_home

            home = get_hermes_home()
        self._session_id = session_id
        self._base_dir = home / "long_memory"
        self._notes_path = self._base_dir / "notes.jsonl"
        self._index_path = self._base_dir / "index.sqlite3"
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._notes_path.touch(exist_ok=True)
        self._initialize_index()

    def system_prompt_block(self) -> str:
        return (
            "# Memory Taxonomy\n"
            "- Pinned profile and built-in memory are small always-on facts injected every turn.\n"
            "- Skills are procedural workflows and operating instructions.\n"
            "- long_memory stores detailed episodic, source, project, and user_detail notes that are retrieved only when relevant.\n"
            "- Use long_memory_add for rich details that should be searchable later, not for facts that must always be injected."
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        if not (query or "").strip():
            return ""
        key = session_id or self._session_id or "default"
        cached = self._prefetch_cache.get(key)
        if cached and cached.get("query") == query:
            return cached.get("context", "")
        return self._format_prefetch_context(self.search(query, top_k=PREFETCH_LIMIT))

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        if not (query or "").strip():
            return
        key = session_id or self._session_id or "default"
        existing = self._prefetch_threads.get(key)
        if existing and existing.is_alive():
            return

        def _run() -> None:
            try:
                context = self._format_prefetch_context(self.search(query, top_k=PREFETCH_LIMIT))
                self._prefetch_cache[key] = {"query": query, "context": context}
            except Exception:
                logger.debug("long_memory background prefetch failed", exc_info=True)

        thread = threading.Thread(target=_run, daemon=True, name="long-memory-prefetch")
        self._prefetch_threads[key] = thread
        thread.start()

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        # v1 stores explicit notes via long_memory_add only.
        return

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [LONG_MEMORY_ADD_SCHEMA, LONG_MEMORY_SEARCH_SCHEMA, LONG_MEMORY_LIST_SCHEMA]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        try:
            if tool_name == "long_memory_add":
                note = self.add_note(
                    content=str(args.get("content", "")),
                    title=args.get("title"),
                    kind=args.get("kind"),
                    tags=args.get("tags"),
                    source=args.get("source"),
                )
                return tool_result({"status": "added", "note": note})
            if tool_name == "long_memory_search":
                results = self.search(
                    str(args.get("query", "")),
                    top_k=_safe_int(args.get("top_k"), DEFAULT_SEARCH_LIMIT, maximum=25),
                    kind=args.get("kind"),
                    tags=args.get("tags"),
                )
                return tool_result({"results": results, "count": len(results)})
            if tool_name == "long_memory_list":
                notes = self.list_notes(
                    limit=_safe_int(args.get("limit"), DEFAULT_LIST_LIMIT, maximum=100),
                    kind=args.get("kind"),
                    tags=args.get("tags"),
                )
                return tool_result({"notes": notes, "count": len(notes)})
        except Exception as exc:
            return tool_error(str(exc))
        return tool_error(f"Unknown tool: {tool_name}")

    def shutdown(self) -> None:
        for thread in list(self._prefetch_threads.values()):
            if thread.is_alive():
                thread.join(timeout=1.0)
        self._prefetch_threads.clear()
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = None
        self._fts_available = False

    def add_note(
        self,
        *,
        content: str,
        title: Any = None,
        kind: Any = None,
        tags: Any = None,
        source: Any = None,
    ) -> Dict[str, Any]:
        self._ensure_initialized()
        clean_content = str(content or "").strip()
        if not clean_content:
            raise ValueError("content is required")
        now = _utc_now()
        note = {
            "id": uuid.uuid4().hex,
            "content": clean_content,
            "title": str(title).strip() if title else "",
            "kind": _normalize_kind(str(kind) if kind is not None else None),
            "tags": _normalize_tags(tags),
            "source": str(source).strip() if source else "",
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            assert self._notes_path is not None
            with self._notes_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(note, ensure_ascii=False, sort_keys=True) + "\n")
            self._index_note(note)
            self._prefetch_cache.clear()
        return dict(note)

    def search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_SEARCH_LIMIT,
        kind: Any = None,
        tags: Any = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_initialized()
        query = (query or "").strip()
        if not query:
            return []
        top_k = _safe_int(top_k, DEFAULT_SEARCH_LIMIT, maximum=100)
        normalized_kind = _normalize_kind(str(kind)) if kind else None
        normalized_tags = _normalize_tags(tags)
        with self._lock:
            if self._fts_available:
                try:
                    return self._search_fts(query, top_k=top_k, kind=normalized_kind, tags=normalized_tags)
                except Exception:
                    logger.debug("long_memory FTS search failed; falling back to scan", exc_info=True)
            return self._search_scan(query, top_k=top_k, kind=normalized_kind, tags=normalized_tags)

    def list_notes(
        self,
        *,
        limit: int = DEFAULT_LIST_LIMIT,
        kind: Any = None,
        tags: Any = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_initialized()
        limit = _safe_int(limit, DEFAULT_LIST_LIMIT, maximum=500)
        normalized_kind = _normalize_kind(str(kind)) if kind else None
        normalized_tags = _normalize_tags(tags)
        with self._lock:
            notes = [
                note
                for note in self._read_notes()
                if _matches_filters(note, kind=normalized_kind, tags=normalized_tags)
            ]
        notes.sort(key=lambda n: n.get("created_at", ""), reverse=True)
        return [_public_note(note) for note in notes[:limit]]

    def _initialize_index(self) -> None:
        self._fts_available = False
        if self._index_path is None:
            return
        try:
            self._conn = sqlite3.connect(str(self._index_path), check_same_thread=False)
            self._conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                    id UNINDEXED,
                    title,
                    content,
                    kind,
                    tags,
                    source,
                    created_at UNINDEXED,
                    updated_at UNINDEXED
                )
                """
            )
            self._conn.execute("DELETE FROM notes_fts")
            for note in self._read_notes():
                self._index_note(note, commit=False)
            self._conn.commit()
            self._fts_available = True
        except sqlite3.Error:
            logger.debug("SQLite FTS5 unavailable for long_memory; using JSONL scan", exc_info=True)
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
            self._conn = None

    def _index_note(self, note: Dict[str, Any], *, commit: bool = True) -> None:
        if not self._conn:
            return
        try:
            self._conn.execute(
                """
                INSERT INTO notes_fts(id, title, content, kind, tags, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note.get("id", ""),
                    note.get("title", ""),
                    note.get("content", ""),
                    note.get("kind", ""),
                    " ".join(_normalize_tags(note.get("tags", []))),
                    note.get("source", ""),
                    note.get("created_at", ""),
                    note.get("updated_at", ""),
                ),
            )
            if commit:
                self._conn.commit()
        except sqlite3.Error:
            logger.debug("long_memory index write failed; disabling FTS", exc_info=True)
            self._fts_available = False

    def _search_fts(
        self,
        query: str,
        *,
        top_k: int,
        kind: Optional[str],
        tags: List[str],
    ) -> List[Dict[str, Any]]:
        fts_query = _fts_query(query)
        if not fts_query or not self._conn:
            return self._search_scan(query, top_k=top_k, kind=kind, tags=tags)
        rows = self._conn.execute(
            "SELECT id FROM notes_fts WHERE notes_fts MATCH ? ORDER BY bm25(notes_fts) LIMIT ?",
            (fts_query, max(top_k * 8, top_k)),
        ).fetchall()
        wanted_ids = [row[0] for row in rows]
        if not wanted_ids:
            return []
        notes_by_id = {note.get("id"): note for note in self._read_notes()}
        results = []
        for note_id in wanted_ids:
            note = notes_by_id.get(note_id)
            if note and _matches_filters(note, kind=kind, tags=tags):
                results.append(_public_note(note))
            if len(results) >= top_k:
                break
        return results

    def _search_scan(
        self,
        query: str,
        *,
        top_k: int,
        kind: Optional[str],
        tags: List[str],
    ) -> List[Dict[str, Any]]:
        tokens = _tokenize_query(query)
        if not tokens:
            return []
        scored = []
        for note in self._read_notes():
            if not _matches_filters(note, kind=kind, tags=tags):
                continue
            haystack = " ".join(
                [
                    str(note.get("title", "")),
                    str(note.get("content", "")),
                    str(note.get("kind", "")),
                    " ".join(_normalize_tags(note.get("tags", []))),
                    str(note.get("source", "")),
                ]
            ).lower()
            score = sum(haystack.count(token) for token in tokens)
            if score > 0:
                scored.append((score, note.get("updated_at", ""), note))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [_public_note(note) for _, _, note in scored[:top_k]]

    def _format_prefetch_context(self, notes: List[Dict[str, Any]]) -> str:
        if not notes:
            return ""
        lines = ["## Retrieved Long Memory"]
        for note in notes[:PREFETCH_LIMIT]:
            tags = ", ".join(_normalize_tags(note.get("tags", []))) or "none"
            source = note.get("source") or "unspecified"
            title = note.get("title") or "untitled"
            lines.append(
                f"- id={note.get('id')} kind={note.get('kind')} tags={tags} source={source} title={title}: "
                f"{_snippet(note.get('content', ''), PREFETCH_SNIPPET_CHARS)}"
            )
        return "\n".join(lines)

    def _read_notes(self) -> List[Dict[str, Any]]:
        if self._notes_path is None or not self._notes_path.exists():
            return []
        notes = []
        with self._notes_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    note = json.loads(line)
                except json.JSONDecodeError:
                    logger.debug("Skipping malformed long_memory JSONL row")
                    continue
                if isinstance(note, dict) and note.get("id") and note.get("content"):
                    note["kind"] = _normalize_kind(note.get("kind"))
                    note["tags"] = _normalize_tags(note.get("tags", []))
                    notes.append(note)
        return notes

    def _ensure_initialized(self) -> None:
        if self._notes_path is not None:
            return
        from hermes_constants import get_hermes_home

        self.initialize(session_id=self._session_id or "", hermes_home=str(get_hermes_home()))


def register(ctx) -> None:
    """Register native long memory as a memory provider plugin."""
    ctx.register_memory_provider(LongMemoryProvider())
