# Desired-State Autonomy Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Turn the current autonomy system from a repo-health-heavy MVP into a real desired-state engine that can continuously move goals like Embarka forward.

**Architecture:** Keep desired states as the top-level primitive, use sensors to emit append-only signals, derive world state, rank opportunities, policy-gate execution, verify outcomes, and persist learnings. Keep Hermes as the control plane and promote repeatable work into workflows only after the pattern is stable.

**Tech Stack:** Hermes autonomy engine, SQLite (`~/.hermes/autonomy.db`), Telegram review flow, Codex executor, OpenClaw/Hermes gateway scheduler.

---

## Current Intended Flow

1. **Desired states are defined**
   - Example: `Embarka becomes a real business`
   - Stored live in `~/.hermes/autonomy.db`, table `goals`

2. **Sensors watch reality**
   - Repos, product signals, feedback, competitors, failures, TODO drift, and other domain inputs emit append-only signals

3. **World state is derived**
   - Signals are projected into a materialized view of current reality

4. **Opportunity engine ranks moves**
   - Example opportunities:
     - failing tests in a repo
     - no tests configured
     - competitor shipped a new feature
     - feedback indicates onboarding friction

5. **Policy gate decides what is allowed**
   - Safe low-risk actions can auto-run
   - Implementation work routes to review
   - Risky or external actions remain human-gated

6. **Execution happens**
   - Safe executor, for example `inspect_repo`
   - Bounded implementation executor, for example `codex_task`

7. **Verification happens**
   - The system should prove the action materially helped, not just that a command completed

8. **Review and learning are persisted**
   - Review packets are sent when needed
   - Outcomes and learnings are stored so the system compounds

9. **Scheduler repeats the loop**
   - The loop should run reliably and continuously, not only on manual trigger

---

## Short Honest Status

The current system is good at **repo autonomy with human-gated implementation**.

It is **not yet** a full desired-state autonomy engine.

The architecture is mostly right, but the sensing, goal operationalization, verification, and recurring reliability are still too narrow.

---

## What Already Exists

- goals table in `~/.hermes/autonomy.db`
- signals, opportunities, executions, reviews, and learnings
- desired-state sweep
- repo-health sensing
- Codex review path
- CLI/operator commands
- partial Telegram review wiring
- recent fixes for missing `repo_path` propagation and false-positive `failing_tests`

---

## What Is Still Missing

### 1. Desired states are not operational enough

Current goals exist, but they are too thin.

Missing:
- stronger per-goal metadata
- explicit success metrics
- constraints and off-limits actions
- review thresholds
- better decomposition into subdomains

Example for Embarka:
- product quality
- growth and distribution
- competitor tracking
- feedback intake
- conversion and revenue
- shipping cadence

Right now, broad goals are stored, but not broken down enough for consistent steering.

### 2. Sensors are still too repo-centric

The current system is strongest around repo health.

Missing for real Embarka autonomy:
- feedback sensors
- analytics and conversion sensors
- competitor-change sensors
- production-health sensors
- backlog or issue drift sensors
- customer-signal ingestion

The system can notice failing tests. It is weaker at noticing slipping product outcomes.

### 3. Opportunity generation is too narrow

Current opportunities are mostly infra and code shaped.

Missing:
- product opportunities
- research opportunities
- growth opportunities
- content and launch opportunities
- feedback-synthesis opportunities

A broad autonomy engine needs to surface more than coding chores.

### 4. Verification is too weak

A lot of autonomy systems stop at:
- command succeeded
- tests passed
- no exception occurred

That is not enough.

Missing:
- goal-level verification
- proof the action materially helped Embarka
- production smoke checks
- post-action evidence capture
- longitudinal impact tracking

Without stronger verification, the system will optimize for activity instead of progress.

### 5. Review packets are not yet cross-domain decision-ready

For code tasks, they are decent. For broader autonomy, still weak.

Missing:
- why this move matters to the desired state
- expected outcome
- rollback and risk statement
- confidence level
- approval effect in plain language

Telegram review packets should be understandable in seconds.

### 6. Recurring autonomy is not reliable enough yet

Missing:
- dependable scheduled ticks
- robust Telegram delivery
- retry and circuit-breaker behavior
- fewer silent failures
- better observability

If the loop cannot run reliably, it is not real autonomy.

### 7. Workflow promotion path is not fully defined

Ideal split:
- Hermes decides what matters
- stable repeated patterns get promoted into AutoWorkflow
- workflows handle repeatable execution
- Hermes remains the control plane

Missing:
- explicit promotion rules
- handoff contract
- feedback path from workflow results back into goal progress

### 8. Cross-domain prioritization is still immature

When the system sees:
- Embarka issues
- repo hygiene issues
- finance cleanup
- family/admin tasks

it needs a sane prioritization mechanism.

Missing:
- cross-goal priority arbitration
- leverage versus urgency versus effort weighting
- interruption discipline

Without that, the system will thrash.

---

## Recommended Build Order

### Phase 1: Harden the goal model

**Objective:** Turn broad desired states into operational steering objects.

Tasks:
1. Expand goal schema to support:
   - objective
   - success metrics
   - constraints
   - subdomains
   - allowed auto-actions
   - approval-required actions
   - review thresholds
   - sensor sources
2. Update goal onboarding so broad goals get decomposed instead of stored as thin text blobs
3. Backfill existing high-value goals, starting with Embarka
4. Add regression tests for goal persistence and partial conversational updates

**Done when:** A goal like `ds_embarka_business` is actionable without manual interpretation each tick.

### Phase 2: Add Embarka-specific sensing

**Objective:** Give the system real visibility into product progress, not just repo health.

Tasks:
1. Add feedback intake sensor
2. Add competitor-change sensor
3. Add production-health sensor
4. Add shipping-cadence sensor
5. Add backlog or issue-drift sensor
6. Normalize these into append-only signals

**Done when:** The system can detect product, growth, and feedback opportunities for Embarka without being asked.

### Phase 3: Expand opportunity generation

**Objective:** Surface moves that are broader than implementation chores.

Tasks:
1. Add product opportunity types
2. Add research opportunity types
3. Add growth opportunity types
4. Add UX and onboarding opportunity types
5. Add content and launch opportunity types
6. Score them conservatively against the desired state and current constraints

**Done when:** The top opportunities list contains meaningful business and product actions, not just repo maintenance.

### Phase 4: Strengthen verification

**Objective:** Prove that completed actions moved the desired state forward.

Tasks:
1. Separate execution evidence from outcome evidence
2. Add goal-level verification hooks
3. Add production smoke verification where relevant
4. Add post-action evidence capture
5. Persist impact summaries over time

**Done when:** Completed actions can be audited against actual desired-state movement.

### Phase 5: Make recurring autonomy reliable

**Objective:** Ensure the loop actually runs unattended and can be trusted.

Tasks:
1. Harden scheduler reliability
2. Harden Telegram review delivery
3. Add retry behavior for transient failures
4. Add circuit breakers and pause controls
5. Add observability for failed ticks, dropped reviews, and executor stalls

**Done when:** The system can run unattended without silently dropping work or hanging.

### Phase 6: Define workflow promotion path

**Objective:** Let Hermes stay strategic while AutoWorkflow handles stable repeatable work.

Tasks:
1. Define criteria for promoting a repeated pattern into a workflow
2. Define workflow handoff payload shape
3. Define result-ingestion path back into goal progress and learnings
4. Add at least one real promoted workflow for Embarka

**Done when:** Hermes can discover repeated work and hand it off without losing strategic context.

### Phase 7: Improve cross-domain prioritization

**Objective:** Stop everything from competing as if it matters equally.

Tasks:
1. Add top-level priority arbitration across goals
2. Model leverage, urgency, effort, risk, and interruption cost explicitly
3. Add user-visible reasoning for why one opportunity outranked another
4. Add budget limits so low-value churn does not crowd out strategic work

**Done when:** The engine consistently picks the next best move across domains.

---

## Embarka Should Be the First Real Desired-State Target

Start with `ds_embarka_business`.

Convert it from a broad statement into an operational goal spec with:
- objective
- success metrics
- constraints
- subdomains
- allowed auto-actions
- approval-required actions
- sensor sources

Suggested first subdomains:
- product quality
- trip creation UX
- feedback intake
- competitor tracking
- conversion and growth
- production health
- shipping cadence

Suggested first sensors:
- feedback ingestion
- competitor monitoring
- production smoke and uptime

This is the fastest path from “goal stored in SQLite” to “system can actually steer against it.”

---

## Practical Summary

The current autonomy loop is a strong narrow MVP.

To become the thing we actually want, it needs:
- richer goal definitions
- broader sensing
- broader opportunity generation
- stronger verification
- reliable recurring execution
- a clean workflow-promotion path
- better cross-domain prioritization

---

## Recommended Immediate Next Step

Write and persist an **Embarka operational goal spec** for `ds_embarka_business`, then wire the first three Embarka-specific sensors against it.

That turns the current autonomy system from a clever repo loop into an engine that can start making real product progress.
