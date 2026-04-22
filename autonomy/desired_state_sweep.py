"""Desired-state sweep — the proactive orchestrator that wakes up and thinks.

Replaces the single-domain ``AutonomyExecutionLoop.tick`` for Phase A. Loads every
active goal, asks the sensor registry for signals on each goal-matrix asset,
ranks the resulting opportunities across goals, and acts on the top N under
policy guard. ``AutonomyExecutionLoop`` stays intact and remains the fallback
path used by legacy-domain mode.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from autonomy.evidence import Evidence, record_evidence
from autonomy.executors.base import BaseExecutor, ExecutionTask
from autonomy.models import (
    DelegationMode,
    Execution,
    ExecutionStatus,
    Goal,
    GoalMatrixEntry,
    GoalStatus,
    Opportunity,
    Signal,
)
from autonomy.opportunity_engine import OpportunityEngine
from autonomy.policy_engine import PolicyDecision, PolicyEngine
from autonomy.sensors.base import BaseSensor, SensorContext
from autonomy.sensors.registry import SensorRegistry
from autonomy.store import AutonomyStore
from autonomy.world_state import WorldStateProjector


logger = logging.getLogger(__name__)

ReviewNotifier = Callable[[str], None]
ActionPlanner = Callable[[Opportunity], list[str]]

DEFAULT_MAX_ACTIONS_PER_TICK = 3


@dataclass(slots=True)
class SweepActionOutcome:
    opportunity_id: str
    goal_id: str | None
    status: str
    execution_id: str | None = None
    review_id: str | None = None
    blocked_reason: str | None = None


@dataclass(slots=True)
class SweepResult:
    status: str
    goals_checked: int = 0
    signals_collected: int = 0
    opportunities_found: int = 0
    actions: list[SweepActionOutcome] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped_reason: str | None = None

    @property
    def pending_reviews(self) -> list[str]:
        return [action.review_id for action in self.actions if action.review_id]

    @property
    def actions_taken(self) -> int:
        return sum(
            1
            for action in self.actions
            if action.status
            in {"executed", "review_required", "autoworkflow_dispatched"}
        )


class DesiredStateSweep:
    def __init__(
        self,
        *,
        store: AutonomyStore,
        sensor_registry: SensorRegistry,
        executors: dict[str, BaseExecutor] | None = None,
        opportunity_engine: OpportunityEngine | None = None,
        policy_engine: PolicyEngine | None = None,
        projector: WorldStateProjector | None = None,
        action_planner: ActionPlanner | None = None,
        review_notifier: ReviewNotifier | None = None,
        max_actions_per_tick: int = DEFAULT_MAX_ACTIONS_PER_TICK,
    ):
        self.store = store
        self.sensor_registry = sensor_registry
        self.executors = dict(executors or {})
        self.opportunity_engine = opportunity_engine or OpportunityEngine()
        self.policy_engine = policy_engine or PolicyEngine()
        self.projector = projector or WorldStateProjector()
        self.action_planner = action_planner or self._default_action_planner
        self.review_notifier = review_notifier
        self.max_actions_per_tick = max(1, int(max_actions_per_tick))
        self._lock = threading.Lock()

    def run(self) -> SweepResult:
        if not self._lock.acquire(blocking=False):
            return SweepResult(
                status="skipped_locked", skipped_reason="sweep_in_progress"
            )
        try:
            return self._run_locked()
        finally:
            self._lock.release()

    def _run_locked(self) -> SweepResult:
        result = SweepResult(status="ok")
        try:
            active_goals = self.store.list_goals(status=GoalStatus.ACTIVE)
        except Exception as exc:
            logger.exception("desired_state_sweep: failed to load active goals")
            return SweepResult(status="error", errors=[f"load_goals_failed: {exc}"])

        result.goals_checked = len(active_goals)
        if not active_goals:
            result.status = "idle_no_goals"
            return result

        signals_by_goal: dict[str, list[Signal]] = {}
        for goal in active_goals:
            goal_signals = self._collect_goal_signals(goal, errors=result.errors)
            if goal_signals:
                signals_by_goal[goal.id] = goal_signals
                result.signals_collected += len(goal_signals)

        if not signals_by_goal:
            result.status = "idle_no_signals"
            return result

        ranked = self._generate_and_rank_opportunities(
            active_goals, signals_by_goal, errors=result.errors
        )
        result.opportunities_found = len(ranked)
        if not ranked:
            result.status = "idle_no_opportunities"
            return result

        for goal, opportunity, _weighted_score in ranked[: self.max_actions_per_tick]:
            try:
                outcome = self._decide_and_execute(goal=goal, opportunity=opportunity)
            except Exception as exc:
                logger.exception(
                    "desired_state_sweep: action failed for opportunity %s",
                    opportunity.id,
                )
                result.errors.append(f"action_failed:{opportunity.id}:{exc}")
                continue
            result.actions.append(outcome)

        if result.actions_taken == 0 and not result.errors:
            result.status = "considered_no_action"
        return result

    def _collect_goal_signals(self, goal: Goal, *, errors: list[str]) -> list[Signal]:
        try:
            entries = self.store.list_goal_matrix_entries(goal_id=goal.id)
        except Exception as exc:
            logger.exception(
                "desired_state_sweep: failed to load matrix for goal %s", goal.id
            )
            errors.append(f"matrix_load_failed:{goal.id}:{exc}")
            return []

        persisted: list[Signal] = []
        for entry in entries:
            sensor = self.sensor_registry.resolve(entry.asset_type)
            if sensor is None:
                logger.debug(
                    "desired_state_sweep: no sensor for asset_type=%s goal=%s",
                    entry.asset_type,
                    goal.id,
                )
                continue
            persisted.extend(
                self._collect_entry_signals(
                    goal=goal, entry=entry, sensor=sensor, errors=errors
                )
            )
        return persisted

    def _collect_entry_signals(
        self,
        *,
        goal: Goal,
        entry: GoalMatrixEntry,
        sensor: BaseSensor,
        errors: list[str],
    ) -> list[Signal]:
        context = SensorContext(
            domain=goal.domain,
            repo_path=Path(entry.locator) if entry.asset_type == "repo" else None,
            metadata={
                "goal_id": goal.id,
                "locator": entry.locator,
                "label": entry.label,
                **(entry.metadata or {}),
            },
        )
        try:
            sensor_result = sensor.collect(context)
        except Exception as exc:
            logger.exception(
                "desired_state_sweep: sensor %s failed for %s",
                sensor.name,
                entry.locator,
            )
            errors.append(f"sensor_failed:{sensor.name}:{entry.id}:{exc}")
            return []

        persisted: list[Signal] = []
        for emitted in sensor_result.signals:
            try:
                unique_id = f"{emitted.id}:{uuid4().hex[:8]}"
                stored = self.store.append_signal(
                    signal_id=unique_id,
                    domain=emitted.domain,
                    source_sensor=emitted.source_sensor,
                    entity_type=emitted.entity_type,
                    entity_key=emitted.entity_key,
                    signal_type=emitted.signal_type,
                    signal_strength=emitted.signal_strength,
                    evidence={**emitted.evidence, "goal_id": goal.id},
                )
                self.projector.project_signal(self.store, stored)
                persisted.append(stored)
            except Exception as exc:
                logger.exception(
                    "desired_state_sweep: failed to persist signal %s", emitted.id
                )
                errors.append(f"signal_persist_failed:{emitted.id}:{exc}")
        return persisted

    def _generate_and_rank_opportunities(
        self,
        goals: list[Goal],
        signals_by_goal: dict[str, list[Signal]],
        *,
        errors: list[str],
    ) -> list[tuple[Goal, Opportunity, float]]:
        goals_by_id = {goal.id: goal for goal in goals}
        ranked: list[tuple[Goal, Opportunity, float]] = []
        for goal_id, signals in signals_by_goal.items():
            goal = goals_by_id.get(goal_id)
            if goal is None:
                continue
            for signal in signals:
                try:
                    opportunity = self.opportunity_engine.upsert_from_signal(
                        self.store, signal
                    )
                except Exception as exc:
                    logger.exception(
                        "desired_state_sweep: failed to upsert opportunity for signal %s",
                        signal.id,
                    )
                    errors.append(f"opportunity_upsert_failed:{signal.id}:{exc}")
                    continue
                weighted = self._weighted_score(goal=goal, opportunity=opportunity)
                opportunity = self._persist_ranking_inputs(
                    goal=goal,
                    opportunity=opportunity,
                    weighted_score=weighted,
                )
                ranked.append((goal, opportunity, weighted))

        ranked.sort(key=lambda item: (-item[2], item[1].created_at, item[1].id))
        return ranked

    @staticmethod
    def _weighted_score(*, goal: Goal, opportunity: Opportunity) -> float:
        priority_weight = max(0, goal.priority) / 100.0
        urgency = max(0.0, opportunity.urgency)
        score = max(0.0, opportunity.score)
        return round(priority_weight * score * (0.5 + 0.5 * urgency), 6)

    def _persist_ranking_inputs(
        self,
        *,
        goal: Goal,
        opportunity: Opportunity,
        weighted_score: float,
    ) -> Opportunity:
        ranking = {
            "goal_priority": goal.priority,
            "opportunity_score": opportunity.score,
            "urgency": opportunity.urgency,
            "weighted_score": weighted_score,
        }
        evidence = dict(opportunity.evidence or {})
        evidence["goal_id"] = goal.id
        evidence["ranking"] = ranking
        return self.store.upsert_opportunity(
            opportunity_id=opportunity.id,
            domain=opportunity.domain,
            goal_id=goal.id,
            source_sensor=opportunity.source_sensor,
            title=opportunity.title,
            score=opportunity.score,
            risk_level=opportunity.risk_level,
            confidence=opportunity.confidence,
            urgency=opportunity.urgency,
            expected_value=opportunity.expected_value,
            context_cost=opportunity.context_cost,
            status=opportunity.status,
            description=opportunity.description,
            evidence=evidence,
            delegation_mode=opportunity.delegation_mode,
            delegation_target=opportunity.delegation_target,
            desired_outcome=opportunity.desired_outcome,
        )

    def _decide_and_execute(
        self, *, goal: Goal, opportunity: Opportunity
    ) -> SweepActionOutcome:
        proposed_actions = self.action_planner(opportunity)
        if not proposed_actions:
            return SweepActionOutcome(
                opportunity_id=opportunity.id,
                goal_id=goal.id,
                status="no_action_planned",
                blocked_reason="no_planned_action",
            )

        try:
            policy = self.store.get_policy_for_domain(opportunity.domain)
        except KeyError:
            return SweepActionOutcome(
                opportunity_id=opportunity.id,
                goal_id=goal.id,
                status="policy_missing",
                blocked_reason=f"no_policy_for_domain:{opportunity.domain}",
            )

        decision = self.policy_engine.evaluate(
            policy=policy,
            opportunity=opportunity,
            proposed_actions=proposed_actions,
        )

        if decision.requires_review:
            return self._dispatch_review(
                goal=goal,
                opportunity=opportunity,
                decision=decision,
                proposed_actions=proposed_actions,
            )
        if not decision.allowed_to_execute:
            return SweepActionOutcome(
                opportunity_id=opportunity.id,
                goal_id=goal.id,
                status="blocked",
                blocked_reason=decision.blocked_reason,
            )
        return self._dispatch_direct_execution(
            goal=goal,
            opportunity=opportunity,
            decision=decision,
            proposed_actions=proposed_actions,
        )

    def _dispatch_review(
        self,
        *,
        goal: Goal,
        opportunity: Opportunity,
        decision: PolicyDecision,
        proposed_actions: list[str],
    ) -> SweepActionOutcome:
        execution_id = f"exec_{uuid4().hex}"
        plan = {
            "opportunity_id": opportunity.id,
            "goal_id": goal.id,
            "proposed_actions": proposed_actions,
        }
        execution = self.store.create_execution(
            execution_id=execution_id,
            opportunity_id=opportunity.id,
            domain=opportunity.domain,
            executor_type="review_only",
            plan=plan,
            review_required=True,
        )
        review = self.store.create_review(
            review_id=f"review_{uuid4().hex}",
            execution_id=execution.id,
            domain=opportunity.domain,
            review_type="policy_gate",
            reason=decision.blocked_reason or "review_required",
            payload={
                "opportunity_id": opportunity.id,
                "goal_id": goal.id,
                "title": opportunity.title,
                "proposed_actions": proposed_actions,
                "evidence": opportunity.evidence,
            },
        )
        if self.review_notifier is not None:
            try:
                self.review_notifier(review.id)
            except Exception:
                logger.exception(
                    "desired_state_sweep: review_notifier raised for %s", review.id
                )
        return SweepActionOutcome(
            opportunity_id=opportunity.id,
            goal_id=goal.id,
            status="review_required",
            execution_id=execution.id,
            review_id=review.id,
            blocked_reason=decision.blocked_reason,
        )

    def _dispatch_direct_execution(
        self,
        *,
        goal: Goal,
        opportunity: Opportunity,
        decision: PolicyDecision,
        proposed_actions: list[str],
    ) -> SweepActionOutcome:
        executor_type = (
            decision.allowed_executor_types[0]
            if decision.allowed_executor_types
            else "repo_executor"
        )
        executor = self.executors.get(executor_type)
        if executor is None:
            return SweepActionOutcome(
                opportunity_id=opportunity.id,
                goal_id=goal.id,
                status="blocked",
                blocked_reason=f"executor_unavailable:{executor_type}",
            )

        primary_action = proposed_actions[0]
        repo_path = self._resolve_repo_path(opportunity)
        plan = {
            "action": primary_action,
            "proposed_actions": proposed_actions,
            "opportunity_id": opportunity.id,
            "goal_id": goal.id,
            "repo_path": str(repo_path) if repo_path is not None else None,
        }
        execution = self.store.create_execution(
            execution_id=f"exec_{uuid4().hex}",
            opportunity_id=opportunity.id,
            domain=opportunity.domain,
            executor_type=executor_type,
            plan=plan,
        )
        finalized = self._run_execution(
            execution=execution,
            executor=executor,
            primary_action=primary_action,
            opportunity=opportunity,
            repo_path=repo_path,
        )

        if opportunity.delegation_mode == DelegationMode.AUTOWORKFLOW_RUN:
            status = (
                "autoworkflow_dispatched"
                if finalized.status == ExecutionStatus.COMPLETED
                else "autoworkflow_failed"
            )
        else:
            status = (
                "executed"
                if finalized.status == ExecutionStatus.COMPLETED
                else "execution_failed"
            )

        if finalized.status == ExecutionStatus.COMPLETED:
            self._record_execution_evidence(
                goal=goal,
                opportunity=opportunity,
                execution=finalized,
            )

        return SweepActionOutcome(
            opportunity_id=opportunity.id,
            goal_id=goal.id,
            status=status,
            execution_id=finalized.id,
            blocked_reason=None
            if finalized.status == ExecutionStatus.COMPLETED
            else finalized.outcome.get("status") or finalized.outcome.get("error"),
        )

    def _run_execution(
        self,
        *,
        execution: Execution,
        executor: BaseExecutor,
        primary_action: str,
        opportunity: Opportunity,
        repo_path: Path | None,
    ) -> Execution:
        lease_owner = f"{execution.executor_type}-sweep-worker"
        lease_expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=5)
        ).isoformat()
        claimed = self.store.claim_execution(
            execution.id, lease_owner=lease_owner, lease_expires_at=lease_expires_at
        )
        payload = self._build_task_payload(
            primary_action=primary_action, opportunity=opportunity, repo_path=repo_path
        )
        result = executor.run(
            ExecutionTask(
                id=claimed.id,
                domain=claimed.domain,
                action=primary_action,
                repo_path=repo_path,
                idempotency_key=f"{claimed.id}:{primary_action}",
                payload=payload,
            )
        )
        if result.success:
            return self.store.complete_execution(
                claimed.id,
                lease_owner=lease_owner,
                verification=result.verification,
                outcome=result.outcome,
            )
        outcome = dict(result.outcome)
        outcome.setdefault("status", result.status)
        return self.store.fail_execution(
            claimed.id, lease_owner=lease_owner, outcome=outcome
        )

    def _record_execution_evidence(
        self,
        *,
        goal: Goal,
        opportunity: Opportunity,
        execution: Execution,
    ) -> None:
        outcome = execution.outcome or {}
        source = (
            "autoworkflow_run"
            if opportunity.delegation_mode == DelegationMode.AUTOWORKFLOW_RUN
            else "direct_execution"
        )
        executor_run_id = str(outcome.get("run_id") or execution.id)
        artifact_keys = ("response", "stdout", "stderr", "changed_files", "changed_count", "prompt")
        artifacts = {key: outcome[key] for key in artifact_keys if key in outcome}
        impact_summary = self._summarize_execution_impact(opportunity=opportunity, execution=execution)
        record_evidence(
            self.store,
            Evidence(
                id=f"evidence::{execution.id}",
                opportunity_id=opportunity.id,
                goal_id=goal.id,
                source=source,
                executor_run_id=executor_run_id,
                outcome="success",
                artifacts=artifacts,
                impact_summary=impact_summary,
                recorded_at=execution.completed_at or datetime.now(timezone.utc).isoformat(),
            ),
        )

    @staticmethod
    def _summarize_execution_impact(*, opportunity: Opportunity, execution: Execution) -> str:
        outcome = execution.outcome or {}
        if opportunity.delegation_mode == DelegationMode.AUTOWORKFLOW_RUN:
            run_id = outcome.get("run_id") or execution.id
            return f"Launched AutoWorkflow run {run_id} for {opportunity.title}."
        if outcome.get("changed_count") is not None:
            return f"Completed {opportunity.title} with {outcome['changed_count']} changed files observed."
        return f"Completed {opportunity.title}."

    @staticmethod
    def _resolve_repo_path(opportunity: Opportunity) -> Path | None:
        evidence = opportunity.evidence or {}
        signal_evidence = evidence.get("signal_evidence") or {}
        candidate = (
            signal_evidence.get("repo_path")
            or signal_evidence.get("locator")
            or evidence.get("repo_path")
        )
        if not candidate and evidence.get("entity_type") == "repo":
            candidate = evidence.get("entity_key")
        if candidate:
            return Path(str(candidate))
        return None

    @staticmethod
    def _build_task_payload(
        *, primary_action: str, opportunity: Opportunity, repo_path: Path | None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"opportunity_id": opportunity.id}
        if primary_action == "codex_task":
            repo_display = (
                str(repo_path) if repo_path is not None else "the target asset"
            )
            payload["prompt"] = (
                f"{opportunity.title} in {repo_display}. "
                "Investigate the signal, take the smallest correct action, verify, and summarize outcomes."
            )
        if opportunity.delegation_target:
            payload["delegation_target"] = opportunity.delegation_target
        return payload

    @staticmethod
    def _default_action_planner(opportunity: Opportunity) -> list[str]:
        if opportunity.delegation_mode == DelegationMode.HERMES_REVIEW:
            return ["review_only"]
        if opportunity.delegation_mode == DelegationMode.AUTOWORKFLOW_RUN:
            return ["autoworkflow_run"]
        signal_type = (opportunity.evidence or {}).get("signal_type")
        if signal_type == "failing_tests":
            return ["codex_task"]
        return ["inspect_repo"]
