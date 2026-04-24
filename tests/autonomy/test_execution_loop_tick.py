from pathlib import Path

from autonomy.execution_loop import AutonomyExecutionLoop
from autonomy.executors.base import BaseExecutor, ExecutionResult, ExecutionTask
from autonomy.models import ExecutionStatus, Signal
from autonomy.sensors.base import BaseSensor, SensorContext, SensorResult
from autonomy.store import AutonomyStore


class DirtyRepoSensor(BaseSensor):
    @property
    def name(self) -> str:
        return 'dirty_repo_sensor'

    def collect(self, context: SensorContext) -> SensorResult:
        return SensorResult(
            sensor_name=self.name,
            signals=[
                Signal(
                    id='sig_dirty',
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type='repo',
                    entity_key=str(context.repo_path),
                    signal_type='dirty_worktree',
                    signal_strength=0.8,
                    evidence={'changed_count': 2},
                )
            ],
        )


class SuccessfulInspectExecutor(BaseExecutor):
    @property
    def name(self) -> str:
        return 'repo_executor'

    def run(self, task: ExecutionTask) -> ExecutionResult:
        assert task.action == 'inspect_repo'
        return ExecutionResult(
            success=True,
            status='completed',
            verification={'command': 'git status --short'},
            outcome={'changed_count': 2, 'repo_path': str(task.repo_path)},
        )


class FailingInspectExecutor(BaseExecutor):
    @property
    def name(self) -> str:
        return 'repo_executor'

    def run(self, task: ExecutionTask) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            status='git_failed',
            verification={'command': 'git status --short'},
            outcome={'error': 'not a git repo'},
        )


class FailingTestsSensor(BaseSensor):
    @property
    def name(self) -> str:
        return 'repo_health_sensor'

    def collect(self, context: SensorContext) -> SensorResult:
        return SensorResult(
            sensor_name=self.name,
            signals=[
                Signal(
                    id='sig_tests',
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type='repo',
                    entity_key=str(context.repo_path),
                    signal_type='failing_tests',
                    signal_strength=0.95,
                    evidence={'failing_command': 'pytest -q', 'failing_count': 3},
                )
            ],
        )


class SuccessfulCodexExecutor(BaseExecutor):
    @property
    def name(self) -> str:
        return 'codex_executor'

    def run(self, task: ExecutionTask) -> ExecutionResult:
        assert task.action == 'codex_task'
        assert task.payload['prompt']
        return ExecutionResult(
            success=True,
            status='completed',
            verification={'command': 'codex exec --yolo'},
            outcome={'stdout': 'fixed tests', 'prompt': task.payload['prompt']},
        )


def seed_goal_and_policy(store: AutonomyStore, *, approval_required_for: list[str] | None = None, allowed_actions: list[str] | None = None) -> None:
    store.create_goal(
        goal_id='goal_1',
        title='Keep repo healthy',
        domain='code_projects',
        priority=100,
    )
    store.create_policy(
        policy_id='policy_1',
        domain='code_projects',
        trust_level=1,
        allowed_actions=allowed_actions or ['inspect_repo'],
        approval_required_for=approval_required_for or [],
        verification_required=True,
        max_parallelism=1,
    )


def test_execution_loop_executes_safe_repo_tick(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    seed_goal_and_policy(store)
    repo_path = tmp_path / 'repo'
    repo_path.mkdir()

    loop = AutonomyExecutionLoop(
        store=store,
        sensors=[DirtyRepoSensor()],
        executors={'repo_executor': SuccessfulInspectExecutor()},
    )

    result = loop.tick(domain='code_projects', repo_path=repo_path)

    assert result.status == 'executed'
    assert result.execution_id is not None
    assert result.review_id is None
    assert result.learning_id is not None
    assert len(result.signal_ids) == 1
    assert len(result.opportunity_ids) == 1

    signals = store.list_recent_signals(domain='code_projects')
    assert len(signals) == 1
    world_state = store.get_world_state(domain='code_projects', entity_type='repo', entity_key=str(repo_path))
    assert world_state.state['last_signal_type'] == 'dirty_worktree'

    execution = store.get_execution(result.execution_id)
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.verification['command'] == 'git status --short'
    assert execution.outcome['changed_count'] == 2
    learning = store.get_learning(result.learning_id)
    assert learning.execution_id == execution.id
    assert learning.apply_as == 'workflow_note'
    store.close()


def test_execution_loop_persists_review_when_policy_requires_it(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    seed_goal_and_policy(store, approval_required_for=['inspect_repo'])
    repo_path = tmp_path / 'repo'
    repo_path.mkdir()

    loop = AutonomyExecutionLoop(
        store=store,
        sensors=[DirtyRepoSensor()],
        executors={'repo_executor': SuccessfulInspectExecutor()},
    )

    result = loop.tick(domain='code_projects', repo_path=repo_path)

    assert result.status == 'review_required'
    assert result.review_id is not None
    execution = store.get_execution(result.execution_id)
    assert execution.review_required is True
    reviews = store.list_pending_reviews(domain='code_projects')
    assert len(reviews) == 1
    assert reviews[0].reason == 'policy_requires_review'
    store.close()


def test_execution_loop_records_failed_execution(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    seed_goal_and_policy(store)
    repo_path = tmp_path / 'repo'
    repo_path.mkdir()

    loop = AutonomyExecutionLoop(
        store=store,
        sensors=[DirtyRepoSensor()],
        executors={'repo_executor': FailingInspectExecutor()},
    )

    result = loop.tick(domain='code_projects', repo_path=repo_path)

    assert result.status == 'execution_failed'
    assert result.blocked_reason == 'git_failed'
    assert result.learning_id is not None
    execution = store.get_execution(result.execution_id)
    assert execution.status == ExecutionStatus.FAILED
    assert execution.outcome['error'] == 'not a git repo'
    learning = store.get_learning(result.learning_id)
    assert learning.apply_as == 'guardrail_note'
    store.close()


def test_execution_loop_executes_codex_task_for_failing_tests_signal(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    seed_goal_and_policy(store, allowed_actions=['inspect_repo', 'codex_task'])
    repo_path = tmp_path / 'repo'
    repo_path.mkdir()

    loop = AutonomyExecutionLoop(
        store=store,
        sensors=[FailingTestsSensor()],
        executors={
            'repo_executor': SuccessfulInspectExecutor(),
            'codex_executor': SuccessfulCodexExecutor(),
        },
    )

    result = loop.tick(domain='code_projects', repo_path=repo_path)

    assert result.status == 'executed'
    execution = store.get_execution(result.execution_id)
    assert execution.executor_type == 'codex_executor'
    assert execution.plan['action'] == 'codex_task'
    assert execution.plan['codex_prompt_summary']
    assert 'Investigate failing test slice' in execution.outcome['prompt']
    store.close()


def test_execution_loop_returns_idle_without_active_goals(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_policy(
        policy_id='policy_1',
        domain='code_projects',
        trust_level=1,
        allowed_actions=['inspect_repo'],
        approval_required_for=[],
        verification_required=True,
        max_parallelism=1,
    )
    repo_path = tmp_path / 'repo'
    repo_path.mkdir()

    loop = AutonomyExecutionLoop(
        store=store,
        sensors=[DirtyRepoSensor()],
        executors={'repo_executor': SuccessfulInspectExecutor()},
    )

    result = loop.tick(domain='code_projects', repo_path=repo_path)

    assert result.status == 'idle_no_goals'
    assert store.list_recent_signals(domain='code_projects') == []
    store.close()
