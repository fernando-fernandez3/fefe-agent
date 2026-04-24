from autonomy.models import Opportunity, Policy
from autonomy.policy_engine import PolicyEngine
from autonomy.store import AutonomyStore


def make_policy() -> Policy:
    return Policy(
        id='policy_code_projects',
        domain='code_projects',
        trust_level=2,
        allowed_actions=['inspect_repo', 'codex_task', 'run_workflow'],
        approval_required_for=['merge', 'deploy'],
    )


def test_store_persists_opportunity_delegation_fields(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_goal(goal_id='goal_1', title='Keep repo healthy', domain='code_projects', priority=100)
    opportunity = store.upsert_opportunity(
        opportunity_id='opp_routed',
        domain='code_projects',
        goal_id='goal_1',
        source_sensor='repo_git_state',
        title='Inspect dirty repo state',
        score=0.7,
        risk_level='low',
        confidence=0.8,
        urgency=0.6,
        expected_value=0.6,
        context_cost=0.2,
        delegation_mode='direct_hermes',
        delegation_target='repo_executor',
        desired_outcome='Produce a verified repo-health summary.',
        evidence={'signal_id': 'sig_1'},
    )

    assert opportunity.delegation_mode == 'direct_hermes'
    assert opportunity.delegation_target == 'repo_executor'
    assert opportunity.desired_outcome == 'Produce a verified repo-health summary.'
    store.close()


def test_policy_engine_routes_autoworkflow_opportunities_to_autoworkflow_executor():
    engine = PolicyEngine()
    decision = engine.evaluate(
        policy=make_policy(),
        opportunity=Opportunity(
            id='opp_workflow',
            domain='code_projects',
            source_sensor='workflow_sensor',
            title='Run recurring competitor-gap workflow',
            score=0.8,
            risk_level='low',
            confidence=0.8,
            urgency=0.7,
            expected_value=0.8,
            context_cost=0.2,
            delegation_mode='autoworkflow_run',
            delegation_target='embarka-competitor-gap-issues',
        ),
        proposed_actions=['run_workflow'],
    )
    assert decision.allowed_to_execute is True
    assert decision.allowed_executor_types == ['autoworkflow_executor']


def test_policy_engine_routes_hermes_review_opportunities_to_review_only():
    engine = PolicyEngine()
    decision = engine.evaluate(
        policy=make_policy(),
        opportunity=Opportunity(
            id='opp_review',
            domain='code_projects',
            source_sensor='repo_git_state',
            title='Approve risky deploy-adjacent change',
            score=0.8,
            risk_level='medium',
            confidence=0.8,
            urgency=0.7,
            expected_value=0.8,
            context_cost=0.2,
            delegation_mode='hermes_review',
            desired_outcome='Get approval before executing the risky action.',
        ),
        proposed_actions=['inspect_repo'],
    )
    assert decision.allowed_to_execute is False
    assert decision.requires_review is True
    assert decision.allowed_executor_types == ['review_only']
