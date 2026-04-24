"""Seed Fernando's desired states into the autonomy store."""
from __future__ import annotations

from autonomy.models import GoalStatus


SEED_DESIRED_STATES = [
    {
        'id': 'ds_embarka_business',
        'title': 'Embarka becomes a real business',
        'domain': 'code_projects',
        'priority': 100,
        'horizon': '3_months',
        'why_it_matters': 'Top business priority. Revenue potential.',
        'success_signals': ['revenue', 'active users', 'shipped features weekly'],
        'constraints': {
            'no_deploy_without_review': True,
            'knowledge_skill': 'goals-context/ds_embarka_business',
            'subdomains': [
                'trip_creation_ux',
                'family_differentiation',
                'retention_repeat_planning',
                'revenue_readiness',
                'discovery_cadence',
            ],
        },
        'matrix_entries': [
            {
                'id': 'matrix_embarka_repo',
                'asset_type': 'repo',
                'label': 'Embarka repo',
                'locator': '/home/fefernandez/embarka',
                'metadata': {'subdomain': 'trip_creation_ux'},
            },
            {
                'id': 'matrix_embarka_competitor_gap',
                'asset_type': 'workflow',
                'label': 'Competitor gap scanner',
                'locator': 'autoworkflow://embarka/competitor-gap-issues',
                'metadata': {
                    'subdomain': 'family_differentiation',
                    'workspace': '/home/fefernandez/embarka/.autoworkflow/competitor-gap-issues',
                    'candidates_path': '/home/fefernandez/embarka/.autoworkflow/competitor-gap-issues/candidates.json',
                    'discovered_path': '/home/fefernandez/embarka/.autoworkflow/competitor-gap-issues/discovered.jsonl',
                    'audit_summary_path': '/home/fefernandez/embarka/.autoworkflow/daily-audit/audit-summary.json',
                },
            },
            {
                'id': 'matrix_embarka_feedback',
                'asset_type': 'workflow',
                'label': 'Feedback loop',
                'locator': 'autoworkflow://embarka/feedback',
                'metadata': {
                    'subdomain': 'discovery_cadence',
                    'workspace': '/home/fefernandez/autoworkflow/.autoworkflow/feedback/embarka-intake',
                    'candidates_path': '/home/fefernandez/autoworkflow/.autoworkflow/feedback/embarka-intake/candidates.json',
                    'discovered_path': '/home/fefernandez/autoworkflow/.autoworkflow/feedback/embarka-intake/discovered.jsonl',
                    'proposal_path': '/home/fefernandez/autoworkflow/.autoworkflow/feedback/embarka-intake/draft-remediation-proposal.md',
                    'review_packet_path': '/home/fefernandez/autoworkflow/.autoworkflow/feedback/embarka-intake/weekly-product-risks.md',
                },
            },
            {
                'id': 'matrix_embarka_live',
                'asset_type': 'url',
                'label': 'Embarka live site',
                'locator': 'https://embarka.ai',
                'metadata': {'subdomain': 'trip_creation_ux'},
            },
        ],
    },
    {
        'id': 'ds_software_compounds',
        'title': 'Personal software projects compound instead of stall',
        'domain': 'code_projects',
        'priority': 80,
        'horizon': 'ongoing',
        'why_it_matters': 'Hermes, AutoWorkflow, and OpenClaw should ship weekly, not stall.',
        'success_signals': ['weekly commits', 'PRs merged', 'features shipped'],
        'constraints': {},
        'matrix_entries': [
            {'id': 'matrix_software_hermes', 'asset_type': 'repo', 'label': 'Hermes', 'locator': '/home/fefernandez/.hermes/hermes-agent'},
            {'id': 'matrix_software_autoworkflow', 'asset_type': 'repo', 'label': 'AutoWorkflow', 'locator': '/home/fefernandez/autoworkflow'},
            {'id': 'matrix_software_openclaw', 'asset_type': 'system', 'label': 'OpenClaw workspace', 'locator': '/home/fefernandez/.openclaw/workspace'},
        ],
    },
    {
        'id': 'ds_agentic_skill',
        'title': 'Agentic workflow skill compounds weekly',
        'domain': 'learning',
        'priority': 70,
        'horizon': 'ongoing',
        'why_it_matters': 'The meta-skill of using AI agents effectively is the highest-leverage investment.',
        'success_signals': ['new workflow shipped', 'new integration wired', 'documented lesson'],
        'constraints': {},
        'matrix_entries': [
            {'id': 'matrix_agentic_docs', 'asset_type': 'doc', 'label': 'AutoWorkflow docs', 'locator': '/home/fefernandez/autoworkflow/docs'},
            {'id': 'matrix_agentic_workspace', 'asset_type': 'system', 'label': 'OpenClaw workspace', 'locator': '/home/fefernandez/.openclaw/workspace'},
        ],
    },
    {
        'id': 'ds_finances_observable',
        'title': 'Finances become cleaner and more observable',
        'domain': 'personal',
        'priority': 60,
        'horizon': '3_months',
        'why_it_matters': "Can't make investment decisions without visibility.",
        'success_signals': ['monthly review done', 'budgets tracked', 'anomalies caught'],
        'constraints': {},
        'matrix_entries': [
            {'id': 'matrix_finances_docs', 'asset_type': 'doc', 'label': 'Finance notes', 'locator': '/home/fefernandez/Documents/finances'},
            {'id': 'matrix_finances_budget_system', 'asset_type': 'system', 'label': 'Budget workspace', 'locator': '/home/fefernandez/.hermes/memories'},
        ],
    },
    {
        'id': 'ds_spanish_fluency',
        'title': 'Spanish fluency by end of year',
        'domain': 'learning',
        'priority': 40,
        'horizon': '12_months',
        'why_it_matters': "Family heritage, wife's first language.",
        'success_signals': ['daily practice', 'conversation confidence'],
        'constraints': {},
        'matrix_entries': [
            {'id': 'matrix_spanish_notes', 'asset_type': 'doc', 'label': 'Spanish notes', 'locator': '/home/fefernandez/Documents/spanish'},
            {'id': 'matrix_spanish_audio', 'asset_type': 'system', 'label': 'Voice memo cache', 'locator': '/home/fefernandez/.hermes/audio_cache'},
        ],
    },
]


POLICIES = [
    {
        'policy_id': 'policy_code_projects',
        'domain': 'code_projects',
        'trust_level': 1,
        'allowed_actions': ['inspect_repo', 'codex_task', 'autoworkflow_run'],
        'approval_required_for': ['codex_task'],
    },
    {
        'policy_id': 'policy_learning',
        'domain': 'learning',
        'trust_level': 1,
        'allowed_actions': ['inspect_repo', 'autoworkflow_run'],
        'approval_required_for': [],
    },
    {
        'policy_id': 'policy_personal',
        'domain': 'personal',
        'trust_level': 1,
        'allowed_actions': ['inspect_repo', 'autoworkflow_run'],
        'approval_required_for': [],
    },
]


def seed_desired_states(store) -> dict:
    goals_created = 0
    matrix_entries_created = 0
    policies_created = 0

    for desired_state in SEED_DESIRED_STATES:
        goal_id = desired_state['id']
        try:
            store.get_goal(goal_id)
        except KeyError:
            store.create_goal(
                goal_id=goal_id,
                title=desired_state['title'],
                domain=desired_state['domain'],
                priority=desired_state['priority'],
                horizon=desired_state['horizon'],
                why_it_matters=desired_state['why_it_matters'],
                success_signals=desired_state['success_signals'],
                constraints=desired_state['constraints'],
                status=GoalStatus.ACTIVE,
            )
            goals_created += 1

        for entry in desired_state['matrix_entries']:
            try:
                store.get_goal_matrix_entry(entry['id'])
            except KeyError:
                store.add_goal_matrix_entry(
                    entry_id=entry['id'],
                    goal_id=goal_id,
                    asset_type=entry['asset_type'],
                    label=entry['label'],
                    locator=entry['locator'],
                    metadata=entry.get('metadata'),
                )
                matrix_entries_created += 1

    for policy in POLICIES:
        try:
            store.get_policy_for_domain(policy['domain'])
        except KeyError:
            store.create_policy(
                policy_id=policy['policy_id'],
                domain=policy['domain'],
                trust_level=policy['trust_level'],
                allowed_actions=policy['allowed_actions'],
                approval_required_for=policy['approval_required_for'],
                verification_required=True,
                max_parallelism=1,
            )
            policies_created += 1

    return {
        'goals_created': goals_created,
        'matrix_entries_created': matrix_entries_created,
        'policies_created': policies_created,
    }
