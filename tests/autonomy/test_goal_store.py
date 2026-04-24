from autonomy.models import GoalStatus
from autonomy.store import AutonomyStore


def test_create_and_list_goals(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    goal = store.create_goal(
        goal_id='goal_repo_health',
        title='Improve repo health',
        domain='code_projects',
        priority=90,
        success_signals=['fewer failing tests'],
    )
    assert goal.id == 'goal_repo_health'
    assert goal.status == GoalStatus.ACTIVE

    goals = store.list_goals()
    assert [g.id for g in goals] == ['goal_repo_health']
    store.close()


def test_update_goal_status(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_goal(
        goal_id='goal_repo_health',
        title='Improve repo health',
        domain='code_projects',
        priority=90,
    )
    updated = store.update_goal_status('goal_repo_health', GoalStatus.PAUSED)
    assert updated.status == GoalStatus.PAUSED
    store.close()
