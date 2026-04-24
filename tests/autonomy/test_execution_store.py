import pytest

from autonomy.models import ExecutionStatus
from autonomy.store import AutonomyStore


def test_create_claim_complete_execution(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    execution = store.create_execution(
        execution_id='exec_1',
        domain='code_projects',
        executor_type='repo_executor',
        plan={'action': 'inspect_repo'},
    )
    assert execution.status == ExecutionStatus.PENDING

    claimed = store.claim_execution(
        'exec_1',
        lease_owner='worker-1',
        lease_expires_at='2026-04-12T13:00:00+00:00',
    )
    assert claimed.status == ExecutionStatus.CLAIMED
    assert claimed.lease_owner == 'worker-1'

    completed = store.complete_execution(
        'exec_1',
        lease_owner='worker-1',
        verification={'command': 'git status --short'},
        outcome={'changed_count': 2},
    )
    assert completed.status == ExecutionStatus.COMPLETED
    assert completed.outcome['changed_count'] == 2
    assert completed.completed_at is not None
    store.close()


def test_fail_execution(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_execution(
        execution_id='exec_1',
        domain='code_projects',
        executor_type='repo_executor',
    )
    store.claim_execution(
        'exec_1',
        lease_owner='worker-1',
        lease_expires_at='2099-01-01T00:00:00+00:00',
    )
    failed = store.fail_execution('exec_1', lease_owner='worker-1', outcome={'error': 'boom'})
    assert failed.status == ExecutionStatus.FAILED
    assert failed.outcome['error'] == 'boom'
    store.close()


def test_claim_execution_cannot_steal_active_lease(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_execution(
        execution_id='exec_1',
        domain='code_projects',
        executor_type='repo_executor',
    )

    store.claim_execution(
        'exec_1',
        lease_owner='worker-1',
        lease_expires_at='2099-01-01T00:00:00+00:00',
    )

    with pytest.raises(RuntimeError, match='Execution already claimed'):
        store.claim_execution(
            'exec_1',
            lease_owner='worker-2',
            lease_expires_at='2099-01-01T01:00:00+00:00',
        )

    execution = store.get_execution('exec_1')
    assert execution.lease_owner == 'worker-1'
    store.close()


def test_complete_execution_clears_lease_fields(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_execution(
        execution_id='exec_1',
        domain='code_projects',
        executor_type='repo_executor',
    )
    store.claim_execution(
        'exec_1',
        lease_owner='worker-1',
        lease_expires_at='2099-01-01T00:00:00+00:00',
    )

    completed = store.complete_execution('exec_1', lease_owner='worker-1', outcome={'ok': True})

    assert completed.lease_owner is None
    assert completed.lease_expires_at is None
    store.close()


def test_claim_execution_can_reclaim_expired_lease(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_execution(
        execution_id='exec_1',
        domain='code_projects',
        executor_type='repo_executor',
    )
    store.claim_execution(
        'exec_1',
        lease_owner='worker-1',
        lease_expires_at='2000-01-01T00:00:00+00:00',
    )

    reclaimed = store.claim_execution(
        'exec_1',
        lease_owner='worker-2',
        lease_expires_at='2099-01-01T01:00:00+00:00',
    )

    assert reclaimed.lease_owner == 'worker-2'
    assert reclaimed.status == ExecutionStatus.CLAIMED
    store.close()


def test_complete_execution_rejects_wrong_lease_owner(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_execution(
        execution_id='exec_1',
        domain='code_projects',
        executor_type='repo_executor',
    )
    store.claim_execution(
        'exec_1',
        lease_owner='worker-1',
        lease_expires_at='2099-01-01T00:00:00+00:00',
    )

    with pytest.raises(RuntimeError, match='cannot be completed'):
        store.complete_execution('exec_1', lease_owner='worker-2', outcome={'ok': True})

    store.close()


def test_complete_execution_rejects_pending_execution(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_execution(
        execution_id='exec_1',
        domain='code_projects',
        executor_type='repo_executor',
    )

    with pytest.raises(RuntimeError, match='cannot be completed'):
        store.complete_execution('exec_1', lease_owner='worker-1', outcome={'ok': True})

    store.close()
