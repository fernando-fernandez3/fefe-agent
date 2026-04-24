"""Evidence ingestion helpers for autonomy executions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Evidence:
    id: str
    opportunity_id: str
    goal_id: str
    source: str
    executor_run_id: str
    outcome: str
    artifacts: dict[str, Any]
    impact_summary: str
    recorded_at: str


def record_evidence(store, evidence: Evidence) -> Evidence:
    return store.create_evidence(
        evidence_id=evidence.id,
        opportunity_id=evidence.opportunity_id,
        goal_id=evidence.goal_id,
        source=evidence.source,
        executor_run_id=evidence.executor_run_id,
        outcome=evidence.outcome,
        artifacts=evidence.artifacts,
        impact_summary=evidence.impact_summary,
        recorded_at=evidence.recorded_at,
    )


def list_evidence_for_goal(store, goal_id: str) -> list[Evidence]:
    return store.list_evidence_by_goal(goal_id)


def list_evidence_for_opportunity(store, opportunity_id: str) -> list[Evidence]:
    return store.list_evidence_by_opportunity(opportunity_id)
