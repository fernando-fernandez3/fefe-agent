from autonomy.store import AutonomyStore


def test_create_and_fetch_daily_digest(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    digest = store.create_daily_digest(
        digest_id='digest_2026_04_18',
        date_key='2026-04-18',
        summary='Embarka moved forward and one review is pending.',
        content={
            'progress': ['shipped a safe repo change'],
            'pending_reviews': ['review_123'],
        },
        goal_ids=['goal_embarka_business'],
        opportunity_ids=['opp_1'],
        review_ids=['review_123'],
    )

    assert digest.date_key == '2026-04-18'
    assert digest.goal_ids == ['goal_embarka_business']
    assert digest.content['pending_reviews'] == ['review_123']

    fetched = store.get_daily_digest('2026-04-18')
    assert fetched.id == 'digest_2026_04_18'

    listed = store.list_daily_digests(limit=10)
    assert [item.id for item in listed] == ['digest_2026_04_18']
    store.close()
