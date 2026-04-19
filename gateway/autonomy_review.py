from __future__ import annotations

from autonomy.review_packets import ReviewPacketFormatter
from autonomy.store import AutonomyStore
from cli import HermesCLI


def _build_loop(store: AutonomyStore):
    cli_obj = HermesCLI.__new__(HermesCLI)
    return cli_obj._build_autonomy_execution_loop(store=store)


def list_reviews(limit: int = 5) -> list[dict]:
    store = AutonomyStore()
    try:
        formatter = ReviewPacketFormatter()
        items = []
        for review in store.list_pending_reviews()[: max(1, min(limit, 20))]:
            execution = store.get_execution(review.execution_id)
            packet = formatter.format(review=review, execution=execution)
            items.append(
                {
                    'id': review.id,
                    'title': packet.title,
                    'summary': packet.summary,
                    'reason': review.reason,
                    'approval_effect': packet.approval_effect,
                    'proposed_action': packet.proposed_action,
                }
            )
        return items
    finally:
        store.close()


def render_review_cards(items: list[dict]) -> str:
    if not items:
        return 'No pending autonomy reviews.'
    lines = [f'Autonomy review queue, {len(items)} pending:']
    for index, item in enumerate(items, start=1):
        review_id = item['id']
        lines.append(f"{index}. {item['title']}")
        lines.append(f"   ID: {review_id}")
        if item.get('summary'):
            lines.append(f"   Why: {item['summary']}")
        if item.get('proposed_action'):
            lines.append(f"   Action: {item['proposed_action']}")
        if item.get('approval_effect'):
            lines.append(f"   If approved: {item['approval_effect']}")
        lines.append(f"   Approve: /review-approve {review_id}")
        lines.append(f"   Reject: /review-reject {review_id} why")
        lines.append('')
    lines.append('Tip: run /reviews again after you approve or reject to refresh the queue.')
    return '\n'.join(lines)


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


def approve_review(review_id: str) -> dict:
    store = AutonomyStore()
    try:
        loop = _build_loop(store)
        execution = loop.execute_review(review_id=review_id)
        return {
            'review_id': review_id,
            'status': 'approved',
            'execution_id': execution.id,
            'executor_type': execution.executor_type,
        }
    finally:
        store.close()


def reject_review(review_id: str, reason: str = '') -> dict:
    store = AutonomyStore()
    try:
        loop = _build_loop(store)
        review = loop.reject_review(review_id=review_id, reason=reason)
        return {
            'review_id': review.id,
            'status': 'rejected',
            'reason': reason,
        }
    finally:
        store.close()
