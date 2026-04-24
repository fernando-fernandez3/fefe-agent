from autonomy.seed import seed_desired_states
from autonomy.store import AutonomyStore


def test_seed_desired_states_creates_goals_entries_and_policies_idempotently(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')

    first = seed_desired_states(store)
    second = seed_desired_states(store)

    goals = store.list_goals()
    assert len(goals) == 5
    assert first['goals_created'] == 5
    assert second['goals_created'] == 0
    assert first['matrix_entries_created'] >= 10
    assert second['matrix_entries_created'] == 0
    assert first['policies_created'] >= 3
    assert second['policies_created'] == 0

    by_id = {goal.id: goal for goal in goals}
    assert by_id['ds_embarka_business'].title == 'Embarka becomes a real business'
    assert by_id['ds_spanish_fluency'].domain == 'learning'

    embarka_entries = store.list_goal_matrix_entries(goal_id='ds_embarka_business')
    assert len(embarka_entries) >= 3
    assert any(entry.asset_type == 'workflow' for entry in embarka_entries)

    store.get_policy_for_domain('code_projects')
    store.get_policy_for_domain('learning')
    store.get_policy_for_domain('personal')
    store.close()
