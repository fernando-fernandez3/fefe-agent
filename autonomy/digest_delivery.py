"""Telegram-oriented daily digest rendering."""
from __future__ import annotations

from autonomy.models import DailyDigest


def format_digest_for_telegram(digest: DailyDigest) -> str:
    content = digest.content or {}
    lines = [
        f'Daily digest for {digest.date_key}',
        f'Summary: {digest.summary}',
        '',
        _section('Activity', content.get('activity') or ['No notable activity.']),
        _section('Accomplishments', content.get('accomplishments') or ['Nothing shipped yet.']),
        _section('Pending reviews', [f"{item['id']}: {item['title']}" for item in content.get('pending_reviews') or []] or ['No pending reviews.']),
        _section('Top opportunities', [item['title'] for item in content.get('top_opportunities') or []] or ['No open opportunities.']),
        _section('Drift/risks', [item['title'] for item in content.get('drift_risks') or []] or ['No drift detected.']),
        f"Next: {content.get('next_planned_action') or 'No action queued.'}",
    ]
    return '\n'.join(lines).strip()


def _section(title: str, items: list[str]) -> str:
    body = '\n'.join(f'- {item}' for item in items[:3])
    return f'{title}:\n{body}'
