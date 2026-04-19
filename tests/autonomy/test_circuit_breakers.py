from autonomy.circuit_breakers import CircuitBreakerPolicy


def test_circuit_breaker_trips_on_failures():
    breaker = CircuitBreakerPolicy(max_failures_per_domain=3, max_pending_reviews=10)
    decision = breaker.check(failed_executions=3, pending_reviews=1)
    assert decision.tripped is True
    assert decision.reason == 'too_many_failures'


def test_circuit_breaker_trips_on_review_overflow():
    breaker = CircuitBreakerPolicy(max_failures_per_domain=3, max_pending_reviews=2)
    decision = breaker.check(failed_executions=0, pending_reviews=2)
    assert decision.tripped is True
    assert decision.reason == 'review_queue_overflow'


def test_circuit_breaker_allows_healthy_state():
    breaker = CircuitBreakerPolicy(max_failures_per_domain=3, max_pending_reviews=10)
    decision = breaker.check(failed_executions=1, pending_reviews=1)
    assert decision.tripped is False
    assert decision.reason is None
