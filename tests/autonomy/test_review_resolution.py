from autonomy.executors.base import ExecutionResult
from autonomy.execution_loop import AutonomyExecutionLoop
from autonomy.models import ExecutionStatus, ReviewStatus
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


def test_reject_review_cancels_linked_execution(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_execution(
        execution_id='exec_1',
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
        payload={'title': 'Inspect repo'},
    )

    loop = AutonomyExecutionLoop(
        store=store,
        sensors=[],
        executors={'repo_executor': _SuccessfulRepoExecutor()},
    )

    review = loop.reject_review(review_id='review_1')

    execution = store.get_execution('exec_1')
    assert review.status == ReviewStatus.REJECTED
    assert execution.status == ExecutionStatus.CANCELLED
    store.close()
