"""Goal onboarding helpers for the autonomy MVP."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autonomy.store import AutonomyStore

_TIMEOUT_FALLBACK_SUBSTRINGS = (
    'did not provide a response within the time limit',
    'use your best judgement to make the choice and proceed',
)


@dataclass(slots=True)
class RefinementQuestion:
    key: str
    prompt: str
    choices: list[str]
    kind: str = 'single'


@dataclass(slots=True)
class OnboardResult:
    goal_id: str
    policy_id: str
    domain: str
    title: str
    repo_path: str
    created_goal: bool
    created_policy: bool
    refinement_questions: list[str]
    goal_summary: str
    refinement_answers: dict[str, Any]


class GoalOnboarding:
    def onboard_repo_goal(
        self,
        *,
        store: AutonomyStore,
        repo_path: Path,
        goal_definition: str,
        domain: str = 'code_projects',
        refinement_answers: dict[str, Any] | None = None,
    ) -> OnboardResult:
        normalized_definition = self._normalize_goal_definition(goal_definition, repo_path)
        goal_id = self._goal_id_for_repo(repo_path)
        policy_id = f'policy_{domain}'
        refinement_answers = self._normalize_refinement_answers(refinement_answers)

        created_goal = False
        created_policy = False
        constraints = self._build_constraints(repo_path, refinement_answers)
        success_signals = self._build_success_signals(refinement_answers)
        goal_summary = self.goal_summary(normalized_definition, refinement_answers)
        description = (
            f'Autonomy goal for {repo_path.name}. '
            f'Current onboarding definition: {normalized_definition}. '
            f'{goal_summary}'
        )

        try:
            store.get_goal(goal_id)
            store.update_goal(
                goal_id,
                title=normalized_definition,
                description=description,
                constraints=constraints,
                success_signals=success_signals,
            )
        except KeyError:
            store.create_goal(
                goal_id=goal_id,
                title=normalized_definition,
                description=description,
                domain=domain,
                priority=100,
                constraints=constraints,
                success_signals=success_signals,
            )
            created_goal = True

        try:
            store.get_policy_for_domain(domain)
        except KeyError:
            store.create_policy(
                policy_id=policy_id,
                domain=domain,
                trust_level=1,
                allowed_actions=['inspect_repo'],
                approval_required_for=[],
                verification_required=True,
                max_parallelism=1,
            )
            created_policy = True

        return OnboardResult(
            goal_id=goal_id,
            policy_id=policy_id,
            domain=domain,
            title=normalized_definition,
            repo_path=str(repo_path),
            created_goal=created_goal,
            created_policy=created_policy,
            refinement_questions=[question.prompt for question in self.refinement_questionnaire(normalized_definition)],
            goal_summary=goal_summary,
            refinement_answers=refinement_answers,
        )

    def refinement_questionnaire(self, goal_definition: str) -> list[RefinementQuestion]:
        lowered = goal_definition.lower()
        if not any(keyword in lowered for keyword in ('best', 'grow', 'compared', 'all existing', 'leading', 'win')):
            return []
        return [
            RefinementQuestion(
                key='primary_user_segment',
                prompt='Who exactly is the primary user segment we should optimize for first?',
                choices=[
                    'Travelers with families',
                    'Solo travelers',
                    'Couples',
                    'Business travelers',
                ],
            ),
            RefinementQuestion(
                key='target_competitors',
                prompt='Which competitors or substitutes should Embarka beat first?',
                choices=[
                    'ChatGPT',
                    'Google Travel',
                    'Tripadvisor',
                    'Human travel agents',
                ],
                kind='multi',
            ),
            RefinementQuestion(
                key='success_metrics',
                prompt='Which success metrics matter most right now?',
                choices=[
                    'Activation',
                    'Retention',
                    'Trip completion',
                    'Paid conversion',
                ],
                kind='multi',
            ),
            RefinementQuestion(
                key='autonomy_constraints',
                prompt='What constraints should autonomy respect?',
                choices=[
                    'Brand voice',
                    'Safety',
                    'Budget',
                    'Launch timeline',
                ],
                kind='multi',
            ),
            RefinementQuestion(
                key='initial_wedge',
                prompt='What wedge should Embarka dominate first?',
                choices=[
                    'Itinerary quality',
                    'Family logistics',
                    'Proactive planning',
                    'Collaboration',
                ],
            ),
        ]

    def goal_summary(self, goal_definition: str, refinement_answers: dict[str, Any] | None = None) -> str:
        answers = self._normalize_refinement_answers(refinement_answers)
        if not answers:
            return f'Goal summary: {goal_definition}'

        segment = answers.get('primary_user_segment', 'the chosen user segment')
        competitors = self._join_values(answers.get('target_competitors')) or 'the selected competitors'
        metrics = self._join_values(answers.get('success_metrics')) or 'the selected success metrics'
        wedge = answers.get('initial_wedge', 'the selected product wedge')
        constraints = self._join_values(answers.get('autonomy_constraints')) or 'the selected operating constraints'
        return (
            f'Goal summary: optimize for {segment}, beat {competitors}, '
            f'win on {wedge}, measure success with {metrics}, '
            f'and respect {constraints}.'
        )

    def _build_constraints(self, repo_path: Path, refinement_answers: dict[str, Any]) -> dict[str, Any]:
        constraints: dict[str, Any] = {
            'repo_path': str(repo_path),
            'mode': 'read_only',
        }
        if refinement_answers:
            constraints['onboarding_answers'] = refinement_answers
            constraints.update(refinement_answers)
        return constraints

    def _build_success_signals(self, refinement_answers: dict[str, Any]) -> list[str]:
        signals = ['safe_repo_inspection', 'verification_evidence', 'useful_learning']
        for metric in refinement_answers.get('success_metrics', []):
            slug = re.sub(r'[^a-z0-9]+', '_', str(metric).lower()).strip('_')
            if slug:
                signals.append(f'success_metric:{slug}')
        return signals

    def _normalize_refinement_answers(self, refinement_answers: dict[str, Any] | None) -> dict[str, Any]:
        if not refinement_answers:
            return {}

        normalized: dict[str, Any] = {}
        for key, value in refinement_answers.items():
            if value is None:
                continue
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned and not self.is_placeholder_response(cleaned):
                    normalized[key] = cleaned
                continue
            if isinstance(value, list):
                cleaned_items = [
                    str(item).strip()
                    for item in value
                    if str(item).strip() and not self.is_placeholder_response(str(item).strip())
                ]
                if cleaned_items:
                    normalized[key] = cleaned_items
                continue
            normalized[key] = value
        return normalized

    def is_placeholder_response(self, value: str) -> bool:
        lowered = value.strip().lower()
        if not lowered:
            return True
        return any(fragment in lowered for fragment in _TIMEOUT_FALLBACK_SUBSTRINGS)

    def _join_values(self, value: Any) -> str:
        if isinstance(value, list):
            return ', '.join(str(item) for item in value if str(item).strip())
        if isinstance(value, str):
            return value.strip()
        return ''

    def _normalize_goal_definition(self, goal_definition: str, repo_path: Path) -> str:
        cleaned = ' '.join(goal_definition.strip().split())
        if cleaned:
            return cleaned
        return f'Continuously improve {repo_path.name} repo health and reduce manual maintenance drag.'

    def _goal_id_for_repo(self, repo_path: Path) -> str:
        slug = re.sub(r'[^a-z0-9]+', '_', repo_path.name.lower()).strip('_') or 'repo'
        return f'goal_{slug}_health'
