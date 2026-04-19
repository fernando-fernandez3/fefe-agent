"""Policy gating for autonomy MVP."""

from __future__ import annotations

from dataclasses import dataclass, field

from autonomy.models import DelegationMode, Opportunity, Policy


HARD_REVIEW_ACTIONS = {'merge', 'deploy', 'external_messaging', 'trust_promotion', 'policy_mutation', 'autonomy_safety_code_change'}


@dataclass(slots=True)
class PolicyDecision:
    allowed_to_execute: bool
    requires_review: bool
    blocked_reason: str | None = None
    allowed_executor_types: list[str] = field(default_factory=list)


class PolicyEngine:
    def evaluate(self, *, policy: Policy, opportunity: Opportunity, proposed_actions: list[str]) -> PolicyDecision:
        if opportunity.delegation_mode == DelegationMode.HERMES_REVIEW:
            return PolicyDecision(
                allowed_to_execute=False,
                requires_review=True,
                blocked_reason='delegated_to_hermes_review',
                allowed_executor_types=['review_only'],
            )

        if any(action in HARD_REVIEW_ACTIONS for action in proposed_actions):
            return PolicyDecision(
                allowed_to_execute=False,
                requires_review=True,
                blocked_reason='hard_review_action',
                allowed_executor_types=['review_only'],
            )

        if any(action in policy.approval_required_for for action in proposed_actions):
            return PolicyDecision(
                allowed_to_execute=False,
                requires_review=True,
                blocked_reason='policy_requires_review',
                allowed_executor_types=['review_only'],
            )

        disallowed = [action for action in proposed_actions if action not in policy.allowed_actions]
        if disallowed:
            return PolicyDecision(
                allowed_to_execute=False,
                requires_review=False,
                blocked_reason=f'disallowed_actions:{",".join(disallowed)}',
                allowed_executor_types=[],
            )

        allowed_executor_types = self._allowed_executor_types(opportunity=opportunity, proposed_actions=proposed_actions)
        return PolicyDecision(
            allowed_to_execute=bool(allowed_executor_types),
            requires_review=False,
            blocked_reason=None if allowed_executor_types else 'no_executor_available',
            allowed_executor_types=allowed_executor_types,
        )

    def _allowed_executor_types(self, *, opportunity: Opportunity, proposed_actions: list[str]) -> list[str]:
        if opportunity.delegation_mode == DelegationMode.AUTOWORKFLOW_RUN:
            return ['autoworkflow_executor']
        if opportunity.domain != 'code_projects':
            return []
        if proposed_actions and proposed_actions[0] == 'codex_task':
            return ['codex_executor']
        return ['repo_executor']
