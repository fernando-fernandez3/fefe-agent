"""Opportunity generation for repo autonomy MVP."""

from __future__ import annotations

from autonomy.models import DelegationMode, Opportunity, Signal
from autonomy.store import AutonomyStore


class OpportunityEngine:
    IGNORE_SIGNAL_TYPES = {
        'doc_recently_modified',
        'system_present',
        'workflows_running',
        'site_healthy',
    }

    def score_signal(self, signal: Signal) -> tuple[float, float, float, float, float, str, str]:
        asset_label = str((signal.evidence or {}).get('asset_label') or signal.entity_key)
        subdomain = str((signal.evidence or {}).get('subdomain') or '').replace('_', ' ').strip()
        subdomain_prefix = f'{subdomain}: ' if subdomain else ''

        if signal.signal_type == 'failing_tests':
            confidence = 0.9
            urgency = 0.85
            expected_value = 0.9
            context_cost = 0.2
            title = 'Investigate failing test slice'
            risk_level = 'low'
        elif signal.signal_type == 'workflows_failed':
            confidence = 0.9
            urgency = 0.8
            expected_value = 0.8
            context_cost = 0.2
            title = f'{subdomain_prefix}Investigate failed workflow: {asset_label}'
            risk_level = 'medium'
        elif signal.signal_type == 'workflows_pending_review':
            confidence = 0.85
            urgency = 0.7
            expected_value = 0.75
            context_cost = 0.15
            title = f'{subdomain_prefix}Review pending workflow items: {asset_label}'
            risk_level = 'low'
        elif signal.signal_type == 'site_down':
            confidence = 0.95
            urgency = 0.95
            expected_value = 0.9
            context_cost = 0.1
            title = f'{subdomain_prefix}Investigate live-site outage: {asset_label}'
            risk_level = 'high'
        elif signal.signal_type == 'site_degraded':
            confidence = 0.9
            urgency = 0.75
            expected_value = 0.75
            context_cost = 0.15
            title = f'{subdomain_prefix}Investigate degraded live-site response: {asset_label}'
            risk_level = 'medium'
        elif signal.signal_type == 'missing_asset':
            confidence = 0.9
            urgency = 0.65
            expected_value = 0.6
            context_cost = 0.15
            title = f'{subdomain_prefix}Missing tracked asset: {asset_label}'
            risk_level = 'medium'
        elif signal.signal_type == 'doc_stale':
            confidence = 0.75
            urgency = 0.45
            expected_value = 0.45
            context_cost = 0.2
            title = f'{subdomain_prefix}Refresh stale goal asset: {asset_label}'
            risk_level = 'low'
        elif signal.signal_type == 'doc_very_stale':
            confidence = 0.8
            urgency = 0.6
            expected_value = 0.55
            context_cost = 0.2
            title = f'{subdomain_prefix}Refresh very stale goal asset: {asset_label}'
            risk_level = 'low'
        elif signal.signal_type == 'system_missing':
            confidence = 0.85
            urgency = 0.7
            expected_value = 0.65
            context_cost = 0.15
            title = f'{subdomain_prefix}Investigate missing system asset: {asset_label}'
            risk_level = 'medium'
        elif signal.signal_type == 'feedback_onboarding_friction':
            confidence = 0.85
            urgency = 0.8
            expected_value = 0.85
            context_cost = 0.2
            title = f'{subdomain_prefix}Address onboarding friction from live feedback'
            risk_level = 'medium'
        elif signal.signal_type == 'feedback_family_constraint_gap':
            confidence = 0.85
            urgency = 0.75
            expected_value = 0.9
            context_cost = 0.2
            title = f'{subdomain_prefix}Close family-constraint gap from live feedback'
            risk_level = 'medium'
        elif signal.signal_type == 'competitor_family_feature_threat':
            confidence = 0.9
            urgency = 0.85
            expected_value = 0.9
            context_cost = 0.2
            title = f'{subdomain_prefix}Respond to competitor family-feature threat'
            risk_level = 'high'
        elif signal.signal_type == 'competitor_positioning_shift':
            confidence = 0.85
            urgency = 0.7
            expected_value = 0.8
            context_cost = 0.2
            title = f'{subdomain_prefix}Review competitor positioning shift'
            risk_level = 'medium'
        elif signal.signal_type == 'feedback_mobile_usability_gap':
            confidence = 0.85
            urgency = 0.8
            expected_value = 0.85
            context_cost = 0.2
            title = f'{subdomain_prefix}Fix mobile usability gap from feedback artifacts'
            risk_level = 'medium'
        elif signal.signal_type == 'feedback_trip_output_trust_gap':
            confidence = 0.9
            urgency = 0.85
            expected_value = 0.9
            context_cost = 0.2
            title = f'{subdomain_prefix}Improve trip-output trust from feedback artifacts'
            risk_level = 'high'
        elif signal.signal_type == 'competitor_collaboration_feature_threat':
            confidence = 0.9
            urgency = 0.8
            expected_value = 0.9
            context_cost = 0.2
            title = f'{subdomain_prefix}Respond to competitor collaboration threat'
            risk_level = 'high'
        elif signal.signal_type == 'competitor_budget_visibility_threat':
            confidence = 0.85
            urgency = 0.75
            expected_value = 0.85
            context_cost = 0.2
            title = f'{subdomain_prefix}Respond to competitor budget-visibility threat'
            risk_level = 'high'
        elif signal.signal_type == 'feedback_itinerary_editing_gap':
            confidence = 0.85
            urgency = 0.78
            expected_value = 0.85
            context_cost = 0.2
            title = f'{subdomain_prefix}Improve itinerary editing from feedback artifacts'
            risk_level = 'medium'
        elif signal.signal_type == 'feedback_family_profile_capture_gap':
            confidence = 0.84
            urgency = 0.74
            expected_value = 0.88
            context_cost = 0.2
            title = f'{subdomain_prefix}Improve family-profile capture from feedback artifacts'
            risk_level = 'medium'
        elif signal.signal_type == 'feedback_booking_readiness_gap':
            confidence = 0.88
            urgency = 0.8
            expected_value = 0.9
            context_cost = 0.2
            title = f'{subdomain_prefix}Improve booking readiness from feedback artifacts'
            risk_level = 'high'
        elif signal.signal_type == 'competitor_trip_change_management_threat':
            confidence = 0.88
            urgency = 0.8
            expected_value = 0.88
            context_cost = 0.2
            title = f'{subdomain_prefix}Respond to competitor trip-change-management threat'
            risk_level = 'high'
        elif signal.signal_type == 'feedback_family_logistics_gap':
            confidence = 0.87
            urgency = 0.8
            expected_value = 0.9
            context_cost = 0.2
            title = f'{subdomain_prefix}Close family logistics gap from structured feedback'
            risk_level = 'high'
        elif signal.signal_type == 'feedback_trip_memory_gap':
            confidence = 0.8
            urgency = 0.68
            expected_value = 0.78
            context_cost = 0.2
            title = f'{subdomain_prefix}Improve trip memory from structured feedback'
            risk_level = 'medium'
        elif signal.signal_type == 'feedback_collaboration_gap':
            confidence = 0.85
            urgency = 0.76
            expected_value = 0.86
            context_cost = 0.2
            title = f'{subdomain_prefix}Close collaboration gap from structured feedback'
            risk_level = 'medium'
        elif signal.signal_type == 'feedback_booking_confidence_gap':
            confidence = 0.88
            urgency = 0.8
            expected_value = 0.88
            context_cost = 0.2
            title = f'{subdomain_prefix}Improve booking confidence from structured feedback'
            risk_level = 'high'
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
        elif signal.signal_type == 'no_tests_configured':
            # Informational only — repo has no test suite wired up. This is a
            # configuration state, not a bug to fix. Keep score low so it sits
            # below any real signal and doesn't consume an action slot.
            confidence = 0.7
            urgency = 0.2
            expected_value = 0.25
            context_cost = 0.35
            title = 'Repo has no tests configured'
            risk_level = 'low'
        else:
            confidence = min(1.0, signal.signal_strength)
            urgency = min(1.0, signal.signal_strength)
            expected_value = 0.5
            context_cost = 0.3
            title = f'{subdomain_prefix}Inspect signal: {signal.signal_type}'
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
        if signal.signal_type in {
            'workflows_failed',
            'workflows_pending_review',
            'site_down',
            'site_degraded',
            'missing_asset',
            'doc_stale',
            'doc_very_stale',
            'system_missing',
            'feedback_onboarding_friction',
            'feedback_family_constraint_gap',
            'competitor_family_feature_threat',
            'competitor_positioning_shift',
            'feedback_mobile_usability_gap',
            'feedback_trip_output_trust_gap',
            'competitor_collaboration_feature_threat',
            'competitor_budget_visibility_threat',
            'feedback_itinerary_editing_gap',
            'feedback_family_profile_capture_gap',
            'feedback_booking_readiness_gap',
            'competitor_trip_change_management_threat',
            'feedback_family_logistics_gap',
            'feedback_trip_memory_gap',
            'feedback_collaboration_gap',
            'feedback_booking_confidence_gap',
        }:
            return DelegationMode.HERMES_REVIEW, None, f'Review and decide next action for {signal.signal_type}.'
        if signal.signal_type in {'competitor_gap', 'feedback_batch', 'research_digest'}:
            return DelegationMode.AUTOWORKFLOW_RUN, signal.signal_type, f'Run the repeatable workflow for {signal.signal_type}.'
        return DelegationMode.DIRECT_HERMES, None, f'Handle {signal.signal_type} directly in Hermes.'

    def upsert_from_signal(self, store: AutonomyStore, signal: Signal) -> Opportunity | None:
        if signal.signal_type in self.IGNORE_SIGNAL_TYPES:
            return None
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
            evidence={
                'signal_id': signal.id,
                'signal_type': signal.signal_type,
                'signal_evidence': signal.evidence,
                'entity_type': signal.entity_type,
                'entity_key': signal.entity_key,
                'matrix_entry_id': (signal.evidence or {}).get('matrix_entry_id'),
                'asset_type': (signal.evidence or {}).get('asset_type'),
                'asset_label': (signal.evidence or {}).get('asset_label'),
                'locator': (signal.evidence or {}).get('locator'),
                'asset_metadata': (signal.evidence or {}).get('asset_metadata'),
                'subdomain': (signal.evidence or {}).get('subdomain'),
            },
            delegation_mode=delegation_mode,
            delegation_target=delegation_target,
            desired_outcome=desired_outcome,
        )
