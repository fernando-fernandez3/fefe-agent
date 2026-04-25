from autonomy.models import Execution, Opportunity, Review
from autonomy.review_packets import ReviewPacketFormatter


def test_review_packet_formatter_includes_required_sections():
    formatter = ReviewPacketFormatter()
    review = Review(
        id='review_1',
        execution_id='exec_1',
        domain='code_projects',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={
            'title': 'Inspect dirty repo state',
            'evidence': {
                'signal_type': 'dirty_worktree',
                'signal_evidence': {'changed_count': 3, 'branch': 'feature/foo'},
            },
        },
    )
    execution = Execution(
        id='exec_1',
        domain='code_projects',
        executor_type='review_only',
        plan={'proposed_actions': ['inspect_repo']},
    )
    opportunity = Opportunity(
        id='opp_1',
        domain='code_projects',
        source_sensor='repo_git_state',
        title='Inspect dirty repo state',
        score=0.7,
        risk_level='low',
        confidence=0.8,
        urgency=0.6,
        expected_value=0.5,
        context_cost=0.2,
        evidence=review.payload['evidence'],
    )

    packet = formatter.format(review=review, execution=execution, opportunity=opportunity)
    text = packet.as_text()

    assert 'Review required: Inspect dirty repo state' in text
    assert 'Proposed action: inspect_repo' in text
    assert 'Needs review: policy_requires_review' in text
    assert 'If approved: Execution exec_1 will proceed with inspect_repo.' in text
    assert '- signal: dirty_worktree' in text
    assert '- changed files: 3' in text
    assert '- branch: feature/foo' in text


def test_review_packet_formatter_falls_back_without_opportunity():
    formatter = ReviewPacketFormatter()
    review = Review(
        id='review_2',
        execution_id='exec_2',
        domain='code_projects',
        review_type='policy_gate',
        reason='hard_review_action',
        payload={'title': 'Autonomy review request', 'evidence': {}},
    )
    execution = Execution(
        id='exec_2',
        domain='code_projects',
        executor_type='review_only',
        plan={'action': 'inspect_repo'},
    )

    packet = formatter.format(review=review, execution=execution)

    assert packet.proposed_action == 'inspect_repo'
    assert packet.evidence_summary == []


def test_review_packet_formatter_describes_codex_task_execution():
    formatter = ReviewPacketFormatter()
    review = Review(
        id='review_3',
        execution_id='exec_3',
        domain='code_projects',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={
            'title': 'Implement repo health fix',
            'evidence': {
                'signal_type': 'failing_tests',
                'signal_evidence': {'branch': 'feature/autonomy', 'changed_count': 2},
            },
        },
    )
    execution = Execution(
        id='exec_3',
        domain='code_projects',
        executor_type='review_only',
        plan={
            'proposed_actions': ['codex_task'],
            'repo_path': '/tmp/repo',
            'codex_prompt_summary': 'Fix the failing test slice and rerun pytest.',
        },
    )

    packet = formatter.format(review=review, execution=execution)
    text = packet.as_text()

    assert packet.proposed_action == 'codex_task'
    assert 'run Codex inside /tmp/repo' in packet.approval_effect
    assert 'Fix the failing test slice and rerun pytest.' in packet.approval_effect
    assert '- signal: failing_tests' in text


def test_review_packet_formatter_summarizes_embarka_artifact_evidence():
    formatter = ReviewPacketFormatter()
    evidence = {
        'signal_type': 'feedback_mobile_usability_gap',
        'signal_evidence': {
            'artifact_paths': ['embarka/artifacts/mobile_feedback.md'],
            'candidate_keys': ['mobile.checkout.tap_targets'],
            'canonical_keys': ['feedback.mobile.usability.checkout'],
            'matches': [
                {
                    'source_path': 'embarka/artifacts/mobile_feedback.md',
                    'source_type': 'feedback_artifact',
                    'title': 'Mobile checkout feedback',
                    'candidate_key': 'mobile.checkout.tap_targets',
                    'canonical_key': 'feedback.mobile.usability.checkout',
                    'matched_keys': ['mobile.checkout', 'tap_targets'],
                    'matched_keywords': ['mobile', 'tap targets', 'checkout'],
                    'snippet': 'Checkout buttons are hard to tap on small screens.',
                }
            ],
        },
    }
    review = Review(
        id='review_4',
        execution_id='exec_4',
        domain='product_feedback',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={'title': 'Review mobile usability gap', 'evidence': evidence},
    )
    execution = Execution(
        id='exec_4',
        domain='product_feedback',
        executor_type='review_only',
        plan={'proposed_actions': ['codex_task']},
    )

    packet = formatter.format(review=review, execution=execution)
    text = packet.as_text()

    assert '- artifact source file: embarka/artifacts/mobile_feedback.md (feedback_artifact; Mobile checkout feedback)' in text
    assert '- candidate keys: mobile.checkout.tap_targets' in text
    assert '- canonical keys: feedback.mobile.usability.checkout' in text
    assert '- matched keys: mobile.checkout, tap_targets' in text
    assert '- matched keywords: mobile, tap targets, checkout' in text
    assert '- snippet: Checkout buttons are hard to tap on small screens.' in text
    assert '- suggested action: review mobile usability feedback and close the mapped artifact gap.' in text


def test_review_packet_formatter_accepts_live_artifact_paths_dict_shape():
    formatter = ReviewPacketFormatter()
    review = Review(
        id='review_5',
        execution_id='exec_5',
        domain='code_projects',
        review_type='policy_gate',
        reason='policy_requires_review',
        payload={
            'title': 'Review competitor budget threat',
            'evidence': {
                'signal_type': 'competitor_budget_visibility_threat',
                'signal_evidence': {
                    'artifact_paths': {
                        'workspace': '/tmp/competitor-gap-issues',
                        'candidates': '/tmp/competitor-gap-issues/candidates.json',
                    },
                    'candidate_keys': ['trip-plan-budget-rollup'],
                    'canonical_keys': ['trip-plan-budget-rollup'],
                    'matches': [
                        {
                            'source_path': '/tmp/competitor-gap-issues/candidates.json',
                            'source_type': 'candidates',
                            'title': 'Budget overview',
                            'candidate_key': 'trip-plan-budget-rollup',
                            'matched_keys': ['trip-plan-budget-rollup'],
                            'matched_keywords': ['budget'],
                            'snippet': 'Competitor has shared expenses and budget overview.',
                        }
                    ],
                },
            },
        },
    )
    execution = Execution(
        id='exec_5',
        domain='code_projects',
        executor_type='review_only',
        plan={'proposed_actions': ['codex_task']},
    )

    text = formatter.format(review=review, execution=execution).as_text()

    assert '- artifact source file: /tmp/competitor-gap-issues/candidates.json (candidates; Budget overview)' in text
    assert '- candidate keys: trip-plan-budget-rollup' in text
    assert '- suggested action: review competitor budget evidence and decide whether budget visibility belongs on the roadmap.' in text
