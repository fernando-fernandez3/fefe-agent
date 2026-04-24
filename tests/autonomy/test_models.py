from autonomy.models import ExecutionStatus, GoalStatus, OpportunityStatus, ReviewStatus


def test_lifecycle_enums_have_expected_values():
    assert GoalStatus.ACTIVE.value == 'active'
    assert OpportunityStatus.REVIEW_REQUIRED.value == 'review_required'
    assert ExecutionStatus.CLAIMED.value == 'claimed'
    assert ReviewStatus.APPROVED.value == 'approved'
