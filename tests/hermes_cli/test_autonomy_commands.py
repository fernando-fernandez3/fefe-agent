from contextlib import redirect_stdout
from io import StringIO
import subprocess
from unittest.mock import MagicMock

import hermes_cli.setup as setup_ui

from cli import HermesCLI
from autonomy.executors.base import ExecutionResult
from autonomy.models import OpportunityStatus
from autonomy.store import AutonomyStore
from hermes_cli.commands import COMMANDS, resolve_command


def make_cli(tmp_path):
    cli_obj = HermesCLI.__new__(HermesCLI)
    cli_obj.config = {}
    cli_obj.console = MagicMock()
    cli_obj._open_autonomy_store = lambda: AutonomyStore(tmp_path / 'autonomy.db')
    return cli_obj


def seed_autonomy_state(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_goal(
        goal_id='goal_1',
        title='Keep repo healthy',
        domain='code_projects',
        priority=100,
    )
    store.create_policy(
        policy_id='policy_1',
        domain='code_projects',
        trust_level=1,
        allowed_actions=['inspect_repo', 'codex_task'],
        approval_required_for=[],
        verification_required=True,
        max_parallelism=1,
    )
    store.upsert_opportunity(
        opportunity_id='opp_1',
        domain='code_projects',
        source_sensor='repo_git_state',
        title='Inspect dirty repo state',
        score=0.73,
        risk_level='low',
        confidence=0.8,
        urgency=0.6,
        expected_value=0.5,
        context_cost=0.2,
        status=OpportunityStatus.OPEN,
        evidence={'signal_type': 'dirty_worktree'},
    )
    store.create_execution(
        execution_id='exec_1',
        opportunity_id='opp_1',
        domain='code_projects',
        executor_type='review_only',
        review_required=True,
        plan={
            'proposed_actions': ['codex_task'],
            'repo_path': str(tmp_path / 'repo'),
            'codex_prompt_summary': 'Fix the failing tests and rerun pytest.',
        },
    )
    store.create_review(
        review_id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={
            'title': 'Inspect dirty repo state',
            'evidence': {'signal_type': 'failing_tests', 'signal_evidence': {'changed_count': 2}},
        },
    )
    store.create_learning(
        learning_id='learning_1',
        domain='code_projects',
        execution_id='exec_1',
        title='Read-only repo inspection succeeded',
        lesson='Verification evidence was attached.',
        confidence=0.8,
        actionability='reuse_readonly_repo_inspection',
        apply_as='workflow_note',
    )
    store.close()


def test_autonomy_commands_registered():
    assert '/autonomy' in COMMANDS
    assert '/autonomy-run' in COMMANDS
    assert '/autonomy-seed' in COMMANDS
    assert '/autonomy-onboard' in COMMANDS
    assert '/review-approve' in COMMANDS
    assert '/review-reject' in COMMANDS
    assert '/goals' in COMMANDS
    assert '/reviews' in COMMANDS
    assert '/opportunities' in COMMANDS
    assert resolve_command('autonomy').name == 'autonomy'
    assert resolve_command('autonomy-run').name == 'autonomy-run'
    assert resolve_command('autonomy-seed').name == 'autonomy-seed'
    assert resolve_command('autonomy-onboard').name == 'autonomy-onboard'
    assert resolve_command('review-approve').name == 'review-approve'
    assert resolve_command('review-reject').name == 'review-reject'
    assert resolve_command('goals').name == 'goals'
    assert resolve_command('reviews').name == 'reviews'
    assert resolve_command('opportunities').name == 'opportunities'


def test_autonomy_commands_render_stored_state(tmp_path):
    seed_autonomy_state(tmp_path)
    cli_obj = make_cli(tmp_path)

    buffer = StringIO()
    with redirect_stdout(buffer):
        assert cli_obj.process_command('/autonomy') is True
        assert cli_obj.process_command('/goals') is True
        assert cli_obj.process_command('/reviews') is True
        assert cli_obj.process_command('/opportunities') is True

    output = buffer.getvalue()
    assert 'Autonomy report' in output
    assert 'Goals: 1 total, 1 active' in output
    assert 'Open opportunities: 1' in output
    assert 'Pending reviews: 1' in output
    assert 'Learnings captured: 1' in output
    assert 'Autonomy goals' in output
    assert '[active] Keep repo healthy' in output
    assert 'Pending autonomy reviews' in output
    assert 'review_1' in output
    assert 'policy_requires_review' in output
    assert 'run Codex inside' in output
    assert 'Open autonomy opportunities' in output
    assert 'Inspect dirty repo state [code_projects] score=0.73 risk=low' in output


def test_autonomy_seed_and_run_commands(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-b', 'main'], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo, check=True, capture_output=True, text=True)
    (repo / 'README.md').write_text('hello\n')
    subprocess.run(['git', 'add', 'README.md'], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'commit', '-m', 'initial'], cwd=repo, check=True, capture_output=True, text=True)
    (repo / 'README.md').write_text('changed\n')
    monkeypatch.setenv('TERMINAL_CWD', str(repo))

    cli_obj = make_cli(tmp_path)
    buffer = StringIO()
    with redirect_stdout(buffer):
        assert cli_obj.process_command('/autonomy-seed') is True
        assert cli_obj.process_command('/autonomy-run') is True

    output = buffer.getvalue()
    assert 'Seeded repo-health autonomy goal/policy for code_projects.' in output
    assert 'Autonomy tick: executed' in output
    assert 'Execution:' in output
    assert 'Learning:' in output


def test_autonomy_seed_and_run_creates_review_for_failing_tests(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-b', 'main'], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo, check=True, capture_output=True, text=True)
    tests_dir = repo / 'tests'
    tests_dir.mkdir()
    (tests_dir / 'test_fail.py').write_text('def test_fail():\n    assert False\n')
    subprocess.run(['git', 'add', 'tests/test_fail.py'], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'commit', '-m', 'initial failing test'], cwd=repo, check=True, capture_output=True, text=True)
    monkeypatch.setenv('TERMINAL_CWD', str(repo))

    cli_obj = make_cli(tmp_path)
    buffer = StringIO()
    with redirect_stdout(buffer):
        assert cli_obj.process_command('/autonomy-seed') is True
        assert cli_obj.process_command('/autonomy-run') is True
        assert cli_obj.process_command('/reviews') is True

    output = buffer.getvalue()
    assert 'Autonomy tick: review_required' in output
    assert 'Review:' in output
    assert 'Pending autonomy reviews' in output
    assert 'policy_requires_review' in output
    assert 'run Codex inside' in output

    store = AutonomyStore(tmp_path / 'autonomy.db')
    reviews = store.list_pending_reviews(domain='code_projects')
    assert len(reviews) == 1
    execution = store.get_execution(reviews[0].execution_id)
    assert execution.review_required is True
    assert execution.executor_type == 'review_only'
    assert execution.plan['proposed_actions'] == ['codex_task']
    store.close()


def test_review_approve_command_executes_linked_work(tmp_path, monkeypatch):
    seed_autonomy_state(tmp_path)
    repo = tmp_path / 'repo'
    repo.mkdir(exist_ok=True)

    def fake_run(self, task):
        return ExecutionResult(
            success=True,
            status='completed',
            verification={'command': 'codex exec --yolo'},
            outcome={'stdout': 'done', 'prompt': task.payload['prompt']},
        )

    monkeypatch.setattr('autonomy.executors.codex_executor.CodexExecutor.run', fake_run)

    cli_obj = make_cli(tmp_path)
    buffer = StringIO()
    with redirect_stdout(buffer):
        assert cli_obj.process_command('/review-approve review_1') is True

    output = buffer.getvalue()
    assert 'Approved review review_1' in output
    assert 'Execution completed:' in output

    store = AutonomyStore(tmp_path / 'autonomy.db')
    review = store.get_review('review_1')
    execution = store.get_execution('exec_1')
    assert review.status.value == 'approved'
    assert execution.status.value == 'completed'
    assert execution.executor_type == 'codex_executor'
    store.close()


def test_review_reject_command_cancels_linked_work(tmp_path):
    seed_autonomy_state(tmp_path)
    cli_obj = make_cli(tmp_path)
    buffer = StringIO()
    with redirect_stdout(buffer):
        assert cli_obj.process_command('/review-reject review_1 too risky') is True

    output = buffer.getvalue()
    assert 'Rejected review review_1' in output
    assert 'too risky' in output

    store = AutonomyStore(tmp_path / 'autonomy.db')
    review = store.get_review('review_1')
    execution = store.get_execution('exec_1')
    assert review.status.value == 'rejected'
    assert execution.status.value == 'cancelled'
    store.close()


def test_autonomy_onboard_command(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    repo.mkdir()
    monkeypatch.setenv('TERMINAL_CWD', str(repo))

    cli_obj = make_cli(tmp_path)
    cli_obj._run_autonomy_onboarding_questionnaire = MagicMock(return_value={
        'primary_user_segment': 'Travelers with families',
        'target_competitors': ['ChatGPT', 'Google Travel'],
        'success_metrics': ['Trip completion'],
        'autonomy_constraints': ['Brand voice'],
        'initial_wedge': 'Family logistics',
    })
    buffer = StringIO()
    with redirect_stdout(buffer):
        assert cli_obj.process_command('/autonomy-onboard Grow Embarka to be the best AI travel assistant and planner compared to all existing options.') is True

    output = buffer.getvalue()
    assert 'Onboarded autonomy goal for repo.' in output
    assert 'Goal:   Grow Embarka to be the best AI travel assistant and planner compared to all existing options.' in output
    assert 'Saved refinement:' in output
    assert 'Travelers with families' in output
    assert 'Family logistics' in output

    store = AutonomyStore(tmp_path / 'autonomy.db')
    goals = store.list_goals(domain='code_projects')
    assert len(goals) == 1
    assert goals[0].title == 'Grow Embarka to be the best AI travel assistant and planner compared to all existing options.'
    assert goals[0].constraints['primary_user_segment'] == 'Travelers with families'
    assert goals[0].constraints['initial_wedge'] == 'Family logistics'
    store.close()


def test_autonomy_questionnaire_uses_clarify_ui_inside_tui(tmp_path, monkeypatch):
    cli_obj = make_cli(tmp_path)
    cli_obj._app = object()
    cli_obj._clarify_callback = MagicMock(side_effect=[
        'Travelers with families',
        'ChatGPT',
        'Google Travel',
        'Done selecting',
        'Trip completion',
        'Done selecting',
        'Brand voice',
        'Done selecting',
        'Family logistics',
    ])

    monkeypatch.setattr(setup_ui, 'prompt_choice', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('prompt_choice should not be used in TUI mode')))
    monkeypatch.setattr(setup_ui, 'prompt_checklist', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('prompt_checklist should not be used in TUI mode')))

    from autonomy.onboarding import GoalOnboarding
    answers = cli_obj._run_autonomy_onboarding_questionnaire(
        GoalOnboarding().refinement_questionnaire(
            'Grow Embarka to be the best AI travel assistant and planner compared to all existing options.'
        )
    )

    assert answers == {
        'primary_user_segment': 'Travelers with families',
        'target_competitors': ['ChatGPT', 'Google Travel'],
        'success_metrics': ['Trip completion'],
        'autonomy_constraints': ['Brand voice'],
        'initial_wedge': 'Family logistics',
    }
    assert cli_obj._clarify_callback.call_count == 9


def test_autonomy_questionnaire_drops_timeout_fallback_responses(tmp_path, monkeypatch):
    cli_obj = make_cli(tmp_path)
    cli_obj._app = object()
    timeout_text = 'The user did not provide a response within the time limit. Use your best judgement to make the choice and proceed.'
    cli_obj._clarify_callback = MagicMock(side_effect=[
        'Travelers with families',
        timeout_text,
        timeout_text,
        'Brand voice',
        'Done selecting',
        'Family logistics',
    ])

    monkeypatch.setattr(setup_ui, 'prompt_choice', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('prompt_choice should not be used in TUI mode')))
    monkeypatch.setattr(setup_ui, 'prompt_checklist', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('prompt_checklist should not be used in TUI mode')))

    from autonomy.onboarding import GoalOnboarding
    answers = cli_obj._run_autonomy_onboarding_questionnaire(
        GoalOnboarding().refinement_questionnaire(
            'Grow Embarka to be the best AI travel assistant and planner compared to all existing options.'
        )
    )

    assert answers == {
        'primary_user_segment': 'Travelers with families',
        'autonomy_constraints': ['Brand voice'],
        'initial_wedge': 'Family logistics',
    }
