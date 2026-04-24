"""Core autonomy models and lifecycle enums."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GoalStatus(str, Enum):
    ACTIVE = 'active'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class OpportunityStatus(str, Enum):
    OPEN = 'open'
    SUPPRESSED = 'suppressed'
    IN_PROGRESS = 'in_progress'
    REVIEW_REQUIRED = 'review_required'
    COMPLETED = 'completed'
    FAILED = 'failed'


class DelegationMode(str, Enum):
    DIRECT_HERMES = 'direct_hermes'
    HERMES_REVIEW = 'hermes_review'
    AUTOWORKFLOW_RUN = 'autoworkflow_run'


class ExecutionStatus(str, Enum):
    PENDING = 'pending'
    CLAIMED = 'claimed'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class ReviewStatus(str, Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'


@dataclass(slots=True)
class Execution:
    id: str
    domain: str
    executor_type: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    opportunity_id: str | None = None
    plan: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    outcome: dict[str, Any] = field(default_factory=dict)
    started_at: str | None = None
    completed_at: str | None = None
    review_required: bool = False
    lease_owner: str | None = None
    lease_expires_at: str | None = None


@dataclass(slots=True)
class Goal:
    id: str
    title: str
    domain: str
    priority: int
    status: GoalStatus = GoalStatus.ACTIVE
    description: str = ''
    why_it_matters: str = ''
    horizon: str = 'ongoing'
    constraints: dict[str, Any] = field(default_factory=dict)
    success_signals: list[Any] = field(default_factory=list)
    progress_examples: list[Any] = field(default_factory=list)
    review_thresholds: dict[str, Any] = field(default_factory=dict)
    created_at: str = ''
    updated_at: str = ''


@dataclass(slots=True)
class Policy:
    id: str
    domain: str
    trust_level: int
    allowed_actions: list[str]
    approval_required_for: list[str]
    verification_required: bool = True
    max_parallelism: int = 1
    escalation_contacts: list[str] = field(default_factory=list)
    created_at: str = ''
    updated_at: str = ''


@dataclass(slots=True)
class Signal:
    id: str
    domain: str
    source_sensor: str
    entity_type: str
    entity_key: str
    signal_type: str
    signal_strength: float
    evidence: dict[str, Any] = field(default_factory=dict)
    created_at: str = ''


@dataclass(slots=True)
class WorldStateRecord:
    id: str
    domain: str
    entity_type: str
    entity_key: str
    state: dict[str, Any] = field(default_factory=dict)
    freshness_ts: str = ''
    source: str = ''
    updated_at: str = ''


@dataclass(slots=True)
class Opportunity:
    id: str
    domain: str
    source_sensor: str
    title: str
    score: float
    risk_level: str
    confidence: float
    urgency: float
    expected_value: float
    context_cost: float
    status: OpportunityStatus = OpportunityStatus.OPEN
    goal_id: str | None = None
    description: str = ''
    evidence: dict[str, Any] = field(default_factory=dict)
    delegation_mode: DelegationMode = DelegationMode.DIRECT_HERMES
    delegation_target: str | None = None
    desired_outcome: str = ''
    created_at: str = ''
    updated_at: str = ''


@dataclass(slots=True)
class Review:
    id: str
    execution_id: str
    domain: str
    review_type: str
    reason: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: str = ''
    resolved_at: str | None = None


@dataclass(slots=True)
class GoalMatrixEntry:
    id: str
    goal_id: str
    asset_type: str
    label: str
    locator: str
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ''
    updated_at: str = ''


@dataclass(slots=True)
class DailyDigest:
    id: str
    date_key: str
    summary: str
    content: dict[str, Any] = field(default_factory=dict)
    goal_ids: list[str] = field(default_factory=list)
    opportunity_ids: list[str] = field(default_factory=list)
    review_ids: list[str] = field(default_factory=list)
    created_at: str = ''


@dataclass(slots=True)
class Learning:
    id: str
    domain: str
    title: str
    lesson: str
    confidence: float
    actionability: str
    apply_as: str
    execution_id: str | None = None
    created_at: str = ''
