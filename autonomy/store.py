"""Storage APIs for autonomy MVP."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .db import AutonomyDB
from .models import DailyDigest, DelegationMode, Execution, ExecutionStatus, Goal, GoalMatrixEntry, GoalStatus, Learning, Opportunity, OpportunityStatus, Policy, Review, ReviewStatus, Signal, WorldStateRecord


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AutonomyStore:
    def __init__(self, db_path: Path | None = None):
        self.db = AutonomyDB(db_path=db_path)

    def close(self) -> None:
        self.db.close()

    def create_goal(
        self,
        *,
        goal_id: str,
        title: str,
        domain: str,
        priority: int,
        description: str = '',
        horizon: str = 'ongoing',
        status: GoalStatus = GoalStatus.ACTIVE,
        constraints: dict | None = None,
        success_signals: list | None = None,
        why_it_matters: str = '',
        progress_examples: list | None = None,
        review_thresholds: dict | None = None,
    ) -> Goal:
        now = utc_now_iso()
        constraints = constraints or {}
        success_signals = success_signals or []
        progress_examples = progress_examples or []
        review_thresholds = review_thresholds or {}
        self.db.execute(
            """
            INSERT INTO goals (
                id, title, description, domain, priority, status, horizon,
                constraints_json, success_signals_json, why_it_matters,
                progress_examples_json, review_thresholds_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                goal_id,
                title,
                description,
                domain,
                priority,
                status.value,
                horizon,
                json.dumps(constraints),
                json.dumps(success_signals),
                why_it_matters,
                json.dumps(progress_examples),
                json.dumps(review_thresholds),
                now,
                now,
            ),
        )
        return self.get_goal(goal_id)

    def get_goal(self, goal_id: str) -> Goal:
        row = self.db.fetchone('SELECT * FROM goals WHERE id = ?', (goal_id,))
        if row is None:
            raise KeyError(f'Goal not found: {goal_id}')
        return Goal(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            domain=row['domain'],
            priority=row['priority'],
            status=GoalStatus(row['status']),
            why_it_matters=row['why_it_matters'],
            horizon=row['horizon'],
            constraints=json.loads(row['constraints_json']),
            success_signals=json.loads(row['success_signals_json']),
            progress_examples=json.loads(row['progress_examples_json']),
            review_thresholds=json.loads(row['review_thresholds_json']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    def list_goals(self, status: GoalStatus | None = None, domain: str | None = None) -> list[Goal]:
        sql = 'SELECT id FROM goals WHERE 1=1'
        params: list = []
        if status is not None:
            sql += ' AND status = ?'
            params.append(status.value)
        if domain is not None:
            sql += ' AND domain = ?'
            params.append(domain)
        sql += ' ORDER BY priority DESC, created_at ASC'
        rows = self.db.fetchall(sql, tuple(params))
        return [self.get_goal(row['id']) for row in rows]

    def update_goal_status(self, goal_id: str, status: GoalStatus) -> Goal:
        now = utc_now_iso()
        self.db.execute(
            'UPDATE goals SET status = ?, updated_at = ? WHERE id = ?',
            (status.value, now, goal_id),
        )
        return self.get_goal(goal_id)

    def update_goal(
        self,
        goal_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        priority: int | None = None,
        horizon: str | None = None,
        constraints: dict | None = None,
        success_signals: list | None = None,
        why_it_matters: str | None = None,
        progress_examples: list | None = None,
        review_thresholds: dict | None = None,
    ) -> Goal:
        current = self.get_goal(goal_id)
        now = utc_now_iso()
        self.db.execute(
            """
            UPDATE goals
            SET title = ?,
                description = ?,
                priority = ?,
                horizon = ?,
                constraints_json = ?,
                success_signals_json = ?,
                why_it_matters = ?,
                progress_examples_json = ?,
                review_thresholds_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                current.title if title is None else title,
                current.description if description is None else description,
                current.priority if priority is None else priority,
                current.horizon if horizon is None else horizon,
                json.dumps(current.constraints if constraints is None else constraints),
                json.dumps(current.success_signals if success_signals is None else success_signals),
                current.why_it_matters if why_it_matters is None else why_it_matters,
                json.dumps(current.progress_examples if progress_examples is None else progress_examples),
                json.dumps(current.review_thresholds if review_thresholds is None else review_thresholds),
                now,
                goal_id,
            ),
        )
        return self.get_goal(goal_id)

    def add_goal_matrix_entry(
        self,
        *,
        entry_id: str,
        goal_id: str,
        asset_type: str,
        label: str,
        locator: str,
        weight: float = 1.0,
        metadata: dict | None = None,
    ) -> GoalMatrixEntry:
        now = utc_now_iso()
        metadata = metadata or {}
        self.db.execute(
            """
            INSERT INTO goal_matrix_entries (
                id, goal_id, asset_type, label, locator, weight,
                metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id,
                goal_id,
                asset_type,
                label,
                locator,
                weight,
                json.dumps(metadata),
                now,
                now,
            ),
        )
        return self.get_goal_matrix_entry(entry_id)

    def get_goal_matrix_entry(self, entry_id: str) -> GoalMatrixEntry:
        row = self.db.fetchone('SELECT * FROM goal_matrix_entries WHERE id = ?', (entry_id,))
        if row is None:
            raise KeyError(f'Goal matrix entry not found: {entry_id}')
        return GoalMatrixEntry(
            id=row['id'],
            goal_id=row['goal_id'],
            asset_type=row['asset_type'],
            label=row['label'],
            locator=row['locator'],
            weight=row['weight'],
            metadata=json.loads(row['metadata_json']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    def list_goal_matrix_entries(self, *, goal_id: str | None = None) -> list[GoalMatrixEntry]:
        sql = 'SELECT id FROM goal_matrix_entries WHERE 1=1'
        params: list = []
        if goal_id is not None:
            sql += ' AND goal_id = ?'
            params.append(goal_id)
        sql += ' ORDER BY weight DESC, created_at ASC, id ASC'
        rows = self.db.fetchall(sql, tuple(params))
        return [self.get_goal_matrix_entry(row['id']) for row in rows]

    def update_goal_matrix_entry(
        self,
        entry_id: str,
        *,
        asset_type: str | None = None,
        label: str | None = None,
        locator: str | None = None,
        weight: float | None = None,
        metadata: dict | None = None,
    ) -> GoalMatrixEntry:
        current = self.get_goal_matrix_entry(entry_id)
        now = utc_now_iso()
        self.db.execute(
            """
            UPDATE goal_matrix_entries
            SET asset_type = ?,
                label = ?,
                locator = ?,
                weight = ?,
                metadata_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                current.asset_type if asset_type is None else asset_type,
                current.label if label is None else label,
                current.locator if locator is None else locator,
                current.weight if weight is None else weight,
                json.dumps(current.metadata if metadata is None else metadata),
                now,
                entry_id,
            ),
        )
        return self.get_goal_matrix_entry(entry_id)

    def remove_goal_matrix_entry(self, entry_id: str) -> None:
        self.db.execute('DELETE FROM goal_matrix_entries WHERE id = ?', (entry_id,))

    def create_policy(
        self,
        *,
        policy_id: str,
        domain: str,
        trust_level: int,
        allowed_actions: list[str],
        approval_required_for: list[str],
        verification_required: bool = True,
        max_parallelism: int = 1,
        escalation_contacts: list[str] | None = None,
    ) -> Policy:
        now = utc_now_iso()
        escalation_contacts = escalation_contacts or []
        self.db.execute(
            """
            INSERT INTO policies (
                id, domain, trust_level, allowed_actions_json,
                approval_required_for_json, verification_required,
                max_parallelism, escalation_contacts_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                policy_id,
                domain,
                trust_level,
                json.dumps(allowed_actions),
                json.dumps(approval_required_for),
                1 if verification_required else 0,
                max_parallelism,
                json.dumps(escalation_contacts),
                now,
                now,
            ),
        )
        return self.get_policy_for_domain(domain)

    def get_policy_for_domain(self, domain: str) -> Policy:
        row = self.db.fetchone('SELECT * FROM policies WHERE domain = ?', (domain,))
        if row is None:
            raise KeyError(f'Policy not found for domain: {domain}')
        return Policy(
            id=row['id'],
            domain=row['domain'],
            trust_level=row['trust_level'],
            allowed_actions=json.loads(row['allowed_actions_json']),
            approval_required_for=json.loads(row['approval_required_for_json']),
            verification_required=bool(row['verification_required']),
            max_parallelism=row['max_parallelism'],
            escalation_contacts=json.loads(row['escalation_contacts_json']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    def update_policy(
        self,
        domain: str,
        *,
        trust_level: int | None = None,
        allowed_actions: list[str] | None = None,
        approval_required_for: list[str] | None = None,
        verification_required: bool | None = None,
        max_parallelism: int | None = None,
        escalation_contacts: list[str] | None = None,
    ) -> Policy:
        current = self.get_policy_for_domain(domain)
        now = utc_now_iso()
        self.db.execute(
            """
            UPDATE policies
            SET trust_level = ?,
                allowed_actions_json = ?,
                approval_required_for_json = ?,
                verification_required = ?,
                max_parallelism = ?,
                escalation_contacts_json = ?,
                updated_at = ?
            WHERE domain = ?
            """,
            (
                current.trust_level if trust_level is None else trust_level,
                json.dumps(current.allowed_actions if allowed_actions is None else allowed_actions),
                json.dumps(current.approval_required_for if approval_required_for is None else approval_required_for),
                1 if (current.verification_required if verification_required is None else verification_required) else 0,
                current.max_parallelism if max_parallelism is None else max_parallelism,
                json.dumps(current.escalation_contacts if escalation_contacts is None else escalation_contacts),
                now,
                domain,
            ),
        )
        return self.get_policy_for_domain(domain)

    def append_signal(
        self,
        *,
        domain: str,
        source_sensor: str,
        entity_type: str,
        entity_key: str,
        signal_type: str,
        signal_strength: float,
        evidence: dict | None = None,
        signal_id: str | None = None,
    ) -> Signal:
        now = utc_now_iso()
        evidence = evidence or {}
        signal_id = signal_id or f'sig_{uuid.uuid4().hex}'
        self.db.execute(
            """
            INSERT INTO signals (
                id, domain, source_sensor, entity_type, entity_key,
                signal_type, signal_strength, evidence_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                domain,
                source_sensor,
                entity_type,
                entity_key,
                signal_type,
                signal_strength,
                json.dumps(evidence),
                now,
            ),
        )
        return self.get_signal(signal_id)

    def get_signal(self, signal_id: str) -> Signal:
        row = self.db.fetchone('SELECT * FROM signals WHERE id = ?', (signal_id,))
        if row is None:
            raise KeyError(f'Signal not found: {signal_id}')
        return Signal(
            id=row['id'],
            domain=row['domain'],
            source_sensor=row['source_sensor'],
            entity_type=row['entity_type'],
            entity_key=row['entity_key'],
            signal_type=row['signal_type'],
            signal_strength=row['signal_strength'],
            evidence=json.loads(row['evidence_json']),
            created_at=row['created_at'],
        )

    def list_recent_signals(self, *, domain: str | None = None, limit: int = 50) -> list[Signal]:
        sql = 'SELECT id FROM signals'
        params: list = []
        if domain is not None:
            sql += ' WHERE domain = ?'
            params.append(domain)
        sql += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        rows = self.db.fetchall(sql, tuple(params))
        return [self.get_signal(row['id']) for row in rows]

    def upsert_world_state(
        self,
        *,
        record_id: str,
        domain: str,
        entity_type: str,
        entity_key: str,
        state: dict,
        freshness_ts: str,
        source: str,
    ) -> WorldStateRecord:
        now = utc_now_iso()
        self.db.execute(
            """
            INSERT INTO world_state (
                id, domain, entity_type, entity_key, state_json,
                freshness_ts, source, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(domain, entity_type, entity_key) DO UPDATE SET
                state_json = excluded.state_json,
                freshness_ts = excluded.freshness_ts,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            (
                record_id,
                domain,
                entity_type,
                entity_key,
                json.dumps(state),
                freshness_ts,
                source,
                now,
            ),
        )
        return self.get_world_state(domain=domain, entity_type=entity_type, entity_key=entity_key)

    def get_world_state(self, *, domain: str, entity_type: str, entity_key: str) -> WorldStateRecord:
        row = self.db.fetchone(
            'SELECT * FROM world_state WHERE domain = ? AND entity_type = ? AND entity_key = ?',
            (domain, entity_type, entity_key),
        )
        if row is None:
            raise KeyError(f'World state not found: {domain}:{entity_type}:{entity_key}')
        return WorldStateRecord(
            id=row['id'],
            domain=row['domain'],
            entity_type=row['entity_type'],
            entity_key=row['entity_key'],
            state=json.loads(row['state_json']),
            freshness_ts=row['freshness_ts'],
            source=row['source'],
            updated_at=row['updated_at'],
        )

    def upsert_opportunity(
        self,
        *,
        opportunity_id: str,
        domain: str,
        source_sensor: str,
        title: str,
        score: float,
        risk_level: str,
        confidence: float,
        urgency: float,
        expected_value: float,
        context_cost: float,
        status: OpportunityStatus = OpportunityStatus.OPEN,
        goal_id: str | None = None,
        description: str = '',
        evidence: dict | None = None,
        delegation_mode: str | DelegationMode = DelegationMode.DIRECT_HERMES,
        delegation_target: str | None = None,
        desired_outcome: str = '',
    ) -> Opportunity:
        now = utc_now_iso()
        evidence = evidence or {}
        delegation_mode_value = delegation_mode.value if isinstance(delegation_mode, DelegationMode) else delegation_mode
        self.db.execute(
            """
            INSERT INTO opportunities (
                id, domain, goal_id, source_sensor, title, description,
                risk_level, confidence, urgency, expected_value,
                context_cost, score, status, evidence_json,
                delegation_mode, delegation_target, desired_outcome,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                goal_id = excluded.goal_id,
                source_sensor = excluded.source_sensor,
                title = excluded.title,
                description = excluded.description,
                risk_level = excluded.risk_level,
                confidence = excluded.confidence,
                urgency = excluded.urgency,
                expected_value = excluded.expected_value,
                context_cost = excluded.context_cost,
                score = excluded.score,
                status = excluded.status,
                evidence_json = excluded.evidence_json,
                delegation_mode = excluded.delegation_mode,
                delegation_target = excluded.delegation_target,
                desired_outcome = excluded.desired_outcome,
                updated_at = excluded.updated_at
            """,
            (
                opportunity_id,
                domain,
                goal_id,
                source_sensor,
                title,
                description,
                risk_level,
                confidence,
                urgency,
                expected_value,
                context_cost,
                score,
                status.value,
                json.dumps(evidence),
                delegation_mode_value,
                delegation_target,
                desired_outcome,
                now,
                now,
            ),
        )
        return self.get_opportunity(opportunity_id)

    def get_opportunity(self, opportunity_id: str) -> Opportunity:
        row = self.db.fetchone('SELECT * FROM opportunities WHERE id = ?', (opportunity_id,))
        if row is None:
            raise KeyError(f'Opportunity not found: {opportunity_id}')
        return Opportunity(
            id=row['id'],
            domain=row['domain'],
            source_sensor=row['source_sensor'],
            title=row['title'],
            score=row['score'],
            risk_level=row['risk_level'],
            confidence=row['confidence'],
            urgency=row['urgency'],
            expected_value=row['expected_value'],
            context_cost=row['context_cost'],
            status=OpportunityStatus(row['status']),
            goal_id=row['goal_id'],
            description=row['description'],
            evidence=json.loads(row['evidence_json']),
            delegation_mode=DelegationMode(row['delegation_mode']),
            delegation_target=row['delegation_target'],
            desired_outcome=row['desired_outcome'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    def list_opportunities(self, *, domain: str | None = None, status: OpportunityStatus | None = None) -> list[Opportunity]:
        sql = 'SELECT id FROM opportunities WHERE 1=1'
        params: list = []
        if domain is not None:
            sql += ' AND domain = ?'
            params.append(domain)
        if status is not None:
            sql += ' AND status = ?'
            params.append(status.value)
        sql += ' ORDER BY score DESC, created_at ASC'
        rows = self.db.fetchall(sql, tuple(params))
        return [self.get_opportunity(row['id']) for row in rows]

    def create_execution(
        self,
        *,
        execution_id: str,
        domain: str,
        executor_type: str,
        status: ExecutionStatus = ExecutionStatus.PENDING,
        opportunity_id: str | None = None,
        plan: dict | None = None,
        verification: dict | None = None,
        outcome: dict | None = None,
        review_required: bool = False,
        lease_owner: str | None = None,
        lease_expires_at: str | None = None,
    ) -> Execution:
        self.db.execute(
            """
            INSERT INTO executions (
                id, opportunity_id, domain, plan_json, executor_type, status,
                verification_json, outcome_json, started_at, completed_at,
                review_required, lease_owner, lease_expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution_id,
                opportunity_id,
                domain,
                json.dumps(plan or {}),
                executor_type,
                status.value,
                json.dumps(verification or {}),
                json.dumps(outcome or {}),
                None,
                None,
                1 if review_required else 0,
                lease_owner,
                lease_expires_at,
            ),
        )
        return self.get_execution(execution_id)

    def get_execution(self, execution_id: str) -> Execution:
        row = self.db.fetchone('SELECT * FROM executions WHERE id = ?', (execution_id,))
        if row is None:
            raise KeyError(f'Execution not found: {execution_id}')
        return Execution(
            id=row['id'],
            opportunity_id=row['opportunity_id'],
            domain=row['domain'],
            executor_type=row['executor_type'],
            status=ExecutionStatus(row['status']),
            plan=json.loads(row['plan_json']),
            verification=json.loads(row['verification_json']),
            outcome=json.loads(row['outcome_json']),
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            review_required=bool(row['review_required']),
            lease_owner=row['lease_owner'],
            lease_expires_at=row['lease_expires_at'],
        )

    def claim_execution(self, execution_id: str, *, lease_owner: str, lease_expires_at: str) -> Execution:
        now = utc_now_iso()
        cur = self.db.execute(
            """
            UPDATE executions
            SET status = ?, lease_owner = ?, lease_expires_at = ?, started_at = COALESCE(started_at, ?)
            WHERE id = ?
              AND (
                    status = ?
                    OR (status = ? AND lease_expires_at IS NOT NULL AND lease_expires_at < ?)
                  )
            """,
            (
                ExecutionStatus.CLAIMED.value,
                lease_owner,
                lease_expires_at,
                now,
                execution_id,
                ExecutionStatus.PENDING.value,
                ExecutionStatus.CLAIMED.value,
                now,
            ),
        )
        if cur.rowcount == 0:
            raise RuntimeError(f'Execution already claimed or not claimable: {execution_id}')
        return self.get_execution(execution_id)

    def complete_execution(
        self,
        execution_id: str,
        *,
        lease_owner: str,
        verification: dict | None = None,
        outcome: dict | None = None,
    ) -> Execution:
        cur = self.db.execute(
            """
            UPDATE executions
            SET status = ?, verification_json = ?, outcome_json = ?, completed_at = ?, lease_owner = NULL, lease_expires_at = NULL
            WHERE id = ? AND status IN (?, ?) AND lease_owner = ?
            """,
            (
                ExecutionStatus.COMPLETED.value,
                json.dumps(verification or {}),
                json.dumps(outcome or {}),
                utc_now_iso(),
                execution_id,
                ExecutionStatus.CLAIMED.value,
                ExecutionStatus.RUNNING.value,
                lease_owner,
            ),
        )
        if cur.rowcount == 0:
            raise RuntimeError(f'Execution cannot be completed by lease owner: {execution_id}')
        return self.get_execution(execution_id)

    def fail_execution(self, execution_id: str, *, lease_owner: str, outcome: dict | None = None) -> Execution:
        cur = self.db.execute(
            """
            UPDATE executions
            SET status = ?, outcome_json = ?, completed_at = ?, lease_owner = NULL, lease_expires_at = NULL
            WHERE id = ? AND status IN (?, ?) AND lease_owner = ?
            """,
            (
                ExecutionStatus.FAILED.value,
                json.dumps(outcome or {}),
                utc_now_iso(),
                execution_id,
                ExecutionStatus.CLAIMED.value,
                ExecutionStatus.RUNNING.value,
                lease_owner,
            ),
        )
        if cur.rowcount == 0:
            raise RuntimeError(f'Execution cannot be failed by lease owner: {execution_id}')
        return self.get_execution(execution_id)

    def prepare_execution_for_review_approval(
        self,
        execution_id: str,
        *,
        executor_type: str,
        plan: dict | None = None,
    ) -> Execution:
        cur = self.db.execute(
            """
            UPDATE executions
            SET executor_type = ?, status = ?, review_required = 0,
                plan_json = ?, verification_json = '{}', outcome_json = '{}',
                started_at = NULL, completed_at = NULL, lease_owner = NULL, lease_expires_at = NULL
            WHERE id = ?
            """,
            (
                executor_type,
                ExecutionStatus.PENDING.value,
                json.dumps(plan or {}),
                execution_id,
            ),
        )
        if cur.rowcount == 0:
            raise KeyError(f'Execution not found: {execution_id}')
        return self.get_execution(execution_id)

    def cancel_execution(self, execution_id: str, *, outcome: dict | None = None) -> Execution:
        cur = self.db.execute(
            """
            UPDATE executions
            SET status = ?, outcome_json = ?, completed_at = ?,
                lease_owner = NULL, lease_expires_at = NULL
            WHERE id = ?
            """,
            (
                ExecutionStatus.CANCELLED.value,
                json.dumps(outcome or {}),
                utc_now_iso(),
                execution_id,
            ),
        )
        if cur.rowcount == 0:
            raise KeyError(f'Execution not found: {execution_id}')
        return self.get_execution(execution_id)

    def create_review(
        self,
        *,
        review_id: str,
        execution_id: str,
        domain: str,
        review_type: str,
        reason: str,
        payload: dict,
        status: ReviewStatus = ReviewStatus.PENDING,
    ) -> Review:
        now = utc_now_iso()
        self.db.execute(
            """
            INSERT INTO reviews (
                id, execution_id, domain, review_type, reason,
                payload_json, status, created_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                execution_id,
                domain,
                review_type,
                reason,
                json.dumps(payload),
                status.value,
                now,
                None,
            ),
        )
        return self.get_review(review_id)

    def get_review(self, review_id: str) -> Review:
        row = self.db.fetchone('SELECT * FROM reviews WHERE id = ?', (review_id,))
        if row is None:
            raise KeyError(f'Review not found: {review_id}')
        return Review(
            id=row['id'],
            execution_id=row['execution_id'],
            domain=row['domain'],
            review_type=row['review_type'],
            reason=row['reason'],
            payload=json.loads(row['payload_json']),
            status=ReviewStatus(row['status']),
            created_at=row['created_at'],
            resolved_at=row['resolved_at'],
        )

    def list_pending_reviews(self, *, domain: str | None = None) -> list[Review]:
        sql = 'SELECT id FROM reviews WHERE status = ?'
        params: list = [ReviewStatus.PENDING.value]
        if domain is not None:
            sql += ' AND domain = ?'
            params.append(domain)
        sql += ' ORDER BY created_at ASC'
        rows = self.db.fetchall(sql, tuple(params))
        return [self.get_review(row['id']) for row in rows]

    def resolve_review(self, review_id: str, status: ReviewStatus) -> Review:
        if status not in {ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.EXPIRED, ReviewStatus.CANCELLED}:
            raise ValueError(f'Invalid terminal review status: {status}')
        resolved_at = utc_now_iso()
        self.db.execute(
            'UPDATE reviews SET status = ?, resolved_at = ? WHERE id = ?',
            (status.value, resolved_at, review_id),
        )
        return self.get_review(review_id)

    def create_daily_digest(
        self,
        *,
        digest_id: str,
        date_key: str,
        summary: str,
        content: dict | None = None,
        goal_ids: list[str] | None = None,
        opportunity_ids: list[str] | None = None,
        review_ids: list[str] | None = None,
    ) -> DailyDigest:
        created_at = utc_now_iso()
        self.db.execute(
            """
            INSERT INTO daily_digests (
                id, date_key, summary, content_json, goal_ids_json,
                opportunity_ids_json, review_ids_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                digest_id,
                date_key,
                summary,
                json.dumps(content or {}),
                json.dumps(goal_ids or []),
                json.dumps(opportunity_ids or []),
                json.dumps(review_ids or []),
                created_at,
            ),
        )
        return self.get_daily_digest(date_key)

    def get_daily_digest(self, date_key: str) -> DailyDigest:
        row = self.db.fetchone('SELECT * FROM daily_digests WHERE date_key = ?', (date_key,))
        if row is None:
            raise KeyError(f'Daily digest not found: {date_key}')
        return DailyDigest(
            id=row['id'],
            date_key=row['date_key'],
            summary=row['summary'],
            content=json.loads(row['content_json']),
            goal_ids=json.loads(row['goal_ids_json']),
            opportunity_ids=json.loads(row['opportunity_ids_json']),
            review_ids=json.loads(row['review_ids_json']),
            created_at=row['created_at'],
        )

    def list_daily_digests(self, *, limit: int = 20) -> list[DailyDigest]:
        rows = self.db.fetchall(
            'SELECT date_key FROM daily_digests ORDER BY date_key DESC LIMIT ?',
            (limit,),
        )
        return [self.get_daily_digest(row['date_key']) for row in rows]

    def create_learning(
        self,
        *,
        learning_id: str,
        domain: str,
        title: str,
        lesson: str,
        confidence: float,
        actionability: str,
        apply_as: str,
        execution_id: str | None = None,
    ) -> Learning:
        created_at = utc_now_iso()
        self.db.execute(
            """
            INSERT INTO learnings (
                id, domain, execution_id, title, lesson, confidence,
                actionability, apply_as, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learning_id,
                domain,
                execution_id,
                title,
                lesson,
                confidence,
                actionability,
                apply_as,
                created_at,
            ),
        )
        return self.get_learning(learning_id)

    def get_learning(self, learning_id: str) -> Learning:
        row = self.db.fetchone('SELECT * FROM learnings WHERE id = ?', (learning_id,))
        if row is None:
            raise KeyError(f'Learning not found: {learning_id}')
        return Learning(
            id=row['id'],
            domain=row['domain'],
            execution_id=row['execution_id'],
            title=row['title'],
            lesson=row['lesson'],
            confidence=row['confidence'],
            actionability=row['actionability'],
            apply_as=row['apply_as'],
            created_at=row['created_at'],
        )

    def list_learnings(self, *, domain: str | None = None, limit: int = 50) -> list[Learning]:
        sql = 'SELECT id FROM learnings'
        params: list = []
        if domain is not None:
            sql += ' WHERE domain = ?'
            params.append(domain)
        sql += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        rows = self.db.fetchall(sql, tuple(params))
        return [self.get_learning(row['id']) for row in rows]
