"""Initial circuit breaker helpers for autonomy MVP."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CircuitBreakerDecision:
    tripped: bool
    reason: str | None = None


class CircuitBreakerPolicy:
    def __init__(self, *, max_failures_per_domain: int = 3, max_pending_reviews: int = 10):
        self.max_failures_per_domain = max_failures_per_domain
        self.max_pending_reviews = max_pending_reviews

    def check(self, *, failed_executions: int, pending_reviews: int) -> CircuitBreakerDecision:
        if failed_executions >= self.max_failures_per_domain:
            return CircuitBreakerDecision(tripped=True, reason='too_many_failures')
        if pending_reviews >= self.max_pending_reviews:
            return CircuitBreakerDecision(tripped=True, reason='review_queue_overflow')
        return CircuitBreakerDecision(tripped=False, reason=None)
