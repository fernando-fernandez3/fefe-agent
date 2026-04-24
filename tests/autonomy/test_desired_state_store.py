from autonomy.models import GoalStatus
from autonomy.store import AutonomyStore


def test_create_and_update_desired_state_fields(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    goal = store.create_goal(
        goal_id='goal_embarka_business',
        title='Embarka becomes a real business',
        domain='code_projects',
        priority=100,
        description='Turn Embarka into a revenue-generating product.',
        horizon='3_months',
        why_it_matters='It is the top business priority.',
        progress_examples=['shipped feature', 'new revenue'],
        review_thresholds={'deploy': 'always_review'},
        success_signals=['revenue', 'active users'],
        constraints={'no_deploy_without_approval': True},
    )

    assert goal.id == 'goal_embarka_business'
    assert goal.status == GoalStatus.ACTIVE
    assert goal.why_it_matters == 'It is the top business priority.'
    assert goal.progress_examples == ['shipped feature', 'new revenue']
    assert goal.review_thresholds == {'deploy': 'always_review'}
    assert goal.constraints == {'no_deploy_without_approval': True}

    updated = store.update_goal(
        'goal_embarka_business',
        why_it_matters='It compounds product and revenue progress.',
        progress_examples=['weekly shipped work'],
        review_thresholds={'deploy': 'always_review', 'merge': 'review'},
    )

    assert updated.why_it_matters == 'It compounds product and revenue progress.'
    assert updated.progress_examples == ['weekly shipped work']
    assert updated.review_thresholds == {'deploy': 'always_review', 'merge': 'review'}
    store.close()
