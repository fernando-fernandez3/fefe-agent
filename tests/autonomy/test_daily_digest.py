from datetime import datetime, timedelta, timezone

from autonomy.digest_generator import DigestGenerator
from autonomy.evidence import Evidence, record_evidence
from autonomy.models import ReviewStatus
from autonomy.store import AutonomyStore


def seed_goal(store: AutonomyStore, *, goal_id: str, title: str, priority: int = 100, created_at: str | None = None):
    store.create_goal(goal_id=goal_id, title=title, domain='code_projects', priority=priority)
    store.upsert_opportunity(
        opportunity_id=f'opp_{goal_id}',
        domain='code_projects',
        goal_id=goal_id,
        source_sensor='sensor',
        title=f'Opportunity for {title}',
        score=0.8,
        risk_level='low',
        confidence=0.8,
        urgency=0.7,
        expected_value=0.8,
        context_cost=0.2,
    )
    if created_at is not None:
        store.db.execute('UPDATE goals SET created_at = ?, updated_at = ? WHERE id = ?', (created_at, created_at, goal_id))


def test_digest_generator_generates_summary_with_activity_and_is_idempotent(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    now = datetime(2026, 4, 20, 13, 0, tzinfo=timezone.utc)
    seed_goal(store, goal_id='goal_embarka', title='Embarka becomes a real business')
    store.create_execution(
        execution_id='exec_1',
        opportunity_id='opp_goal_embarka',
        domain='code_projects',
        executor_type='repo_executor',
        plan={},
    )
    store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='policy_gate',
        reason='review_required',
        payload={'title': 'Review workflow output'},
        status=ReviewStatus.PENDING,
    )
    record_evidence(
        store,
        Evidence(
            id='evidence_1',
            opportunity_id='opp_goal_embarka',
            goal_id='goal_embarka',
            source='direct_execution',
            executor_run_id='exec_1',
            outcome='success',
            artifacts={},
            impact_summary='Shipped a meaningful autonomy improvement.',
            recorded_at=(now - timedelta(hours=2)).isoformat(),
        ),
    )

    generator = DigestGenerator(store=store, now_fn=lambda: now)

    digest = generator.generate()
    repeated = generator.generate()

    assert digest.id == repeated.id
    assert digest.date_key == '2026-04-20'
    assert 'Shipped a meaningful autonomy improvement.' in digest.content['accomplishments']
    assert digest.content['pending_reviews'][0]['id'] == 'review_1'
    assert digest.content['top_opportunities'][0]['id'] == 'opp_goal_embarka'
    assert digest.content['next_planned_action']
    store.close()


def test_digest_generator_marks_all_quiet_and_detects_drift(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    now = datetime(2026, 4, 20, 13, 0, tzinfo=timezone.utc)
    stale_created_at = (now - timedelta(days=10)).isoformat()
    seed_goal(
        store,
        goal_id='goal_stale',
        title='Old neglected goal',
        priority=50,
        created_at=stale_created_at,
    )

    digest = DigestGenerator(store=store, now_fn=lambda: now).generate()

    assert digest.summary == 'All quiet across active desired states.'
    assert digest.content['accomplishments'] == []
    assert digest.content['drift_risks'][0]['goal_id'] == 'goal_stale'
    store.close()
