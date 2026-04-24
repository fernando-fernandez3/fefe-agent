from autonomy.models import Opportunity, Policy
from autonomy.policy_engine import PolicyEngine


def make_policy() -> Policy:
    return Policy(
        id='policy_code_projects',
        domain='code_projects',
        trust_level=2,
        allowed_actions=['inspect_repo', 'run_tests', 'create_branch'],
        approval_required_for=['merge', 'deploy'],
    )


def make_opportunity() -> Opportunity:
    return Opportunity(
        id='opp_dirty',
        domain='code_projects',
        source_sensor='repo_git_state',
        title='Inspect dirty repo state',
        score=0.72,
        risk_level='low',
        confidence=0.8,
        urgency=0.6,
        expected_value=0.6,
        context_cost=0.2,
    )


def test_policy_engine_allows_safe_repo_actions():
    engine = PolicyEngine()
    decision = engine.evaluate(
        policy=make_policy(),
        opportunity=make_opportunity(),
        proposed_actions=['inspect_repo', 'run_tests'],
    )
    assert decision.allowed_to_execute is True
    assert decision.requires_review is False
    assert decision.allowed_executor_types == ['repo_executor']


def test_policy_engine_requires_review_for_policy_actions():
    engine = PolicyEngine()
    decision = engine.evaluate(
        policy=make_policy(),
        opportunity=make_opportunity(),
        proposed_actions=['merge'],
    )
    assert decision.allowed_to_execute is False
    assert decision.requires_review is True
    assert decision.blocked_reason == 'hard_review_action'


def test_policy_engine_routes_codex_tasks_to_codex_executor():
    engine = PolicyEngine()
    policy = make_policy()
    policy.allowed_actions.append('codex_task')
    decision = engine.evaluate(
        policy=policy,
        opportunity=make_opportunity(),
        proposed_actions=['codex_task'],
    )
    assert decision.allowed_to_execute is True
    assert decision.allowed_executor_types == ['codex_executor']


def test_policy_engine_blocks_disallowed_actions():
    engine = PolicyEngine()
    decision = engine.evaluate(
        policy=make_policy(),
        opportunity=make_opportunity(),
        proposed_actions=['delete_remote_branch'],
    )
    assert decision.allowed_to_execute is False
    assert decision.requires_review is False
    assert 'disallowed_actions' in decision.blocked_reason
