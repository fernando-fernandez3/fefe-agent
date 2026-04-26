#!/usr/bin/env python3
"""Refresh open failing-tests opportunity titles with repo labels."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from autonomy.opportunity_engine import failing_tests_opportunity_title  # noqa: E402
from autonomy.store import utc_now_iso  # noqa: E402
from hermes_constants import get_hermes_home  # noqa: E402


def _entity_key_from_id(opportunity_id: str) -> str:
    parts = opportunity_id.split('::', 3)
    return parts[3] if len(parts) == 4 else ''


def _load_evidence(raw_evidence: str | None) -> dict:
    if not raw_evidence:
        return {}
    try:
        evidence = json.loads(raw_evidence)
    except json.JSONDecodeError:
        return {}
    return evidence if isinstance(evidence, dict) else {}


def backfill(db_path: Path) -> int:
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute(
            "SELECT id, title, evidence_json FROM opportunities WHERE status = 'open'"
        ).fetchall()
        updates: list[tuple[str, str, str]] = []
        now = utc_now_iso()
        for opportunity_id, current_title, raw_evidence in rows:
            evidence = _load_evidence(raw_evidence)
            if evidence.get('signal_type') != 'failing_tests' and '::failing_tests::' not in opportunity_id:
                continue
            entity_key = evidence.get('entity_key') or _entity_key_from_id(opportunity_id)
            new_title = failing_tests_opportunity_title(evidence=evidence, entity_key=entity_key)
            if current_title != new_title:
                updates.append((new_title, now, opportunity_id))

        con.executemany(
            'UPDATE opportunities SET title = ?, updated_at = ? WHERE id = ?',
            updates,
        )
        con.commit()
        return len(updates)
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--db',
        type=Path,
        default=get_hermes_home() / 'autonomy.db',
        help='Path to autonomy.db. Defaults to HERMES_HOME/autonomy.db.',
    )
    args = parser.parse_args()
    updated_count = backfill(args.db)
    print(f'Updated {updated_count} open failing-tests opportunity title(s) in {args.db}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
