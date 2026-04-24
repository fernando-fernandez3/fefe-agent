"""Structured learning extraction for autonomy MVP executions."""

from __future__ import annotations

from uuid import uuid4

from autonomy.models import Execution, ExecutionStatus, Learning, Opportunity
from autonomy.store import AutonomyStore


class LearningEngine:
    def extract_and_persist(self, *, store: AutonomyStore, execution: Execution, opportunity: Opportunity) -> Learning:
        title, lesson, confidence, actionability, apply_as = self._build_learning(execution=execution, opportunity=opportunity)
        if apply_as == 'trust_promotion':
            raise ValueError('Autonomous trust promotion is forbidden')
        return store.create_learning(
            learning_id=f'learning_{uuid4().hex}',
            domain=execution.domain,
            execution_id=execution.id,
            title=title,
            lesson=lesson,
            confidence=confidence,
            actionability=actionability,
            apply_as=apply_as,
        )

    def _build_learning(self, *, execution: Execution, opportunity: Opportunity) -> tuple[str, str, float, str, str]:
        if execution.status == ExecutionStatus.COMPLETED:
            return (
                'Read-only repo inspection succeeded',
                f'Opportunity "{opportunity.title}" completed with verification evidence attached.',
                0.8,
                'reuse_readonly_repo_inspection',
                'workflow_note',
            )
        return (
            'Repo inspection failed safely',
            f'Opportunity "{opportunity.title}" failed without widening side effects and should be investigated before retry.',
            0.7,
            'tighten_preconditions_before_retry',
            'guardrail_note',
        )
