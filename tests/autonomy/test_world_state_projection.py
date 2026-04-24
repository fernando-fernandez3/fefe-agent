from autonomy.models import Signal
from autonomy.store import AutonomyStore
from autonomy.world_state import WorldStateProjector


def test_world_state_projector_updates_repo_state(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    signal = Signal(
        id='sig_dirty',
        domain='code_projects',
        source_sensor='repo_git_state',
        entity_type='repo',
        entity_key='/tmp/repo',
        signal_type='dirty_worktree',
        signal_strength=0.8,
        evidence={'changed_count': 2},
        created_at='2026-04-12T12:00:00+00:00',
    )

    projector = WorldStateProjector()
    record = projector.project_signal(store, signal)

    assert record.entity_key == '/tmp/repo'
    assert record.state['last_signal_type'] == 'dirty_worktree'
    assert record.state['last_evidence']['changed_count'] == 2
    store.close()
