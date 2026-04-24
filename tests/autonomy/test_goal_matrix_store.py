from autonomy.store import AutonomyStore


def test_add_and_list_goal_matrix_entries(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_goal(
        goal_id='goal_embarka_business',
        title='Embarka becomes a real business',
        domain='code_projects',
        priority=100,
    )

    entry = store.add_goal_matrix_entry(
        entry_id='matrix_embarka_repo',
        goal_id='goal_embarka_business',
        asset_type='repo',
        label='Embarka repo',
        locator='/home/fefernandez/embarka',
        weight=1.5,
        metadata={'default_branch': 'master'},
    )

    assert entry.goal_id == 'goal_embarka_business'
    assert entry.asset_type == 'repo'
    assert entry.weight == 1.5
    assert entry.metadata == {'default_branch': 'master'}

    entries = store.list_goal_matrix_entries(goal_id='goal_embarka_business')
    assert [item.id for item in entries] == ['matrix_embarka_repo']

    updated = store.update_goal_matrix_entry('matrix_embarka_repo', weight=2.0, metadata={'default_branch': 'main'})
    assert updated.weight == 2.0
    assert updated.metadata == {'default_branch': 'main'}

    store.remove_goal_matrix_entry('matrix_embarka_repo')
    assert store.list_goal_matrix_entries(goal_id='goal_embarka_business') == []
    store.close()
