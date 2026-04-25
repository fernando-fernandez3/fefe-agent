"""Telegram-friendly review packet formatting for autonomy reviews."""

from __future__ import annotations

from dataclasses import dataclass

from autonomy.models import Execution, Opportunity, Review


@dataclass(slots=True)
class ReviewPacket:
    title: str
    summary: str
    proposed_action: str
    needs_review_reason: str
    approval_effect: str
    evidence_summary: list[str]

    def as_text(self) -> str:
        evidence_block = '\n'.join(f'- {item}' for item in self.evidence_summary) if self.evidence_summary else '- no evidence attached'
        return (
            f'{self.title}\n'
            f'{self.summary}\n\n'
            f'Proposed action: {self.proposed_action}\n'
            f'Needs review: {self.needs_review_reason}\n'
            f'If approved: {self.approval_effect}\n'
            f'Evidence:\n{evidence_block}'
        )


class ReviewPacketFormatter:
    def format(self, *, review: Review, execution: Execution, opportunity: Opportunity | None = None) -> ReviewPacket:
        proposed_actions = execution.plan.get('proposed_actions', [])
        primary_action = proposed_actions[0] if proposed_actions else execution.plan.get('action', 'unknown_action')
        opportunity_title = opportunity.title if opportunity is not None else review.payload.get('title', 'Autonomy review request')
        evidence = review.payload.get('evidence', {})

        return ReviewPacket(
            title=f'Review required: {opportunity_title}',
            summary=f'Selected from the autonomy queue for domain {review.domain}.',
            proposed_action=primary_action,
            needs_review_reason=review.reason,
            approval_effect=self._approval_effect(execution=execution, primary_action=primary_action),
            evidence_summary=self._summarize_evidence(evidence),
        )

    def _approval_effect(self, *, execution: Execution, primary_action: str) -> str:
        if primary_action == 'codex_task':
            repo_path = execution.plan.get('repo_path') or 'the target repo'
            prompt_summary = execution.plan.get('codex_prompt_summary') or execution.plan.get('prompt_summary')
            if prompt_summary:
                return (
                    f'Execution {execution.id} will run Codex inside {repo_path} '
                    f'to: {prompt_summary}'
                )
            return f'Execution {execution.id} will run Codex inside {repo_path}.'

        return f'Execution {execution.id} will proceed with {primary_action}.'

    def _summarize_evidence(self, evidence: dict) -> list[str]:
        if not evidence:
            return []

        def _join_values(values: object) -> str | None:
            if isinstance(values, list):
                return ', '.join(str(value) for value in values if value)
            if isinstance(values, dict):
                return ', '.join(str(value) for value in values.values() if value)
            if values:
                return str(values)
            return None

        summary: list[str] = []
        signal_type = evidence.get('signal_type')
        if signal_type:
            summary.append(f'signal: {signal_type}')

        signal_evidence = evidence.get('signal_evidence', {})
        matches = signal_evidence.get('matches') or []
        first_match = matches[0] if matches and isinstance(matches[0], dict) else {}

        artifact_paths = signal_evidence.get('artifact_paths') or []
        artifact_path_fallback = None
        if isinstance(artifact_paths, dict):
            artifact_path_fallback = next((str(value) for value in artifact_paths.values() if value), None)
        elif isinstance(artifact_paths, list):
            artifact_path_fallback = str(artifact_paths[0]) if artifact_paths else None
        elif artifact_paths:
            artifact_path_fallback = str(artifact_paths)
        artifact_source = first_match.get('source_path') or artifact_path_fallback
        if artifact_source:
            source_details = []
            source_type = first_match.get('source_type')
            if source_type:
                source_details.append(str(source_type))
            title = first_match.get('title')
            if title:
                source_details.append(str(title))
            detail_text = f" ({'; '.join(source_details)})" if source_details else ''
            summary.append(f'artifact source file: {artifact_source}{detail_text}')

        candidate_keys = _join_values(signal_evidence.get('candidate_keys') or first_match.get('candidate_key'))
        if candidate_keys:
            summary.append(f'candidate keys: {candidate_keys}')

        canonical_keys = _join_values(signal_evidence.get('canonical_keys') or first_match.get('canonical_key'))
        if canonical_keys:
            summary.append(f'canonical keys: {canonical_keys}')

        matched_keys = _join_values(first_match.get('matched_keys'))
        if matched_keys:
            summary.append(f'matched keys: {matched_keys}')

        matched_keywords = _join_values(first_match.get('matched_keywords'))
        if matched_keywords:
            summary.append(f'matched keywords: {matched_keywords}')

        snippet = first_match.get('snippet')
        if snippet:
            summary.append(f'snippet: {snippet}')

        suggested_actions = {
            'feedback_mobile_usability_gap': 'review mobile usability feedback and close the mapped artifact gap.',
            'feedback_trip_output_trust_gap': 'review trip-output trust evidence and decide the smallest confidence-building fix.',
            'feedback_itinerary_editing_gap': 'review itinerary editing evidence and decide whether version/history UX needs work.',
            'feedback_family_profile_capture_gap': 'review family-profile evidence and decide what context Embarka should capture earlier.',
            'feedback_booking_readiness_gap': 'review booking readiness evidence and decide what conversion blocker to remove.',
            'feedback_family_logistics_gap': 'review family logistics evidence and decide what family constraint support is missing.',
            'feedback_trip_memory_gap': 'review trip memory evidence and decide what preference persistence is needed.',
            'feedback_collaboration_gap': 'review collaboration evidence and decide what shared-planning affordance is missing.',
            'feedback_booking_confidence_gap': 'review booking confidence evidence and decide what proof or handoff would increase trust.',
            'competitor_collaboration_feature_threat': 'review competitor collaboration evidence and decide whether Embarka needs a response.',
            'competitor_budget_visibility_threat': 'review competitor budget evidence and decide whether budget visibility belongs on the roadmap.',
            'competitor_trip_change_management_threat': 'review competitor change-management evidence and decide whether itinerary revision support needs work.',
        }
        suggested_action = suggested_actions.get(signal_type)
        if suggested_action:
            summary.append(f'suggested action: {suggested_action}')

        changed_count = signal_evidence.get('changed_count')
        if changed_count is not None:
            summary.append(f'changed files: {changed_count}')

        branch = signal_evidence.get('branch')
        if branch:
            summary.append(f'branch: {branch}')

        age_seconds = signal_evidence.get('age_seconds')
        if age_seconds is not None:
            summary.append(f'age_seconds: {age_seconds}')

        if not summary:
            summary.append(str(evidence))
        return summary
