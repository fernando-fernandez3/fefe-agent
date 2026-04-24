from autonomy.models import OpportunityStatus


def test_opportunity_status_enum_values():
    assert OpportunityStatus.OPEN.value == 'open'
    assert OpportunityStatus.REVIEW_REQUIRED.value == 'review_required'
