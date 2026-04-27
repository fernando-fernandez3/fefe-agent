from __future__ import annotations

from autonomy.review_packets import ReviewPacketFormatter
from autonomy.store import AutonomyStore


def format_review_notification(review_id: str) -> str:
    store = AutonomyStore()
    try:
        formatter = ReviewPacketFormatter()
        review = store.get_review(review_id)
        execution = store.get_execution(review.execution_id)
        packet = formatter.format(review=review, execution=execution)
        return (
            f"{packet.as_text()}\n\n"
            f"Approve: /review-approve {review_id}\n"
            f"Reject: /review-reject {review_id} why"
        )
    finally:
        store.close()
