"""One-shot autonomy execution loop for the repo-only MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from autonomy.learning_engine import LearningEngine
from autonomy.models import Execution, ExecutionStatus, GoalStatus, Opportunity, OpportunityStatus, Policy, Review, ReviewStatus, Signal
from autonomy.opportunity_engine import OpportunityEngine
from autonomy.policy_engine import PolicyDecision, PolicyEngine
from autonomy.sensors.base import BaseSensor, SensorContext
from autonomy.store import AutonomyStore
from autonomy.world_state import WorldStateProjector
from autonomy.executors.base import BaseExecutor, ExecutionTask


ActionPlanner = Callable[[Opportunity], list[str]]
ReviewNotifier = Callable[[str], None]


@dataclass(slots=True)
class TickResult:
    domain: str
    status: str
    goals_considered: int
    signal_ids: list[str] = field(default_factory=list)
    opportunity_ids: list[str] = field(default_factory=list)
    selected_opportunity_id: str | None = None
    execution_id: str | None = None
    review_id: str | None = None
    learning_id: str | None = None
    blocked_reason: str | None = None


class AutonomyExecutionLoop:
    def __init__(
        self,
        *,
        store: AutonomyStore,
        sensors: list[BaseSensor],
        executors: dict[str, BaseExecutor],
        projector: WorldStateProjector | None = None,
        opportunity_engine: OpportunityEngine | None = None,
        policy_engine: PolicyEngine | None = None,
        learning_engine: LearningEngine | None = None,
        action_planner: ActionPlanner | None = None,
        review_notifier: ReviewNotifier | None = None,
    ):
        self.store = store
        self.sensors = sensors
        self.executors = executors
        self.projector = projector or WorldStateProjector()
        self.opportunity_engine = opportunity_engine or OpportunityEngine()
        self.policy_engine = policy_engine or PolicyEngine()
        self.learning_engine = learning_engine or LearningEngine()
        self.action_planner = action_planner or self._default_action_planner
        self.review_notifier = review_notifier

    def execute_review(self, *, review_id: str) -> 'Execution':
        review = self.store.resolve_review(review_id, ReviewStatus.APPROVED)
        execution = self.store.get_execution(review.execution_id)
        primary_action = self._primary_action(execution.plan)
        executor_type = self._executor_type_for_action(primary_action)
        prepared_execution = self.store.prepare_execution_for_review_approval(
            execution.id,
            executor_type=executor_type,
            plan=execution.plan,
        )
        return self._execute_existing_execution(prepared_execution)

    def reject_review(self, *, review_id: str, reason: str = '') -> 'Review':
        review = self.store.resolve_review(review_id, ReviewStatus.REJECTED)
        outcome = {'reason': reason} if reason else {'reason': 'review_rejected'}
        self.store.cancel_execution(review.execution_id, outcome=outcome)
        return review

    def tick(self, *, domain: str, repo_path: Path | None = None, metadata: dict | None = None) -> TickResult:
        active_goals = self.store.list_goals(status=GoalStatus.ACTIVE, domain=domain)
        if not active_goals:
            return TickResult(domain=domain, status='idle_no_goals', goals_considered=0)

        policy = self.store.get_policy_for_domain(domain)
        persisted_signals = self._collect_and_persist_signals(domain=domain, repo_path=repo_path, metadata=metadata or {})
        if not persisted_signals:
            return TickResult(domain=domain, status='idle_no_signals', goals_considered=len(active_goals))

        opportunities = [self.opportunity_engine.upsert_from_signal(self.store, signal) for signal in persisted_signals]
        opportunities.sort(key=lambda opportunity: (-opportunity.score, opportunity.created_at, opportunity.id))

        selected = self._select_allowed_opportunity(policy=policy, opportunities=opportunities)
        if selected is None:
            return TickResult(
                domain=domain,
                status='blocked_no_allowed_opportunity',
                goals_considered=len(active_goals),
                signal_ids=[signal.id for signal in persisted_signals],
                opportunity_ids=[opportunity.id for opportunity in opportunities],
                blocked_reason='no_allowed_opportunity',
            )

        opportunity, decision, proposed_actions = selected
        if decision.requires_review:
            execution_id = f'exec_{uuid4().hex}'
            review_plan = {
                'opportunity_id': opportunity.id,
                'proposed_actions': proposed_actions,
                'repo_path': str(repo_path) if repo_path is not None else None,
            }
            review_payload = self._build_execution_task_payload(
                opportunity=opportunity,
                primary_action=proposed_actions[0],
                repo_path=repo_path,
            )
            if 'prompt' in review_payload:
                review_plan['codex_prompt_summary'] = review_payload['prompt']
            execution = self.store.create_execution(
                execution_id=execution_id,
                opportunity_id=opportunity.id,
                domain=domain,
                executor_type='review_only',
                plan=review_plan,
                review_required=True,
            )
            review = self.store.create_review(
                review_id=f'review_{uuid4().hex}',
                execution_id=execution.id,
                domain=domain,
                review_type='policy_gate',
                reason=decision.blocked_reason or 'review_required',
                payload={
                    'opportunity_id': opportunity.id,
                    'title': opportunity.title,
                    'proposed_actions': proposed_actions,
                    'evidence': opportunity.evidence,
                },
            )
            if self.review_notifier is not None:
                self.review_notifier(review.id)
            return TickResult(
                domain=domain,
                status='review_required',
                goals_considered=len(active_goals),
                signal_ids=[signal.id for signal in persisted_signals],
                opportunity_ids=[opportunity.id for opportunity in opportunities],
                selected_opportunity_id=opportunity.id,
                execution_id=execution.id,
                review_id=review.id,
                blocked_reason=decision.blocked_reason,
            )

        primary_action = proposed_actions[0]
        executor_type = decision.allowed_executor_types[0] if decision.allowed_executor_types else 'repo_executor'
        task_payload = self._build_execution_task_payload(opportunity=opportunity, primary_action=primary_action, repo_path=repo_path)
        execution_plan = {
            'action': primary_action,
            'proposed_actions': proposed_actions,
            'repo_path': str(repo_path) if repo_path is not None else None,
        }
        if 'prompt' in task_payload:
            execution_plan['codex_prompt_summary'] = task_payload['prompt']
        execution = self.store.create_execution(
            execution_id=f'exec_{uuid4().hex}',
            opportunity_id=opportunity.id,
            domain=domain,
            executor_type=executor_type,
            plan=execution_plan,
        )
        finalized_execution = self._execute_existing_execution(execution, task_payload=task_payload, repo_path=repo_path)

        if finalized_execution.status == ExecutionStatus.FAILED:
            learning = self.learning_engine.extract_and_persist(
                store=self.store,
                execution=finalized_execution,
                opportunity=opportunity,
            )
            return TickResult(
                domain=domain,
                status='execution_failed',
                goals_considered=len(active_goals),
                signal_ids=[signal.id for signal in persisted_signals],
                opportunity_ids=[opportunity.id for opportunity in opportunities],
                selected_opportunity_id=opportunity.id,
                execution_id=finalized_execution.id,
                learning_id=learning.id,
                blocked_reason=finalized_execution.outcome.get('status') or finalized_execution.outcome.get('error') or 'execution_failed',
            )

        learning = self.learning_engine.extract_and_persist(
            store=self.store,
            execution=finalized_execution,
            opportunity=opportunity,
        )
        return TickResult(
            domain=domain,
            status='executed',
            goals_considered=len(active_goals),
            signal_ids=[signal.id for signal in persisted_signals],
            opportunity_ids=[opportunity.id for opportunity in opportunities],
            selected_opportunity_id=opportunity.id,
            execution_id=finalized_execution.id,
            learning_id=learning.id,
        )

    def _collect_and_persist_signals(self, *, domain: str, repo_path: Path | None, metadata: dict) -> list[Signal]:
        persisted_signals: list[Signal] = []
        context = SensorContext(domain=domain, repo_path=repo_path, metadata=metadata)
        for sensor in self.sensors:
            sensor_result = sensor.collect(context)
            for emitted_signal in sensor_result.signals:
                signal = self.store.append_signal(
                    signal_id=emitted_signal.id,
                    domain=emitted_signal.domain,
                    source_sensor=emitted_signal.source_sensor,
                    entity_type=emitted_signal.entity_type,
                    entity_key=emitted_signal.entity_key,
                    signal_type=emitted_signal.signal_type,
                    signal_strength=emitted_signal.signal_strength,
                    evidence=emitted_signal.evidence,
                )
                self.projector.project_signal(self.store, signal)
                persisted_signals.append(signal)
        return persisted_signals

    def _select_allowed_opportunity(
        self,
        *,
        policy: Policy,
        opportunities: list[Opportunity],
    ) -> tuple[Opportunity, PolicyDecision, list[str]] | None:
        review_candidate: tuple[Opportunity, PolicyDecision, list[str]] | None = None
        for opportunity in opportunities:
            proposed_actions = self.action_planner(opportunity)
            if not proposed_actions:
                continue
            decision = self.policy_engine.evaluate(
                policy=policy,
                opportunity=opportunity,
                proposed_actions=proposed_actions,
            )
            if decision.allowed_to_execute:
                return opportunity, decision, proposed_actions
            if decision.requires_review and review_candidate is None:
                review_candidate = (opportunity, decision, proposed_actions)
        return review_candidate

    def _execute_existing_execution(
        self,
        execution: Execution,
        *,
        task_payload: dict | None = None,
        repo_path: Path | None = None,
    ) -> Execution:
        primary_action = self._primary_action(execution.plan)
        resolved_repo_path = repo_path or self._repo_path_from_plan(execution.plan)
        payload = task_payload or self._task_payload_from_plan(execution.plan, primary_action=primary_action, repo_path=resolved_repo_path)
        executor = self.executors[execution.executor_type]
        lease_owner = f'{execution.executor_type}-worker'
        lease_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        claimed = self.store.claim_execution(execution.id, lease_owner=lease_owner, lease_expires_at=lease_expires_at)
        result = executor.run(
            ExecutionTask(
                id=claimed.id,
                domain=claimed.domain,
                action=primary_action,
                repo_path=resolved_repo_path,
                idempotency_key=f'{claimed.id}:{primary_action}',
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
        outcome.setdefault('status', result.status)
        return self.store.fail_execution(claimed.id, lease_owner=lease_owner, outcome=outcome)

    @staticmethod
    def _primary_action(plan: dict) -> str:
        proposed_actions = plan.get('proposed_actions', [])
        return proposed_actions[0] if proposed_actions else plan.get('action', 'unknown_action')

    @staticmethod
    def _executor_type_for_action(primary_action: str) -> str:
        if primary_action == 'codex_task':
            return 'codex_executor'
        return 'repo_executor'

    @staticmethod
    def _repo_path_from_plan(plan: dict) -> Path | None:
        repo_path = plan.get('repo_path')
        return Path(repo_path) if repo_path else None

    def _task_payload_from_plan(self, plan: dict, *, primary_action: str, repo_path: Path | None) -> dict:
        if primary_action == 'codex_task':
            prompt = plan.get('codex_prompt_summary') or plan.get('prompt_summary')
            if prompt:
                return {'prompt': prompt}
        synthetic_opportunity = Opportunity(
            id=plan.get('opportunity_id') or 'review_execution',
            domain='code_projects',
            source_sensor='review_resolution',
            title=plan.get('title') or 'Approved autonomy task',
            score=0.0,
            risk_level='low',
            confidence=1.0,
            urgency=0.0,
            expected_value=0.0,
            context_cost=0.0,
            evidence={},
        )
        return self._build_execution_task_payload(
            opportunity=synthetic_opportunity,
            primary_action=primary_action,
            repo_path=repo_path,
        )

    @staticmethod
    def _build_execution_task_payload(*, opportunity: Opportunity, primary_action: str, repo_path: Path | None) -> dict:
        payload = {'opportunity_id': opportunity.id}
        if primary_action == 'codex_task':
            repo_display = str(repo_path) if repo_path is not None else 'the target repo'
            payload['prompt'] = (
                f'{opportunity.title} in {repo_display}. '
                'Investigate the issue, implement the smallest correct fix, run the relevant tests, and summarize what changed.'
            )
        return payload

    @staticmethod
    def _default_action_planner(opportunity: Opportunity) -> list[str]:
        if opportunity.domain != 'code_projects':
            return []
        if opportunity.evidence.get('signal_type') == 'failing_tests':
            return ['codex_task']
        return ['inspect_repo']
