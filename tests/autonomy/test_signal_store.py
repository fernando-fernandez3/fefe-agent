from autonomy.store import AutonomyStore


def test_append_and_list_recent_signals(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    first = store.append_signal(
        signal_id='sig_first',
        domain='code_projects',
        source_sensor='repo_git_state',
        entity_type='repo',
        entity_key='/tmp/repo',
        signal_type='dirty_worktree',
        signal_strength=0.8,
        evidence={'changed_count': 2},
    )
    second = store.append_signal(
        signal_id='sig_second',
        domain='code_projects',
        source_sensor='repo_git_state',
        entity_type='repo',
        entity_key='/tmp/repo',
        signal_type='ahead_or_behind_remote',
        signal_strength=0.7,
        evidence={'branch': 'feature/test'},
    )

    assert first.signal_type == 'dirty_worktree'
    recent = store.list_recent_signals(domain='code_projects', limit=5)
    assert [signal.id for signal in recent] == ['sig_second', 'sig_first']
    store.close()
