# Long Memory

Native Hermes long-form memory stores detailed notes locally under
`$HERMES_HOME/long_memory/`.

Enable it:

```bash
hermes config set memory.provider long_memory
```

Files:

- `notes.jsonl` is the durable source of truth.
- `index.sqlite3` is an optional SQLite FTS5 keyword index. If FTS5 is not
  available, Hermes falls back to scanning `notes.jsonl`.

Tools:

| Tool | Purpose |
|------|---------|
| `long_memory_add` | Store episodic, source, project, or user_detail notes |
| `long_memory_search` | Keyword search notes with kind/tag filters |
| `long_memory_list` | List recent notes with kind/tag filters |

Use built-in memory for small facts that should always be injected. Use
`long_memory_add` for richer details that should be retrieved only when
relevant.
