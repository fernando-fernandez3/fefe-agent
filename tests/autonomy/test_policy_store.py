from autonomy.store import AutonomyStore


def test_create_and_get_policy(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    policy = store.create_policy(
        policy_id='policy_code_projects',
        domain='code_projects',
        trust_level=2,
        allowed_actions=['inspect_repo', 'run_tests'],
        approval_required_for=['merge', 'deploy'],
    )
    assert policy.domain == 'code_projects'
    assert policy.trust_level == 2
    assert policy.allowed_actions == ['inspect_repo', 'run_tests']
    store.close()


def test_update_policy(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_policy(
        policy_id='policy_code_projects',
        domain='code_projects',
        trust_level=2,
        allowed_actions=['inspect_repo'],
        approval_required_for=['merge'],
    )
    updated = store.update_policy(
        'code_projects',
        trust_level=3,
        allowed_actions=['inspect_repo', 'run_tests', 'create_branch'],
    )
    assert updated.trust_level == 3
    assert 'create_branch' in updated.allowed_actions
    assert updated.approval_required_for == ['merge']
    store.close()
