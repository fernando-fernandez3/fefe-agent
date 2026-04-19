"""Opportunity generation for repo autonomy MVP."""

from __future__ import annotations

from autonomy.models import DelegationMode, Opportunity, Signal
from autonomy.store import AutonomyStore


class OpportunityEngine:
    def score_signal(self, signal: Signal) -> tuple[float, float, float, float, float, str, str]:
        if signal.signal_type == 'failing_tests':
            confidence = 0.9
            urgency = 0.85
            expected_value = 0.9
            context_cost = 0.2
            title = 'Investigate failing test slice'
            risk_level = 'low'
        elif signal.signal_type == 'dirty_worktree':
            confidence = 0.85
            urgency = 0.65
            expected_value = 0.6
            context_cost = 0.25
            title = 'Inspect dirty repo state'
            risk_level = 'low'
        elif signal.signal_type == 'stale_branch':
            confidence = 0.8
            urgency = 0.55
            expected_value = 0.55
            context_cost = 0.3
            title = 'Review stale branch and decide next action'
            risk_level = 'low'
        else:
            confidence = min(1.0, signal.signal_strength)
            urgency = min(1.0, signal.signal_strength)
            expected_value = 0.5
            context_cost = 0.3
            title = f'Inspect signal: {signal.signal_type}'
            risk_level = 'low'

        score = round(
            (confidence * 0.3)
            + (urgency * 0.3)
            + (expected_value * 0.3)
            - (context_cost * 0.1),
            4,
        )
        return score, confidence, urgency, expected_value, context_cost, risk_level, title

    def routing_for_signal(self, signal: Signal) -> tuple[DelegationMode, str | None, str]:
        if signal.signal_type in {'deploy_candidate', 'external_message_needed'}:
            return DelegationMode.HERMES_REVIEW, None, f'Review and approve action for {signal.signal_type}.'
        if signal.signal_type in {'competitor_gap', 'feedback_batch', 'research_digest'}:
            return DelegationMode.AUTOWORKFLOW_RUN, signal.signal_type, f'Run the repeatable workflow for {signal.signal_type}.'
        return DelegationMode.DIRECT_HERMES, None, f'Handle {signal.signal_type} directly in Hermes.'

    def upsert_from_signal(self, store: AutonomyStore, signal: Signal) -> Opportunity:
        score, confidence, urgency, expected_value, context_cost, risk_level, title = self.score_signal(signal)
        delegation_mode, delegation_target, desired_outcome = self.routing_for_signal(signal)
        return store.upsert_opportunity(
            opportunity_id=f'opp::{signal.domain}::{signal.signal_type}::{signal.entity_key}',
            domain=signal.domain,
            source_sensor=signal.source_sensor,
            title=title,
            score=score,
            risk_level=risk_level,
            confidence=confidence,
            urgency=urgency,
            expected_value=expected_value,
            context_cost=context_cost,
            description=f'Generated from signal {signal.signal_type} on {signal.entity_key}',
            evidence={'signal_id': signal.id, 'signal_type': signal.signal_type, 'signal_evidence': signal.evidence},
            delegation_mode=delegation_mode,
            delegation_target=delegation_target,
            desired_outcome=desired_outcome,
        )
