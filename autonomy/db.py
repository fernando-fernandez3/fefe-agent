"""SQLite persistence for autonomy state."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from hermes_constants import get_hermes_home

DEFAULT_DB_PATH = get_hermes_home() / 'autonomy.db'

SCHEMA_SQL = '''
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS goals (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    domain TEXT NOT NULL,
    priority INTEGER NOT NULL,
    status TEXT NOT NULL,
    horizon TEXT NOT NULL,
    constraints_json TEXT NOT NULL DEFAULT '{}',
    success_signals_json TEXT NOT NULL DEFAULT '[]',
    why_it_matters TEXT NOT NULL DEFAULT '',
    progress_examples_json TEXT NOT NULL DEFAULT '[]',
    review_thresholds_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS goal_matrix_entries (
    id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    label TEXT NOT NULL,
    locator TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(goal_id) REFERENCES goals(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS policies (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL UNIQUE,
    trust_level INTEGER NOT NULL,
    allowed_actions_json TEXT NOT NULL,
    approval_required_for_json TEXT NOT NULL,
    verification_required INTEGER NOT NULL,
    max_parallelism INTEGER NOT NULL,
    escalation_contacts_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    source_sensor TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    signal_strength REAL NOT NULL,
    evidence_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS world_state (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    state_json TEXT NOT NULL,
    freshness_ts TEXT NOT NULL,
    source TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(domain, entity_type, entity_key)
);

CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    goal_id TEXT,
    source_sensor TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    risk_level TEXT NOT NULL,
    confidence REAL NOT NULL,
    urgency REAL NOT NULL,
    expected_value REAL NOT NULL,
    context_cost REAL NOT NULL,
    score REAL NOT NULL,
    status TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    delegation_mode TEXT NOT NULL DEFAULT 'direct_hermes',
    delegation_target TEXT,
    desired_outcome TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(goal_id) REFERENCES goals(id)
);

CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT,
    domain TEXT NOT NULL,
    plan_json TEXT NOT NULL DEFAULT '{}',
    executor_type TEXT NOT NULL,
    status TEXT NOT NULL,
    verification_json TEXT NOT NULL DEFAULT '{}',
    outcome_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT,
    completed_at TEXT,
    review_required INTEGER NOT NULL DEFAULT 0,
    lease_owner TEXT,
    lease_expires_at TEXT,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    review_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY(execution_id) REFERENCES executions(id)
);

CREATE TABLE IF NOT EXISTS daily_digests (
    id TEXT PRIMARY KEY,
    date_key TEXT NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    content_json TEXT NOT NULL DEFAULT '{}',
    goal_ids_json TEXT NOT NULL DEFAULT '[]',
    opportunity_ids_json TEXT NOT NULL DEFAULT '[]',
    review_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learnings (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    execution_id TEXT,
    title TEXT NOT NULL,
    lesson TEXT NOT NULL,
    confidence REAL NOT NULL,
    actionability TEXT NOT NULL,
    apply_as TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(execution_id) REFERENCES executions(id)
);

CREATE INDEX IF NOT EXISTS idx_goals_domain_status ON goals(domain, status);
CREATE INDEX IF NOT EXISTS idx_goal_matrix_goal_id ON goal_matrix_entries(goal_id, weight DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_signals_domain_created_at ON signals(domain, created_at);
CREATE INDEX IF NOT EXISTS idx_world_state_lookup ON world_state(domain, entity_type, entity_key);
CREATE INDEX IF NOT EXISTS idx_opportunities_domain_status ON opportunities(domain, status);
CREATE INDEX IF NOT EXISTS idx_reviews_status_created_at ON reviews(status, created_at);
CREATE INDEX IF NOT EXISTS idx_daily_digests_date_key ON daily_digests(date_key DESC);
'''

MIGRATIONS = [
    "ALTER TABLE goals ADD COLUMN why_it_matters TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE goals ADD COLUMN progress_examples_json TEXT NOT NULL DEFAULT '[]'",
    "ALTER TABLE goals ADD COLUMN review_thresholds_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE opportunities ADD COLUMN delegation_mode TEXT NOT NULL DEFAULT 'direct_hermes'",
    "ALTER TABLE opportunities ADD COLUMN delegation_target TEXT",
    "ALTER TABLE opportunities ADD COLUMN desired_outcome TEXT NOT NULL DEFAULT ''",
]


class AutonomyDB:
    """Small SQLite wrapper for the autonomy MVP."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA_SQL)
            for migration in MIGRATIONS:
                try:
                    self._conn.execute(migration)
                except sqlite3.OperationalError as exc:
                    if 'duplicate column name' not in str(exc).lower():
                        raise
            self._conn.commit()

    def execute(self, sql: str, params: tuple = ()):
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def fetchone(self, sql: str, params: tuple = ()):
        with self._lock:
            return self._conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()):
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
