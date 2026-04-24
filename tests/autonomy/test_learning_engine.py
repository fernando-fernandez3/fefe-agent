from autonomy.learning_engine import LearningEngine
from autonomy.models import Execution, ExecutionStatus, Opportunity
from autonomy.store import AutonomyStore


def make_opportunity() -> Opportunity:
    return Opportunity(
        id='opp_1',
        domain='code_projects',
        source_sensor='repo_git_state',
        title='Inspect dirty repo state',
        score=0.7,
        risk_level='low',
        confidence=0.8,
        urgency=0.6,
        expected_value=0.5,
        context_cost=0.2,
        evidence={'signal_type': 'dirty_worktree'},
    )


def test_learning_engine_persists_learning_for_completed_execution(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = LearningEngine()
    store.create_execution(
        execution_id='exec_1',
        domain='code_projects',
        executor_type='repo_executor',
    )
    execution = Execution(
        id='exec_1',
        domain='code_projects',
        executor_type='repo_executor',
        status=ExecutionStatus.COMPLETED,
        verification={'command': 'git status --short'},
    )

    learning = engine.extract_and_persist(store=store, execution=execution, opportunity=make_opportunity())

    assert learning.execution_id == 'exec_1'
    assert learning.apply_as == 'workflow_note'
    assert store.list_learnings(domain='code_projects')[0].id == learning.id
    store.close()


def test_learning_engine_never_promotes_trust_automatically(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = LearningEngine()
    store.create_execution(
        execution_id='exec_2',
        domain='code_projects',
        executor_type='repo_executor',
    )
    execution = Execution(
        id='exec_2',
        domain='code_projects',
        executor_type='repo_executor',
        status=ExecutionStatus.FAILED,
        outcome={'error': 'git_failed'},
    )

    learning = engine.extract_and_persist(store=store, execution=execution, opportunity=make_opportunity())

    assert learning.apply_as != 'trust_promotion'
    assert learning.actionability == 'tighten_preconditions_before_retry'
    store.close()
