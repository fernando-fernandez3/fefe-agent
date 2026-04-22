from autonomy.desired_state_sweep import DesiredStateSweep
from autonomy.executors.base import BaseExecutor, ExecutionResult, ExecutionTask
from autonomy.sensors.base import BaseSensor, SensorContext, SensorResult
from autonomy.sensors.registry import SensorRegistry
from autonomy.store import AutonomyStore
from autonomy.models import Signal


class LocatorSignalSensor(BaseSensor):
    def __init__(self, mapping: dict[str, Signal]):
        self._mapping = mapping

    @property
    def name(self) -> str:
        return 'locator_signal_sensor'

    def collect(self, context: SensorContext) -> SensorResult:
        locator = context.metadata['locator']
        signal = self._mapping[locator]
        return SensorResult(sensor_name=self.name, signals=[signal])


class RecordingExecutor(BaseExecutor):
    def __init__(self, name: str = 'repo_executor'):
        self._name = name
        self.tasks: list[ExecutionTask] = []

    @property
    def name(self) -> str:
        return self._name

    def run(self, task: ExecutionTask) -> ExecutionResult:
        self.tasks.append(task)
        return ExecutionResult(
            success=True,
            status='completed',
            verification={'executor': self._name},
            outcome={'action': task.action, 'repo_path': str(task.repo_path) if task.repo_path else None},
        )


def seed_goal_policy_and_entry(store: AutonomyStore, *, goal_id: str, priority: int, locator: str) -> None:
    store.create_goal(
        goal_id=goal_id,
        title=f'Goal {goal_id}',
        domain='code_projects',
        priority=priority,
    )
    store.add_goal_matrix_entry(
        entry_id=f'entry_{goal_id}',
        goal_id=goal_id,
        asset_type='repo',
        label=f'Asset {goal_id}',
        locator=locator,
    )


def test_desired_state_sweep_executes_high_priority_goal_first_and_persists_ranking_inputs(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_policy(
        policy_id='policy_code_projects',
        domain='code_projects',
        trust_level=1,
        allowed_actions=['inspect_repo'],
        approval_required_for=[],
    )
    seed_goal_policy_and_entry(store, goal_id='goal_high', priority=100, locator='/repo/high')
    seed_goal_policy_and_entry(store, goal_id='goal_low', priority=20, locator='/repo/low')

    sensor = LocatorSignalSensor(
        {
            '/repo/high': Signal(
                id='sig_high',
                domain='code_projects',
                source_sensor='locator_signal_sensor',
                entity_type='repo',
                entity_key='/repo/high',
                signal_type='generic_high_priority_signal',
                signal_strength=0.65,
                evidence={'repo_path': '/repo/high'},
            ),
            '/repo/low': Signal(
                id='sig_low',
                domain='code_projects',
                source_sensor='locator_signal_sensor',
                entity_type='repo',
                entity_key='/repo/low',
                signal_type='generic_low_priority_signal',
                signal_strength=0.95,
                evidence={'repo_path': '/repo/low'},
            ),
        }
    )
    registry = SensorRegistry({'repo': sensor})
    executor = RecordingExecutor()
    sweep = DesiredStateSweep(
        store=store,
        sensor_registry=registry,
        executors={'repo_executor': executor},
        max_actions_per_tick=1,
    )

    result = sweep.run()

    assert result.status == 'ok'
    assert result.actions_taken == 1
    assert len(executor.tasks) == 1
    assert executor.tasks[0].repo_path.as_posix() == '/repo/high'

    high = store.get_opportunity('opp::code_projects::generic_high_priority_signal::/repo/high')
    low = store.get_opportunity('opp::code_projects::generic_low_priority_signal::/repo/low')
    assert high.evidence['ranking']['goal_priority'] == 100
    assert high.evidence['ranking']['weighted_score'] > low.evidence['ranking']['weighted_score']
    assert high.evidence['ranking']['opportunity_score'] == high.score
    assert high.evidence['ranking']['urgency'] == high.urgency
    store.close()


def test_desired_state_sweep_creates_review_and_notifies_when_policy_requires_it(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_policy(
        policy_id='policy_code_projects',
        domain='code_projects',
        trust_level=1,
        allowed_actions=['inspect_repo'],
        approval_required_for=['inspect_repo'],
    )
    seed_goal_policy_and_entry(store, goal_id='goal_review', priority=100, locator='/repo/review')
    registry = SensorRegistry(
        {
            'repo': LocatorSignalSensor(
                {
                    '/repo/review': Signal(
                        id='sig_review',
                        domain='code_projects',
                        source_sensor='locator_signal_sensor',
                        entity_type='repo',
                        entity_key='/repo/review',
                        signal_type='dirty_worktree',
                        signal_strength=0.7,
                        evidence={'repo_path': '/repo/review'},
                    )
                }
            )
        }
    )
    notified: list[str] = []
    sweep = DesiredStateSweep(
        store=store,
        sensor_registry=registry,
        executors={'repo_executor': RecordingExecutor()},
        review_notifier=notified.append,
    )

    result = sweep.run()

    assert result.actions_taken == 1
    assert result.actions[0].status == 'review_required'
    assert notified == [result.actions[0].review_id]
    reviews = store.list_pending_reviews(domain='code_projects')
    assert len(reviews) == 1
    assert reviews[0].id == result.actions[0].review_id
    store.close()


def test_desired_state_sweep_records_evidence_after_successful_execution(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_policy(
        policy_id='policy_code_projects',
        domain='code_projects',
        trust_level=1,
        allowed_actions=['inspect_repo'],
        approval_required_for=[],
    )
    seed_goal_policy_and_entry(store, goal_id='goal_exec', priority=100, locator='/repo/exec')
    registry = SensorRegistry(
        {
            'repo': LocatorSignalSensor(
                {
                    '/repo/exec': Signal(
                        id='sig_exec',
                        domain='code_projects',
                        source_sensor='locator_signal_sensor',
                        entity_type='repo',
                        entity_key='/repo/exec',
                        signal_type='dirty_worktree',
                        signal_strength=0.7,
                        evidence={'repo_path': '/repo/exec'},
                    )
                }
            )
        }
    )
    sweep = DesiredStateSweep(
        store=store,
        sensor_registry=registry,
        executors={'repo_executor': RecordingExecutor()},
    )

    result = sweep.run()

    assert result.actions[0].status == 'executed'
    evidence = store.list_evidence_by_goal('goal_exec')
    assert len(evidence) == 1
    assert evidence[0].opportunity_id == 'opp::code_projects::dirty_worktree::/repo/exec'
    assert evidence[0].source == 'direct_execution'
    store.close()


def test_desired_state_sweep_skips_when_prior_run_still_holds_lock(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    sweep = DesiredStateSweep(
        store=store,
        sensor_registry=SensorRegistry(),
        executors={},
    )
    assert sweep._lock.acquire(blocking=False) is True
    try:
        result = sweep.run()
    finally:
        sweep._lock.release()
        store.close()

    assert result.status == 'skipped_locked'
    assert result.skipped_reason == 'sweep_in_progress'


def test_desired_state_sweep_resolves_repo_path_from_entity_key_when_signal_evidence_omits_it(tmp_path):
    """Regression: repo_health-style signals don't include repo_path in their evidence.

    Without falling back to entity_key, codex_executor fails with 'missing_repo_path'
    on every failing_tests sweep tick — seen in prod 2026-04-21 against embarka and
    autoworkflow matrix entries.
    """
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_policy(
        policy_id='policy_code_projects',
        domain='code_projects',
        trust_level=1,
        allowed_actions=['codex_task'],
        approval_required_for=[],
    )
    seed_goal_policy_and_entry(store, goal_id='goal_repo', priority=100, locator='/repo/fail')
    registry = SensorRegistry(
        {
            'repo': LocatorSignalSensor(
                {
                    '/repo/fail': Signal(
                        id='sig_repo_health_style',
                        domain='code_projects',
                        source_sensor='repo_health',
                        entity_type='repo',
                        entity_key='/repo/fail',
                        signal_type='failing_tests',
                        signal_strength=0.65,
                        # NOTE: repo_path intentionally absent — matches real RepoHealthSensor output
                        evidence={'test_command': 'pytest -q', 'failing_count': 1},
                    )
                }
            )
        }
    )
    executor = RecordingExecutor(name='codex_executor')
    sweep = DesiredStateSweep(
        store=store,
        sensor_registry=registry,
        executors={'codex_executor': executor},
    )

    result = sweep.run()

    assert result.actions_taken == 1, result.actions
    assert result.actions[0].status == 'executed'
    assert len(executor.tasks) == 1
    assert executor.tasks[0].repo_path is not None
    assert executor.tasks[0].repo_path.as_posix() == '/repo/fail'
    store.close()
