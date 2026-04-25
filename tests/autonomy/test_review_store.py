from autonomy.models import ReviewStatus
from autonomy.store import AutonomyStore


def seed_execution(store: AutonomyStore, execution_id: str = 'exec_1') -> None:
    store.db.execute(
        """
        INSERT INTO executions (
            id, opportunity_id, domain, plan_json, executor_type, status,
            verification_json, outcome_json, started_at, completed_at,
            review_required, lease_owner, lease_expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            execution_id,
            None,
            'code_projects',
            '{}',
            'repo_executor',
            'pending',
            '{}',
            '{}',
            None,
            None,
            1,
            None,
            None,
        ),
    )



def test_create_and_list_pending_reviews(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    seed_execution(store)
    review = store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='approval',
        reason='merge requires approval',
        payload={'action': 'merge'},
    )
    assert review.status == ReviewStatus.PENDING

    pending = store.list_pending_reviews(domain='code_projects')
    assert [item.id for item in pending] == ['review_1']
    store.close()


def test_create_review_reuses_pending_review_for_same_opportunity(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    seed_execution(store, 'exec_1')
    seed_execution(store, 'exec_2')

    first = store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='policy_gate',
        reason='delegated_to_hermes_review',
        payload={'opportunity_id': 'opp_1', 'title': 'Fix thing'},
    )
    second = store.create_review(
        review_id='review_2',
        execution_id='exec_2',
        domain='code_projects',
        review_type='policy_gate',
        reason='delegated_to_hermes_review',
        payload={'opportunity_id': 'opp_1', 'title': 'Fix thing again'},
    )

    assert second.id == first.id
    pending = store.list_pending_reviews(domain='code_projects')
    assert [item.id for item in pending] == ['review_1']
    store.close()


def test_create_review_allows_new_review_after_prior_opportunity_review_resolved(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    seed_execution(store, 'exec_1')
    seed_execution(store, 'exec_2')
    store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='policy_gate',
        reason='delegated_to_hermes_review',
        payload={'opportunity_id': 'opp_1'},
    )
    store.resolve_review('review_1', ReviewStatus.CANCELLED)

    second = store.create_review(
        review_id='review_2',
        execution_id='exec_2',
        domain='code_projects',
        review_type='policy_gate',
        reason='delegated_to_hermes_review',
        payload={'opportunity_id': 'opp_1'},
    )

    assert second.id == 'review_2'
    assert [item.id for item in store.list_pending_reviews(domain='code_projects')] == ['review_2']
    store.close()


def test_resolve_review(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    seed_execution(store)
    store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='approval',
        reason='merge requires approval',
        payload={'action': 'merge'},
    )
    resolved = store.resolve_review('review_1', ReviewStatus.APPROVED)
    assert resolved.status == ReviewStatus.APPROVED
    assert resolved.resolved_at is not None
    store.close()
