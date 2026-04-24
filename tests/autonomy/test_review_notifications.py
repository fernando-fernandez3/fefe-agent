from pathlib import Path

from autonomy.execution_loop import AutonomyExecutionLoop
from autonomy.executors.base import BaseExecutor, ExecutionResult, ExecutionTask
from autonomy.models import Signal
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
        return ExecutionResult(success=True, status='completed', verification={}, outcome={})


def seed_goal_and_policy(store: AutonomyStore) -> None:
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
        allowed_actions=['inspect_repo'],
        approval_required_for=['inspect_repo'],
        verification_required=True,
        max_parallelism=1,
    )


def test_execution_loop_calls_review_notifier_when_review_created(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    seed_goal_and_policy(store)
    repo_path = tmp_path / 'repo'
    repo_path.mkdir()
    notified: list[str] = []

    loop = AutonomyExecutionLoop(
        store=store,
        sensors=[DirtyRepoSensor()],
        executors={'repo_executor': SuccessfulInspectExecutor()},
        review_notifier=notified.append,
    )

    result = loop.tick(domain='code_projects', repo_path=Path(repo_path))

    assert result.status == 'review_required'
    assert notified == [result.review_id]
    store.close()
