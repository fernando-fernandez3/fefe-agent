import pytest

from autonomy.executors.base import ExecutionResult
from autonomy.execution_loop import AutonomyExecutionLoop
from autonomy.models import ExecutionStatus, OpportunityStatus, ReviewStatus
from autonomy.store import AutonomyStore


class _SuccessfulCodexExecutor:
    @property
    def name(self) -> str:
        return 'codex_executor'

    def run(self, task):
        assert task.action == 'codex_task'
        assert task.payload['prompt']
        return ExecutionResult(
            success=True,
            status='completed',
            verification={'command': 'codex exec --yolo'},
            outcome={'stdout': 'done', 'prompt': task.payload['prompt']},
        )


class _SuccessfulRepoExecutor:
    @property
    def name(self) -> str:
        return 'repo_executor'

    def run(self, task):
        return ExecutionResult(
            success=True,
            status='completed',
            verification={'command': 'git status --short'},
            outcome={'changed_count': 1},
        )


class _SuccessfulInspectRepoExecutor:
    @property
    def name(self) -> str:
        return 'repo_executor'

    def run(self, task):
        assert task.action == 'inspect_repo'
        return ExecutionResult(
            success=True,
            status='completed',
            verification={'command': 'git status --short'},
            outcome={'changed_count': 1},
        )


def test_approve_review_executes_linked_codex_task(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    repo_path = tmp_path / 'repo'
    repo_path.mkdir()
    store.create_execution(
        execution_id='exec_1',
        domain='code_projects',
        executor_type='review_only',
        review_required=True,
        plan={
            'proposed_actions': ['codex_task'],
            'repo_path': str(repo_path),
            'codex_prompt_summary': 'Fix the failing tests.',
        },
    )
    store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={'title': 'Fix failing tests'},
    )

    loop = AutonomyExecutionLoop(
        store=store,
        sensors=[],
        executors={
            'codex_executor': _SuccessfulCodexExecutor(),
            'repo_executor': _SuccessfulRepoExecutor(),
        },
    )

    execution = loop.execute_review(review_id='review_1')

    review = store.get_review('review_1')
    assert review.status == ReviewStatus.APPROVED
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.executor_type == 'codex_executor'
    assert execution.outcome['stdout'] == 'done'
    store.close()


def test_approved_pending_execution_can_be_retried_after_transient_failure(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.upsert_opportunity(
        opportunity_id='opp_1',
        domain='code_projects',
        source_sensor='repo_sensor',
        title='Inspect repo',
        score=0.8,
        risk_level='low',
        confidence=0.8,
        urgency=0.5,
        expected_value=0.5,
        context_cost=0.1,
    )
    store.create_execution(
        execution_id='exec_1',
        opportunity_id='opp_1',
        domain='code_projects',
        executor_type='review_only',
        review_required=True,
        plan={'proposed_actions': ['inspect_repo']},
    )
    store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={'opportunity_id': 'opp_1', 'title': 'Inspect repo'},
    )

    broken_loop = AutonomyExecutionLoop(store=store, sensors=[], executors={})
    with pytest.raises(KeyError):
        broken_loop.execute_review(review_id='review_1')
    assert store.get_review('review_1').status == ReviewStatus.APPROVED
    assert store.get_execution('exec_1').status == ExecutionStatus.PENDING

    retry_loop = AutonomyExecutionLoop(
        store=store,
        sensors=[],
        executors={'repo_executor': _SuccessfulInspectRepoExecutor()},
    )
    execution = retry_loop.execute_review(review_id='review_1')

    assert execution.status == ExecutionStatus.COMPLETED
    assert store.get_opportunity('opp_1').status == OpportunityStatus.COMPLETED
    store.close()


def test_approved_claimed_execution_is_not_reset_or_duplicated(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.upsert_opportunity(
        opportunity_id='opp_1',
        domain='code_projects',
        source_sensor='repo_sensor',
        title='Inspect repo',
        score=0.8,
        risk_level='low',
        confidence=0.8,
        urgency=0.5,
        expected_value=0.5,
        context_cost=0.1,
        status=OpportunityStatus.IN_PROGRESS,
    )
    store.create_execution(
        execution_id='exec_1',
        opportunity_id='opp_1',
        domain='code_projects',
        executor_type='repo_executor',
        status=ExecutionStatus.CLAIMED,
        lease_owner='worker-1',
        lease_expires_at='2999-01-01T00:00:00+00:00',
        plan={'proposed_actions': ['inspect_repo']},
    )
    store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={'opportunity_id': 'opp_1', 'title': 'Inspect repo'},
        status=ReviewStatus.APPROVED,
    )
    loop = AutonomyExecutionLoop(
        store=store,
        sensors=[],
        executors={'repo_executor': _SuccessfulInspectRepoExecutor()},
    )

    execution = loop.execute_review(review_id='review_1')

    assert execution.status == ExecutionStatus.CLAIMED
    assert execution.lease_owner == 'worker-1'
    assert store.get_opportunity('opp_1').status == OpportunityStatus.IN_PROGRESS
    store.close()


def test_reject_review_cancels_linked_execution_and_suppresses_opportunity(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.upsert_opportunity(
        opportunity_id='opp_1',
        domain='code_projects',
        source_sensor='repo_sensor',
        title='Inspect repo',
        score=0.8,
        risk_level='low',
        confidence=0.8,
        urgency=0.5,
        expected_value=0.5,
        context_cost=0.1,
    )
    store.create_execution(
        execution_id='exec_1',
        opportunity_id='opp_1',
        domain='code_projects',
        executor_type='review_only',
        review_required=True,
        plan={'proposed_actions': ['inspect_repo']},
    )
    store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={'opportunity_id': 'opp_1', 'title': 'Inspect repo'},
    )

    loop = AutonomyExecutionLoop(
        store=store,
        sensors=[],
        executors={'repo_executor': _SuccessfulRepoExecutor()},
    )

    review = loop.reject_review(review_id='review_1')

    execution = store.get_execution('exec_1')
    opportunity = store.get_opportunity('opp_1')
    assert review.status == ReviewStatus.REJECTED
    assert execution.status == ExecutionStatus.CANCELLED
    assert opportunity.status == OpportunityStatus.SUPPRESSED
    store.close()


def test_stale_approve_cannot_reverse_rejected_review(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.upsert_opportunity(
        opportunity_id='opp_1',
        domain='code_projects',
        source_sensor='repo_sensor',
        title='Inspect repo',
        score=0.8,
        risk_level='low',
        confidence=0.8,
        urgency=0.5,
        expected_value=0.5,
        context_cost=0.1,
    )
    store.create_execution(
        execution_id='exec_1',
        opportunity_id='opp_1',
        domain='code_projects',
        executor_type='review_only',
        review_required=True,
        plan={'proposed_actions': ['review_only']},
    )
    store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={'opportunity_id': 'opp_1', 'title': 'Inspect repo'},
    )
    loop = AutonomyExecutionLoop(store=store, sensors=[], executors={})

    loop.reject_review(review_id='review_1', reason='not wanted')
    with pytest.raises(RuntimeError, match='already rejected'):
        loop.execute_review(review_id='review_1')

    assert store.get_review('review_1').status == ReviewStatus.REJECTED
    assert store.get_execution('exec_1').status == ExecutionStatus.CANCELLED
    assert store.get_opportunity('opp_1').status == OpportunityStatus.SUPPRESSED
    store.close()


def test_approve_review_only_completes_without_repo_executor_and_closes_opportunity(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.upsert_opportunity(
        opportunity_id='opp_1',
        domain='learning',
        source_sensor='file_freshness',
        title='Refresh stale docs',
        score=0.8,
        risk_level='low',
        confidence=0.8,
        urgency=0.5,
        expected_value=0.5,
        context_cost=0.1,
    )
    store.create_execution(
        execution_id='exec_1',
        opportunity_id='opp_1',
        domain='learning',
        executor_type='review_only',
        review_required=True,
        plan={'proposed_actions': ['review_only']},
    )
    store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='learning',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={'opportunity_id': 'opp_1', 'title': 'Refresh stale docs'},
    )

    loop = AutonomyExecutionLoop(store=store, sensors=[], executors={})

    execution = loop.execute_review(review_id='review_1')

    review = store.get_review('review_1')
    opportunity = store.get_opportunity('opp_1')
    assert review.status == ReviewStatus.APPROVED
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.outcome['status'] == 'review_only_approved'
    assert opportunity.status == OpportunityStatus.COMPLETED
    store.close()
