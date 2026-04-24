from autonomy.models import ExecutionStatus, OpportunityStatus
from autonomy.reporting import AutonomyReporter
from autonomy.store import AutonomyStore


def seed_report_state(store: AutonomyStore):
    store.create_goal(
        goal_id='goal_1',
        title='Keep repo healthy',
        domain='code_projects',
        priority=100,
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
        domain='code_projects',
        executor_type='repo_executor',
        status=ExecutionStatus.PENDING,
    )
    store.claim_execution('exec_1', lease_owner='worker-1', lease_expires_at='2099-01-01T00:00:00+00:00')
    store.complete_execution(
        'exec_1',
        lease_owner='worker-1',
        verification={'command': 'git status --short'},
        outcome={'changed_count': 2},
    )
    store.create_execution(
        execution_id='exec_2',
        domain='code_projects',
        executor_type='repo_executor',
        status=ExecutionStatus.PENDING,
    )
    store.claim_execution('exec_2', lease_owner='worker-2', lease_expires_at='2099-01-01T00:00:00+00:00')
    store.fail_execution('exec_2', lease_owner='worker-2', outcome={'error': 'git_failed'})
    store.create_review(
        review_id='review_1',
        execution_id='exec_2',
        domain='code_projects',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={'title': 'Inspect dirty repo state'},
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


def test_reporting_builds_summary_and_renders_text(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    seed_report_state(store)
    reporter = AutonomyReporter()

    report = reporter.build_report(store=store, domain='code_projects')
    text = reporter.render_text(report)

    assert report.goals_total == 1
    assert report.active_goals == 1
    assert report.open_opportunities == 1
    assert report.pending_reviews == 1
    assert report.learnings_captured == 1
    assert report.recent_execution_count == 2
    assert report.completed_execution_count == 1
    assert report.failed_execution_count == 1
    assert report.verification_pass_rate == 0.5
    assert report.top_opportunities == ['Inspect dirty repo state']
    assert 'Verification pass rate: 50.00%' in text
    assert '- Inspect dirty repo state' in text
    store.close()
