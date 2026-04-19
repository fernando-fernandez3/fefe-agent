from autonomy.models import Signal
from autonomy.opportunity_engine import OpportunityEngine
from autonomy.store import AutonomyStore


def test_opportunity_engine_creates_ranked_opportunity_from_signal(tmp_path):
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

    engine = OpportunityEngine()
    opportunity = engine.upsert_from_signal(store, signal)

    assert opportunity.domain == 'code_projects'
    assert opportunity.title == 'Inspect dirty repo state'
    assert opportunity.score > 0
    assert opportunity.evidence['signal_id'] == 'sig_dirty'
    store.close()


def test_list_opportunities_orders_by_score_desc(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = OpportunityEngine()

    failing_tests = Signal(
        id='sig_fail',
        domain='code_projects',
        source_sensor='repo_health',
        entity_type='repo',
        entity_key='/tmp/repo',
        signal_type='failing_tests',
        signal_strength=0.95,
        evidence={'failing_tests': 3},
        created_at='2026-04-12T12:00:00+00:00',
    )
    stale_branch = Signal(
        id='sig_stale',
        domain='code_projects',
        source_sensor='repo_git_state',
        entity_type='repo',
        entity_key='/tmp/repo',
        signal_type='stale_branch',
        signal_strength=0.7,
        evidence={'age_seconds': 999999},
        created_at='2026-04-12T12:01:00+00:00',
    )

    engine.upsert_from_signal(store, stale_branch)
    engine.upsert_from_signal(store, failing_tests)

    opportunities = store.list_opportunities(domain='code_projects')
    assert opportunities[0].title == 'Investigate failing test slice'
    store.close()


def test_opportunity_upsert_is_domain_scoped(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = OpportunityEngine()

    first = engine.upsert_from_signal(
        store,
        Signal(
            id='sig_dirty_a',
            domain='domain_a',
            source_sensor='repo_git_state',
            entity_type='repo',
            entity_key='/tmp/repo',
            signal_type='dirty_worktree',
            signal_strength=0.8,
            evidence={},
            created_at='2026-04-12T12:00:00+00:00',
        ),
    )
    second = engine.upsert_from_signal(
        store,
        Signal(
            id='sig_dirty_b',
            domain='domain_b',
            source_sensor='repo_git_state',
            entity_type='repo',
            entity_key='/tmp/repo',
            signal_type='dirty_worktree',
            signal_strength=0.8,
            evidence={},
            created_at='2026-04-12T12:01:00+00:00',
        ),
    )

    assert first.id != second.id
    assert len(store.list_opportunities(domain='domain_a')) == 1
    assert len(store.list_opportunities(domain='domain_b')) == 1
    store.close()


def test_upserted_opportunity_preserves_scoring_inputs(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = OpportunityEngine()
    signal = Signal(
        id='sig_stale',
        domain='code_projects',
        source_sensor='repo_git_state',
        entity_type='repo',
        entity_key='/tmp/repo',
        signal_type='stale_branch',
        signal_strength=0.7,
        evidence={'age_seconds': 999999},
        created_at='2026-04-12T12:01:00+00:00',
    )

    opportunity = engine.upsert_from_signal(store, signal)

    assert opportunity.context_cost == 0.3
    store.close()
