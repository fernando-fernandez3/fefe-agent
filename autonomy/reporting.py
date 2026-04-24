"""Lightweight autonomy reporting for the MVP."""

from __future__ import annotations

from dataclasses import dataclass, field

from autonomy.models import OpportunityStatus
from autonomy.store import AutonomyStore


@dataclass(slots=True)
class AutonomyReport:
    goals_total: int
    active_goals: int
    open_opportunities: int
    pending_reviews: int
    learnings_captured: int
    recent_execution_count: int
    completed_execution_count: int
    failed_execution_count: int
    verification_pass_rate: float
    top_opportunities: list[str] = field(default_factory=list)


class AutonomyReporter:
    def build_report(self, *, store: AutonomyStore, domain: str | None = None) -> AutonomyReport:
        goals = store.list_goals(domain=domain)
        opportunities = store.list_opportunities(domain=domain, status=OpportunityStatus.OPEN)
        reviews = store.list_pending_reviews(domain=domain)
        learnings = store.list_learnings(domain=domain, limit=50)
        executions = self._list_recent_executions(store=store, domain=domain)
        completed = [execution for execution in executions if execution.status.value == 'completed']
        failed = [execution for execution in executions if execution.status.value == 'failed']
        verification_pass_rate = (len(completed) / len(executions)) if executions else 0.0

        return AutonomyReport(
            goals_total=len(goals),
            active_goals=sum(1 for goal in goals if goal.status.value == 'active'),
            open_opportunities=len(opportunities),
            pending_reviews=len(reviews),
            learnings_captured=len(learnings),
            recent_execution_count=len(executions),
            completed_execution_count=len(completed),
            failed_execution_count=len(failed),
            verification_pass_rate=round(verification_pass_rate, 4),
            top_opportunities=[opportunity.title for opportunity in opportunities[:5]],
        )

    def render_text(self, report: AutonomyReport) -> str:
        top_lines = '\n'.join(f'- {title}' for title in report.top_opportunities) if report.top_opportunities else '- none'
        return (
            'Autonomy report\n'
            f'Goals: {report.goals_total} total, {report.active_goals} active\n'
            f'Open opportunities: {report.open_opportunities}\n'
            f'Pending reviews: {report.pending_reviews}\n'
            f'Executions: {report.recent_execution_count} total, {report.completed_execution_count} completed, {report.failed_execution_count} failed\n'
            f'Verification pass rate: {report.verification_pass_rate:.2%}\n'
            f'Learnings captured: {report.learnings_captured}\n'
            f'Top opportunities:\n{top_lines}'
        )

    def _list_recent_executions(self, *, store: AutonomyStore, domain: str | None = None):
        sql = 'SELECT id FROM executions'
        params: list[str] = []
        if domain is not None:
            sql += ' WHERE domain = ?'
            params.append(domain)
        sql += ' ORDER BY COALESCE(completed_at, started_at, id) DESC LIMIT 50'
        rows = store.db.fetchall(sql, tuple(params))
        return [store.get_execution(row['id']) for row in rows]
