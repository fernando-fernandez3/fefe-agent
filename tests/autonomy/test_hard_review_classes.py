from autonomy.models import Opportunity, Policy
from autonomy.policy_engine import PolicyEngine


def test_hard_review_actions_always_require_review():
    policy = Policy(
        id='policy_code_projects',
        domain='code_projects',
        trust_level=4,
        allowed_actions=['inspect_repo', 'run_tests', 'trust_promotion'],
        approval_required_for=[],
    )
    opportunity = Opportunity(
        id='opp_trust',
        domain='code_projects',
        source_sensor='repo_health',
        title='Raise trust level',
        score=0.8,
        risk_level='low',
        confidence=0.8,
        urgency=0.5,
        expected_value=0.4,
        context_cost=0.1,
    )

    decision = PolicyEngine().evaluate(
        policy=policy,
        opportunity=opportunity,
        proposed_actions=['trust_promotion'],
    )

    assert decision.allowed_to_execute is False
    assert decision.requires_review is True
    assert decision.blocked_reason == 'hard_review_action'
