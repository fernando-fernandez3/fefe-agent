"""Daily digest generation across all active desired states."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import uuid4

from autonomy.models import DailyDigest, GoalStatus, OpportunityStatus


class DigestGenerator:
    def __init__(self, *, store, now_fn: Callable[[], datetime] | None = None):
        self.store = store
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def generate(self) -> DailyDigest:
        now = self.now_fn()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        now = now.astimezone()
        date_key = now.date().isoformat()
        try:
            return self.store.get_daily_digest(date_key)
        except KeyError:
            pass

        goals = self.store.list_goals(status=GoalStatus.ACTIVE)
        all_evidence = []
        goal_ids = [goal.id for goal in goals]
        window_start = now - timedelta(hours=24)
        drift_cutoff = now - timedelta(days=7)

        for goal in goals:
            all_evidence.extend(self.store.list_evidence_by_goal(goal.id))

        recent_evidence = [e for e in all_evidence if self._parse_ts(e.recorded_at) >= window_start]
        pending_reviews = self.store.list_pending_reviews()
        top_opportunities = self.store.list_opportunities(status=OpportunityStatus.OPEN)[:3]

        activity = [
            f"{goal.title} had activity in the last 24h."
            for goal in goals
            if any(e.goal_id == goal.id for e in recent_evidence)
        ]
        accomplishments = [e.impact_summary for e in recent_evidence if e.outcome == 'success']
        drift_risks = []
        for goal in goals:
            evidence = self.store.list_evidence_by_goal(goal.id)
            latest = max((self._parse_ts(item.recorded_at) for item in evidence), default=None)
            created_at = self._parse_ts(goal.created_at) if goal.created_at else None
            reference = latest or created_at
            if reference is not None and reference <= drift_cutoff:
                drift_risks.append({
                    'goal_id': goal.id,
                    'title': goal.title,
                    'reason': 'No evidence recorded in 7+ days.',
                })

        pending_review_cards = [
            {'id': review.id, 'title': review.payload.get('title') or review.reason}
            for review in pending_reviews
        ]
        opportunity_cards = [
            {'id': opportunity.id, 'title': opportunity.title, 'desired_outcome': opportunity.desired_outcome}
            for opportunity in top_opportunities
        ]
        next_planned_action = (
            top_opportunities[0].desired_outcome or top_opportunities[0].title
            if top_opportunities
            else 'No action queued.'
        )
        summary = 'All quiet across active desired states.' if not recent_evidence and not pending_reviews else self._build_summary(accomplishments, pending_reviews, top_opportunities)

        return self.store.create_daily_digest(
            digest_id=f'digest_{uuid4().hex}',
            date_key=date_key,
            summary=summary,
            content={
                'activity': activity,
                'accomplishments': accomplishments,
                'pending_reviews': pending_review_cards,
                'top_opportunities': opportunity_cards,
                'drift_risks': drift_risks,
                'next_planned_action': next_planned_action,
            },
            goal_ids=goal_ids,
            opportunity_ids=[item.id for item in top_opportunities],
            review_ids=[item.id for item in pending_reviews],
        )

    @staticmethod
    def _build_summary(accomplishments: list[str], pending_reviews: list, top_opportunities: list) -> str:
        parts = []
        if accomplishments:
            parts.append(f'{len(accomplishments)} accomplishment(s) recorded')
        if pending_reviews:
            parts.append(f'{len(pending_reviews)} review(s) pending')
        if top_opportunities:
            parts.append(f'{len(top_opportunities)} top opportunity(ies) queued')
        return '. '.join(parts) + '.' if parts else 'All quiet across active desired states.'

    @staticmethod
    def _parse_ts(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone()
