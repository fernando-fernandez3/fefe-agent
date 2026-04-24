from autonomy.evidence import Evidence, list_evidence_for_goal, list_evidence_for_opportunity, record_evidence
from autonomy.store import AutonomyStore


def test_record_and_list_evidence_by_goal_and_opportunity(tmp_path):
    store = AutonomyStore(tmp_path / "autonomy.db")
    store.create_goal(
        goal_id="goal_embarka",
        title="Embarka becomes a real business",
        domain="code_projects",
        priority=100,
    )
    store.upsert_opportunity(
        opportunity_id="opp_embarka",
        domain="code_projects",
        goal_id="goal_embarka",
        source_sensor="workflow_sensor",
        title="Run competitor-gap workflow",
        score=0.9,
        risk_level="low",
        confidence=0.9,
        urgency=0.8,
        expected_value=0.9,
        context_cost=0.2,
    )

    evidence = Evidence(
        id="evidence_1",
        opportunity_id="opp_embarka",
        goal_id="goal_embarka",
        source="autoworkflow_run",
        executor_run_id="run_123",
        outcome="success",
        artifacts={"report_url": "https://example.com/report"},
        impact_summary="Launched workflow and queued competitor scan.",
        recorded_at="2026-04-20T12:00:00+00:00",
    )

    recorded = record_evidence(store, evidence)

    assert recorded.id == "evidence_1"
    assert list_evidence_for_goal(store, "goal_embarka") == [recorded]
    assert list_evidence_for_opportunity(store, "opp_embarka") == [recorded]
    store.close()
