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


def test_no_tests_configured_signal_scores_below_failing_tests_and_does_not_codex_route(tmp_path):
    """Regression: pytest exit-5 ('no tests collected') must score as low-priority
    informational, not as failing_tests. Otherwise the sweep's default action
    planner routes it to codex_task and Codex gets asked to fix tests that don't
    exist. Seen in prod against embarka on 2026-04-21.
    """
    from autonomy.desired_state_sweep import DesiredStateSweep
    from autonomy.models import DelegationMode

    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = OpportunityEngine()

    no_tests = Signal(
        id='sig_no_tests',
        domain='code_projects',
        source_sensor='repo_health',
        entity_type='repo',
        entity_key='/tmp/repo_no_tests',
        signal_type='no_tests_configured',
        signal_strength=0.2,
        evidence={'returncode': 5, 'check_mode': 'collect_only'},
        created_at='2026-04-22T12:00:00+00:00',
    )
    failing = Signal(
        id='sig_fail',
        domain='code_projects',
        source_sensor='repo_health',
        entity_type='repo',
        entity_key='/tmp/repo_fail',
        signal_type='failing_tests',
        signal_strength=0.65,
        evidence={'failing_count': 1},
        created_at='2026-04-22T12:01:00+00:00',
    )

    info_opp = engine.upsert_from_signal(store, no_tests)
    fail_opp = engine.upsert_from_signal(store, failing)

    # Scoring: informational signal must rank strictly below a real failing_tests signal.
    assert info_opp.score < fail_opp.score
    assert info_opp.title == 'Repo has no tests configured'
    assert info_opp.urgency <= 0.25
    # Routing: should not land in the AUTOWORKFLOW_RUN or HERMES_REVIEW codex paths —
    # DIRECT_HERMES + inspect_repo is the right (low-cost) handling.
    assert info_opp.delegation_mode == DelegationMode.DIRECT_HERMES

    # And the default action planner must NOT propose codex_task for it.
    planned = DesiredStateSweep._default_action_planner(info_opp)
    assert 'codex_task' not in planned, planned
    assert planned == ['inspect_repo']

    store.close()


def test_opportunity_engine_ignores_healthy_signals(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = OpportunityEngine()

    healthy = Signal(
        id='sig_healthy',
        domain='code_projects',
        source_sensor='url_status',
        entity_type='url',
        entity_key='https://embarka.ai',
        signal_type='site_healthy',
        signal_strength=0.1,
        evidence={'asset_label': 'Embarka live site'},
        created_at='2026-04-22T12:02:00+00:00',
    )

    opportunity = engine.upsert_from_signal(store, healthy)

    assert opportunity is None
    assert store.list_opportunities(domain='code_projects') == []
    store.close()


def test_opportunity_engine_uses_subdomain_and_asset_context_for_workflow_failures(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = OpportunityEngine()

    failed_workflow = Signal(
        id='sig_workflow_failed',
        domain='code_projects',
        source_sensor='autoworkflow_status',
        entity_type='workflow',
        entity_key='autoworkflow://embarka/feedback',
        signal_type='workflows_failed',
        signal_strength=0.8,
        evidence={
            'asset_label': 'Feedback loop',
            'subdomain': 'discovery_cadence',
        },
        created_at='2026-04-22T12:03:00+00:00',
    )

    opportunity = engine.upsert_from_signal(store, failed_workflow)

    assert opportunity is not None
    assert opportunity.title == 'discovery cadence: Investigate failed workflow: Feedback loop'
    assert opportunity.delegation_mode.value == 'hermes_review'
    store.close()



def test_opportunity_engine_routes_structured_embarka_signals_to_review(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = OpportunityEngine()

    signal = Signal(
        id='sig_feedback_gap',
        domain='code_projects',
        source_sensor='autoworkflow_status',
        entity_type='workflow',
        entity_key='autoworkflow://embarka/feedback',
        signal_type='feedback_family_constraint_gap',
        signal_strength=0.8,
        evidence={'subdomain': 'family_differentiation', 'asset_label': 'Feedback loop'},
        created_at='2026-04-22T12:04:00+00:00',
    )

    opportunity = engine.upsert_from_signal(store, signal)

    assert opportunity is not None
    assert opportunity.title == 'family differentiation: Close family-constraint gap from live feedback'
    assert opportunity.delegation_mode.value == 'hermes_review'
    assert opportunity.risk_level == 'medium'
    store.close()


def test_opportunity_engine_routes_artifact_driven_embarka_signals_to_review(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = OpportunityEngine()

    signal = Signal(
        id='sig_mobile_gap',
        domain='code_projects',
        source_sensor='autoworkflow_status',
        entity_type='workflow',
        entity_key='autoworkflow://embarka/feedback',
        signal_type='feedback_mobile_usability_gap',
        signal_strength=0.8,
        evidence={'subdomain': 'trip_creation_ux', 'asset_label': 'Feedback intake artifacts'},
        created_at='2026-04-22T12:05:00+00:00',
    )

    opportunity = engine.upsert_from_signal(store, signal)

    assert opportunity is not None
    assert opportunity.title == 'trip creation ux: Fix mobile usability gap from feedback artifacts'
    assert opportunity.delegation_mode.value == 'hermes_review'
    assert opportunity.risk_level == 'medium'
    store.close()


def test_opportunity_engine_routes_schema_aware_embarka_signals_to_review(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = OpportunityEngine()

    signal = Signal(
        id='sig_change_mgmt',
        domain='code_projects',
        source_sensor='autoworkflow_status',
        entity_type='workflow',
        entity_key='autoworkflow://embarka/competitor-gap-issues',
        signal_type='competitor_trip_change_management_threat',
        signal_strength=0.82,
        evidence={'subdomain': 'trip_creation_ux', 'asset_label': 'Competitor gap artifacts'},
        created_at='2026-04-22T12:06:00+00:00',
    )

    opportunity = engine.upsert_from_signal(store, signal)

    assert opportunity is not None
    assert opportunity.title == 'trip creation ux: Respond to competitor trip-change-management threat'
    assert opportunity.delegation_mode.value == 'hermes_review'
    assert opportunity.risk_level == 'high'
    store.close()


def test_opportunity_engine_routes_direct_feedback_canonical_signals_to_review(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    engine = OpportunityEngine()

    signal = Signal(
        id='sig_family_logistics',
        domain='code_projects',
        source_sensor='autoworkflow_status',
        entity_type='workflow',
        entity_key='autoworkflow://embarka/feedback',
        signal_type='feedback_family_logistics_gap',
        signal_strength=0.8,
        evidence={'subdomain': 'family_differentiation', 'asset_label': 'Feedback artifacts'},
        created_at='2026-04-22T12:07:00+00:00',
    )

    opportunity = engine.upsert_from_signal(store, signal)

    assert opportunity is not None
    assert opportunity.title == 'family differentiation: Close family logistics gap from structured feedback'
    assert opportunity.delegation_mode.value == 'hermes_review'
    assert opportunity.risk_level == 'high'
    store.close()
