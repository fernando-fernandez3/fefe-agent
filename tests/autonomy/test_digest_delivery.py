from autonomy.digest_delivery import format_digest_for_telegram
from autonomy.models import DailyDigest


def test_format_digest_for_telegram_outputs_structured_plain_text_sections():
    digest = DailyDigest(
        id='digest_1',
        date_key='2026-04-20',
        summary='Embarka moved forward and one review is pending.',
        content={
            'activity': ['Embarka goal had activity in the last 24h.'],
            'accomplishments': ['Shipped workflow trigger.'],
            'pending_reviews': [{'id': 'review_1', 'title': 'Review workflow output'}],
            'top_opportunities': [{'id': 'opp_1', 'title': 'Fix workflow blockage'}],
            'drift_risks': [{'goal_id': 'goal_2', 'title': 'Spanish fluency by end of year'}],
            'next_planned_action': 'Investigate the highest-value open opportunity.',
        },
        goal_ids=['goal_1'],
        opportunity_ids=['opp_1'],
        review_ids=['review_1'],
    )

    rendered = format_digest_for_telegram(digest)

    assert 'Daily digest for 2026-04-20' in rendered
    assert 'Summary: Embarka moved forward and one review is pending.' in rendered
    assert 'Activity:' in rendered
    assert 'Pending reviews:' in rendered
    assert 'Next:' in rendered
    assert '|' not in rendered
