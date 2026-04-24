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

        summary: list[str] = []
        signal_type = evidence.get('signal_type')
        if signal_type:
            summary.append(f'signal: {signal_type}')

        signal_evidence = evidence.get('signal_evidence', {})
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
