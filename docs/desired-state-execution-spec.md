# Desired-State Execution Architecture

> Architect: Claude (Opus 4.7) | April 20, 2026
> Status: Implementation-ready spec
> Audience: Coding agents executing this

---

## What We're Building

Transform Hermes from a passive assistant that only thinks when spoken to into a proactive chief of staff that:

1. Wakes on a schedule
2. Checks all desired states against the real world
3. Identifies the highest-value opportunity across all of Fernando's goals
4. Either acts on it, asks for review, or dispatches it to AutoWorkflow
5. Delivers a daily digest of progress, blockers, and recommendations
6. Feeds execution results back into its own learning and priority model

---

## Current State (what already works)

| Component | Status | Notes |
|---|---|---|
| `Goal` model with desired-state fields | ✅ Done | `why_it_matters`, `constraints`, `success_signals`, `progress_examples`, `review_thresholds`, `horizon` |
| `GoalMatrixEntry` model | ✅ Done | Links goals to assets (repos, docs, workflows, calendars) |
| `DailyDigest` model + store | ✅ Done | Persists structured digests |
| `Opportunity` with delegation routing | ✅ Done | `direct_hermes` / `hermes_review` / `autoworkflow_run` |
| `AutonomyScheduler` | ✅ Done | Fires every N minutes, respects pauses and ceilings |
| `AutonomyExecutionLoop.tick()` | ⚠️ Narrow | Only handles single-domain repo ticks |
| `gateway/autoworkflow_review.py` | ✅ Done | Can list/approve/reject AutoWorkflow review items |
| AutoWorkflow `/api/review-queue` | ✅ Done | Returns prioritized pending items |
| Config `autonomy.enabled: true` | ✅ Done | Ticks every 15 min on `code_projects` only |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    HERMES (Control Plane)                      │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Desired State Sweep (runs on scheduler tick)             │ │
│  │                                                         │ │
│  │  1. Load all active desired states                      │ │
│  │  2. For each: check signals from goal matrix assets     │ │
│  │  3. Generate/update opportunities                       │ │
│  │  4. Rank opportunities across all goals                 │ │
│  │  5. Apply policy → decide action for top N              │ │
│  │  6. Execute or delegate                                 │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Direct Exec  │  │ Hermes Review│  │ AutoWorkflow     │   │
│  │ (safe/local) │  │ (Telegram)   │  │ Delegation       │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                  │                   │             │
│         ▼                  ▼                   ▼             │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Evidence Ingestion + Learning                         │    │
│  │ (results flow back, update world state, update trust) │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Daily Digest Generator                                │    │
│  │ (runs once/day, summarizes across all desired states) │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼ (dispatch)
┌──────────────────────────────────────────────────────────────┐
│               AUTOWORKFLOW (Execution Plane)                  │
│                                                              │
│  Runs repeatable pipelines: competitor scans, feedback       │
│  intake, batch processing, issue triage                      │
│  Returns: run_id, artifacts, review items                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Desired State Sweep (`autonomy/desired_state_sweep.py` — NEW)

This is the replacement for the current single-domain `tick()` pattern. It doesn't replace `execution_loop.py`; it sits above it as the orchestrator.

**Responsibilities:**
- Called by the scheduler every tick (15 min default)
- Loads all goals where `status = 'active'`
- For each goal, loads its goal matrix entries
- For each asset in the matrix, invokes the appropriate sensor (or checks staleness)
- Collects signals into opportunity candidates
- Ranks opportunities using existing `OpportunityEngine` + cross-goal priority weighting
- For the top 1-3 opportunities:
  - If `delegation_mode == direct_hermes`: execute via the existing executor framework
  - If `delegation_mode == hermes_review`: create a review packet, deliver via Telegram
  - If `delegation_mode == autoworkflow_run`: call the AutoWorkflow executor
- Records execution results as evidence on the opportunity

**Key design decision:** The sweep does NOT execute all opportunities. It picks the top-ranked actionable ones per tick. This prevents runaway. The rest stay in the queue for next tick.

**Concurrency rule:** Only one sweep runs at a time. If the previous tick is still running, skip.

```python
class DesiredStateSweep:
    def __init__(self, *, store, sensors, executors, opportunity_engine, policy_engine):
        ...

    def run(self) -> SweepResult:
        """One full sweep across all desired states. Called by scheduler."""
        goals = self.store.list_goals(status='active')
        signals = self._collect_signals(goals)
        opportunities = self._generate_opportunities(goals, signals)
        ranked = self._rank_opportunities(opportunities)
        actions = self._decide_actions(ranked[:3])  # top 3 max per tick
        results = self._execute_actions(actions)
        return SweepResult(goals_checked=len(goals), opportunities_found=len(ranked), actions_taken=results)
```

### 2. Sensor Registry (`autonomy/sensors/registry.py` — NEW)

Currently sensors are hard-coded to repo health. The desired-state model needs sensors for different asset types.

**Phase 1 sensors (ship these):**
- `repo_health` — already exists, checks git state
- `autoworkflow_status` — NEW: hits AutoWorkflow `/api/review-queue` and `/api/workflows` to see what's pending/blocked
- `file_freshness` — NEW: checks if a file/doc has been modified recently (simple mtime check)

**Phase 2 sensors (later):**
- `github_issues` — checks issue count/staleness
- `calendar` — checks upcoming events
- `email` — checks unread count (if wired)

The registry maps `asset_type` → sensor class:
```python
SENSOR_REGISTRY = {
    'repo': RepoHealthSensor,
    'workflow': AutoWorkflowStatusSensor,
    'doc': FileFreshnessSensor,
    'system': SystemStatusSensor,
}
```

### 3. AutoWorkflow Executor (`autonomy/executors/autoworkflow_executor.py` — NEW)

Handles `delegation_mode == 'autoworkflow_run'`.

**What it does:**
- Takes an opportunity with `delegation_target` (a workflow config path or workflow ID)
- Hits AutoWorkflow's `POST /api/workflows/{id}/start` or `POST /api/workflow-definitions/{id}/launch`
- Records the run_id on the execution
- On subsequent ticks: polls the workflow status
- When workflow completes: pulls artifacts and review items back into Hermes evidence

```python
class AutoWorkflowExecutor(BaseExecutor):
    name = 'autoworkflow'

    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url
        self.api_token = api_token

    def run(self, task: ExecutionTask) -> ExecutionResult:
        """Launch or poll an AutoWorkflow pipeline."""
        ...

    def poll_status(self, run_id: str) -> dict:
        """Check if a dispatched workflow has completed."""
        ...

    def ingest_evidence(self, run_id: str) -> dict:
        """Pull workflow outputs back into Hermes as evidence."""
        ...
```

### 4. Evidence Ingestion (`autonomy/evidence.py` — NEW)

When any executor finishes (direct, review-approved, or AutoWorkflow), the evidence flows back into the system.

**Evidence record shape:**
```python
@dataclass
class Evidence:
    id: str
    opportunity_id: str
    goal_id: str
    source: str  # 'direct_execution' | 'review_approved' | 'autoworkflow_run'
    executor_run_id: str
    outcome: str  # 'success' | 'partial' | 'failed' | 'needs_review'
    artifacts: dict  # links to produced artifacts
    impact_summary: str  # one-sentence what changed
    recorded_at: str
```

Evidence should:
- Update the opportunity status (`completed`, `failed`, etc.)
- Update the goal's progress tracking (for daily digest)
- Feed into the learning engine if the execution produced a lesson
- Optionally update trust scores for the executor/delegation path

### 5. Daily Digest Generator (`autonomy/digest_generator.py` — NEW)

Runs once per day (triggered by scheduler or cron). Produces a `DailyDigest` record and delivers it via Telegram.

**Digest contents:**
- Which desired states had activity
- Top accomplishments (completed executions, shipped PRs, etc.)
- What's pending review (Hermes reviews + AutoWorkflow review queue)
- Top 3 opportunities for today (ranked, with recommended actions)
- Any drift/risks detected (goals with no activity, stuck workflows)
- What the system plans to work on next unless told otherwise

**Delivery:** Telegram message with the digest summary. Not a wall of text — structured sections, each 1-3 lines.

### 6. Gateway Integration (`gateway/run.py` modifications)

**Scheduler tick upgrade:**

Currently `_maybe_run_autonomy_scheduler_tick` calls `scheduler.trigger(domain=domain)` for each domain in `allowed_domains`. Replace with:

```python
async def _maybe_run_autonomy_scheduler_tick(self) -> list[str]:
    if not self._autonomy_enabled():
        return []
    sweep = self._get_or_create_desired_state_sweep()
    result = sweep.run()
    # If any actions produced review packets, deliver them
    for review in result.pending_reviews:
        await self._deliver_review_notification(review)
    return [f"Sweep: {result.goals_checked} goals, {result.actions_taken} actions"]
```

**Backward compatibility:** Keep the old `tick()` path available as a fallback if `desired_state_sweep` fails. The scheduler should try sweep first, fall back to legacy domain tick on error.

**Daily digest delivery:**

Add a daily trigger check in the scheduler. If it's after the configured digest time (default 8:00 AM local) and today's digest hasn't been generated yet, run the digest generator and deliver via Telegram.

### 7. Config Changes (`~/.hermes/config.yaml`)

```yaml
autonomy:
  enabled: true
  mode: desired_state  # NEW: 'desired_state' | 'legacy_domain' (fallback)
  tick_interval_minutes: 15
  max_actions_per_tick: 3
  daily_digest:
    enabled: true
    delivery_time: "08:00"  # local time
    channel: telegram  # where to deliver
  allowed_domains:
    - code_projects  # kept for backward compat
  desired_states:
    seed_on_first_run: true  # auto-seed Fernando's states if empty
  autoworkflow:
    enabled: true
    base_url: http://127.0.0.1:8882
    api_token: aw_N04GaRCry52PTXmEHHi9mJEEzL07uuPU4lVKAb4diq0
  telegram_reviews_enabled: true
```

---

## Acceptance Criteria

### AC1: Proactive Sweep
- [ ] When Hermes is running and autonomy is enabled, the desired-state sweep fires every `tick_interval_minutes` without any user interaction
- [ ] The sweep loads all active desired states, not just `code_projects`
- [ ] The sweep produces at least one opportunity per active goal that has linked sensors/assets returning signals
- [ ] The sweep respects `max_actions_per_tick` and does not execute more than N actions per cycle
- [ ] If a sweep is already running, the next tick skips gracefully

### AC2: Cross-Goal Ranking
- [ ] Opportunities are ranked by: `goal.priority × opportunity.score × urgency` (or similar weighted formula)
- [ ] A high-priority goal's medium-urgency opportunity ranks above a low-priority goal's high-urgency opportunity
- [ ] Ranking inputs are persisted on the opportunity record (not just final score)

### AC3: Delegation Routing
- [ ] An opportunity with `delegation_mode = 'direct_hermes'` executes using the repo or codex executor
- [ ] An opportunity with `delegation_mode = 'hermes_review'` creates a review packet and sends a Telegram notification
- [ ] An opportunity with `delegation_mode = 'autoworkflow_run'` calls AutoWorkflow's launch API and records the run_id
- [ ] The delegation mode is set during opportunity generation based on: risk level, whether a matching workflow exists, whether the action is repeatable

### AC4: AutoWorkflow Integration
- [ ] Hermes can launch an AutoWorkflow pipeline given a workflow ID or definition ID
- [ ] Hermes can poll a running workflow's status
- [ ] When a workflow completes, Hermes ingests the outcome as evidence on the original opportunity
- [ ] When a workflow has pending review items, Hermes surfaces them in its Telegram digest (without duplicating AutoWorkflow's own review surface)

### AC5: Evidence Loop
- [ ] Every completed execution (direct, review-approved, or AutoWorkflow) produces an evidence record
- [ ] Evidence records are linked to both the opportunity and the parent goal
- [ ] Evidence influences the daily digest (shows up as "progress" or "blocker")
- [ ] Evidence can trigger learning engine entries when notable patterns emerge

### AC6: Daily Digest
- [ ] Once per day at the configured time, Hermes generates a `DailyDigest` record
- [ ] The digest covers all active desired states, not just repo health
- [ ] The digest is delivered via Telegram as a structured message
- [ ] The digest includes: progress made, pending reviews, top opportunities for today, drift/risks
- [ ] If nothing happened (all quiet), the digest says so in one line instead of sending nothing

### AC7: Seed + Persistence
- [ ] Fernando's 5 core desired states can be seeded via a command (`/autonomy-seed-desired-states` or programmatic seed)
- [ ] Each desired state has at least 2-3 goal matrix entries linking to real assets
- [ ] Desired states persist across daemon restarts (already true via SQLite)
- [ ] The seed is idempotent (running twice doesn't duplicate)

### AC8: Backward Compatibility
- [ ] Setting `mode: legacy_domain` falls back to the current repo-only tick behavior
- [ ] All 84 existing autonomy tests continue to pass
- [ ] The gateway's `/autonomy-run` manual command still works

### AC9: Safety
- [ ] No execution fires without a policy check (existing policy engine)
- [ ] Review-required actions never auto-execute, even at high confidence
- [ ] AutoWorkflow runs are bounded by existing workflow timeout/cancel mechanisms
- [ ] The sweep logs what it considered, what it ranked, and what it chose (for auditability)
- [ ] Execution errors are caught and logged, never crash the sweep loop

---

## Fernando's Real Desired States (seed data)

```python
SEED_DESIRED_STATES = [
    {
        "id": "ds_embarka_business",
        "title": "Embarka becomes a real business",
        "domain": "code_projects",
        "priority": 100,
        "horizon": "3_months",
        "why_it_matters": "Top business priority. Revenue potential.",
        "success_signals": ["revenue", "active users", "shipped features weekly"],
        "constraints": {"no_deploy_without_review": True},
        "matrix_entries": [
            {"asset_type": "repo", "label": "Embarka repo", "locator": "/home/fefernandez/embarka"},
            {"asset_type": "workflow", "label": "Competitor gap scanner", "locator": "autoworkflow://embarka/competitor-gap-issues"},
            {"asset_type": "workflow", "label": "Feedback loop", "locator": "autoworkflow://embarka/feedback"},
        ]
    },
    {
        "id": "ds_software_compounds",
        "title": "Personal software projects compound instead of stall",
        "domain": "code_projects",
        "priority": 80,
        "horizon": "ongoing",
        "why_it_matters": "Hermes, AutoWorkflow, and OpenClaw should ship weekly, not stall.",
        "success_signals": ["weekly commits", "PRs merged", "features shipped"],
        "matrix_entries": [
            {"asset_type": "repo", "label": "Hermes", "locator": "/home/fefernandez/.hermes/hermes-agent"},
            {"asset_type": "repo", "label": "AutoWorkflow", "locator": "/home/fefernandez/autoworkflow"},
        ]
    },
    {
        "id": "ds_agentic_skill",
        "title": "Agentic workflow skill compounds weekly",
        "domain": "learning",
        "priority": 70,
        "horizon": "ongoing",
        "why_it_matters": "The meta-skill of using AI agents effectively is the highest-leverage investment.",
        "success_signals": ["new workflow shipped", "new integration wired", "documented lesson"],
        "matrix_entries": [
            {"asset_type": "doc", "label": "AutoWorkflow docs", "locator": "/home/fefernandez/autoworkflow/docs"},
            {"asset_type": "system", "label": "OpenClaw workspace", "locator": "/home/fefernandez/.openclaw/workspace"},
        ]
    },
    {
        "id": "ds_finances_observable",
        "title": "Finances become cleaner and more observable",
        "domain": "personal",
        "priority": 60,
        "horizon": "3_months",
        "why_it_matters": "Can't make investment decisions without visibility.",
        "success_signals": ["monthly review done", "budgets tracked", "anomalies caught"],
        "matrix_entries": []  # no automated assets yet
    },
    {
        "id": "ds_spanish_fluency",
        "title": "Spanish fluency by end of year",
        "domain": "learning",
        "priority": 40,
        "horizon": "12_months",
        "why_it_matters": "Family heritage, wife's first language.",
        "success_signals": ["daily practice", "conversation confidence"],
        "matrix_entries": []  # no automated assets yet
    },
]
```

---

## Implementation Phases

### Phase A: Sweep + Sensors (the core loop)
- `autonomy/desired_state_sweep.py`
- `autonomy/sensors/registry.py`
- `autonomy/sensors/autoworkflow_status.py`
- `autonomy/sensors/file_freshness.py`
- Tests for sweep logic and sensor registry
- Wire into scheduler in `gateway/run.py`

### Phase B: AutoWorkflow Executor + Evidence
- `autonomy/executors/autoworkflow_executor.py`
- `autonomy/evidence.py`
- Tests for executor launch, poll, ingest
- Wire evidence recording into execution completion

### Phase C: Daily Digest + Delivery
- `autonomy/digest_generator.py`
- Daily trigger logic in scheduler
- Telegram delivery of digest
- Tests for digest generation across multiple goals

### Phase D: Seed + Config + Polish
- `autonomy/seed.py` with Fernando's real desired states
- Config schema update for `mode: desired_state`
- `/autonomy-seed-desired-states` gateway command
- `/goals` and `/goal-matrix` display commands upgraded
- Backward compat verification (all 84 tests still pass)

---

## Execution Recommendations

**Best tool for this job:** Claude Code (`claude --model claude-opus-4-7`) running in the Hermes repo.

**Why not Codex:** This requires understanding the 3700-line `gateway/run.py`, the existing autonomy scheduler integration, and making surgical modifications to a complex async system. Codex has already stalled on this twice. Opus 4.7 handles this well because it can read the full gateway, understand the integration points, and write the wiring code with confidence.

**Phasing:** Do A first. Once the sweep runs and generates opportunities, B-D follow naturally. Phase A is the "does it wake up and think" inflection point.
