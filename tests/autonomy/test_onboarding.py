from pathlib import Path

from autonomy.onboarding import GoalOnboarding
from autonomy.store import AutonomyStore


def test_onboarding_creates_goal_and_policy(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    repo_path = tmp_path / 'repo'
    repo_path.mkdir()

    result = GoalOnboarding().onboard_repo_goal(
        store=store,
        repo_path=repo_path,
        goal_definition='Keep this repo clean and healthy.',
    )

    goal = store.get_goal(result.goal_id)
    policy = store.get_policy_for_domain('code_projects')

    assert goal.title == 'Keep this repo clean and healthy.'
    assert goal.constraints['repo_path'] == str(repo_path)
    assert policy.allowed_actions == ['inspect_repo']
    assert result.created_goal is True
    assert result.created_policy is True
    assert result.refinement_questions == []
    store.close()


def test_onboarding_uses_repo_based_default_goal_definition(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    repo_path = tmp_path / 'hermes-agent'
    repo_path.mkdir()

    result = GoalOnboarding().onboard_repo_goal(
        store=store,
        repo_path=repo_path,
        goal_definition='   ',
    )

    assert result.title == 'Continuously improve hermes-agent repo health and reduce manual maintenance drag.'
    store.close()


def test_onboarding_generates_refinement_questions_for_broad_goal(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    repo_path = tmp_path / 'embarka'
    repo_path.mkdir()

    result = GoalOnboarding().onboard_repo_goal(
        store=store,
        repo_path=repo_path,
        goal_definition='Grow Embarka to be the best AI travel assistant and planner compared to all existing options.',
    )

    assert len(result.refinement_questions) == 5
    assert 'primary user segment' in result.refinement_questions[0]
    assert 'competitors or substitutes' in result.refinement_questions[1]
    store.close()


def test_onboarding_persists_refinement_answers_into_goal(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    repo_path = tmp_path / 'embarka'
    repo_path.mkdir()

    result = GoalOnboarding().onboard_repo_goal(
        store=store,
        repo_path=repo_path,
        goal_definition='Grow Embarka to be the best AI travel assistant and planner compared to all existing options.',
        refinement_answers={
            'primary_user_segment': 'Travelers with families',
            'target_competitors': ['ChatGPT', 'Google Travel'],
            'success_metrics': ['Trip completion', 'Paid conversion'],
            'autonomy_constraints': ['Brand voice', 'Safety'],
            'initial_wedge': 'Family logistics',
        },
    )

    goal = store.get_goal(result.goal_id)

    assert goal.constraints['primary_user_segment'] == 'Travelers with families'
    assert goal.constraints['target_competitors'] == ['ChatGPT', 'Google Travel']
    assert goal.constraints['autonomy_constraints'] == ['Brand voice', 'Safety']
    assert 'success_metric:trip_completion' in goal.success_signals
    assert 'success_metric:paid_conversion' in goal.success_signals
    assert 'Travelers with families' in result.goal_summary
    store.close()


def test_onboarding_drops_timeout_fallback_answers(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    repo_path = tmp_path / 'embarka'
    repo_path.mkdir()
    timeout_text = 'The user did not provide a response within the time limit. Use your best judgement to make the choice and proceed.'

    result = GoalOnboarding().onboard_repo_goal(
        store=store,
        repo_path=repo_path,
        goal_definition='Grow Embarka to be the best AI travel assistant and planner compared to all existing options.',
        refinement_answers={
            'primary_user_segment': 'Travelers with families',
            'target_competitors': [timeout_text],
            'success_metrics': [timeout_text],
            'autonomy_constraints': ['Brand voice'],
            'initial_wedge': 'Family logistics',
        },
    )

    goal = store.get_goal(result.goal_id)

    assert 'target_competitors' not in goal.constraints
    assert 'success_metrics' not in goal.constraints
    assert timeout_text not in result.goal_summary
    assert goal.success_signals == ['safe_repo_inspection', 'verification_evidence', 'useful_learning']
    store.close()
