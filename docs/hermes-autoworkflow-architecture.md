# Hermes and AutoWorkflow Architecture Split

Accepted architecture for how desired-state autonomy should be divided between Hermes and AutoWorkflow.

## Short version

Hermes is the control plane.

AutoWorkflow is the execution plane for repeatable, reviewable, event-driven workflows.

Do not make AutoWorkflow the top-level brain.

## Why this split exists

The desired-state system is not just a workflow runner.

It needs:
- long-lived priorities
- cross-goal judgment
- policy by risk
- interruption discipline
- memory of what matters now
- daily digests tied to real goals
- the ability to choose among many possible next actions

That is Hermes territory.

AutoWorkflow is excellent at structured execution once the work is concrete enough to be expressed as a pipeline. It already has strong primitives for:
- scheduled and triggered runs
- batch review
- draft mode
- replay
- mutation proposals
- workflow audit
- event-sourced run history
- operator-visible review queues

That makes it the right substrate for repeated factories, not the right top-level chooser.

Reference:
- AutoWorkflow README: https://github.com/fernando-fernandez3/autoworkflow

## Core decision

Wire most of the desired-state model directly into Hermes.

Use AutoWorkflow when Hermes identifies a recurring or high-volume pattern that benefits from durable workflow structure.

Target split:
- Hermes: roughly 70 to 80 percent of the system logic
- AutoWorkflow: roughly 20 to 30 percent, focused on specialized execution pipelines

## Layer model

### Layer 1, Hermes control plane

Hermes owns:
- desired-state records
- why each state matters
- priority and horizon
- global policies and review thresholds
- goal matrix and linked assets
- signal intake across repos, notes, email, dashboards, calendars, and other surfaces
- opportunity generation and cross-goal ranking
- interruption discipline
- daily digest generation
- learnings across domains
- deciding whether to act directly, ask for review, or delegate into AutoWorkflow

Hermes answers the question:
- What is the highest-value safe thing to do for Fernando right now?

### Layer 2, Hermes native executor path

Hermes should keep its own narrow native executor for:
- safe repo inspection
- safe code changes in approved repos
- lightweight research and draft generation
- Telegram-native review packets for risky actions

This path is the fast lane for obvious low-risk actions.

It avoids the overhead of forcing every action into a workflow.

### Layer 3, AutoWorkflow execution plane

AutoWorkflow owns:
- workflows with explicit triggers
- repeated multi-step pipelines
- batch queues
- draft review loops
- replayable workflows
- workflow-local audits and mutation proposals
- durable run artifacts for specific operational streams

AutoWorkflow answers the question:
- Given this concrete repeatable job, how do we run it safely, observably, and at scale?

## Promotion rule

Do not start with a workflow.

Start in Hermes.

Promote a behavior into AutoWorkflow only when most of these are true:
- it repeats often
- it follows a stable multi-step shape
- it benefits from review queues or batch processing
- it benefits from replay or audit history
- it has clear inputs and outputs
- it is more pipeline than judgment

Good promotion examples:
- competitor scanning and synthesis
- feedback polling and issue drafting
- repeated content drafting queues
- batch ticket triage
- recurring research pipelines
- webhook-triggered or cron-triggered collection jobs

Bad promotion examples:
- broad cross-goal prioritization
- deciding what Fernando should care about today
- setting or changing desired states
- deciding whether something is worth interrupting Fernando over
- freeform strategic judgment across domains

## Decision flow

1. Hermes evaluates desired states and current signals.
2. Hermes generates ranked opportunities.
3. Hermes applies policy and risk rules.
4. Hermes chooses one of three actions:
   - act directly in Hermes
   - create a Hermes review packet
   - launch or inspect an AutoWorkflow pipeline
5. Hermes ingests the resulting evidence.
6. Hermes updates learnings and daily digest output.

## Data ownership

### Hermes-owned durable objects

Hermes should own these as first-class records:
- desired_states
- goal_matrix_entries
- global_policies
- opportunity_records
- execution_records
- review_records
- daily_digests
- learnings

### AutoWorkflow-owned durable objects

AutoWorkflow should own:
- workflow definitions
- run events
- step artifacts
- workflow review items
- workflow replay history
- audit and mutation outputs

### Integration rule

Hermes should read workflow outputs as evidence, not surrender top-level judgment to workflow state.

AutoWorkflow can recommend. Hermes decides what matters in the broader system.

## Review model

There are two distinct review surfaces.

### Hermes review

Use for:
- merges
- deploys
- purchases
- outbound messages
- destructive actions
- any action where the main question is trust or strategic appropriateness

These reviews should be tied directly to desired states and opportunity context.

### AutoWorkflow review

Use for:
- batch review
- draft approval inside a workflow
- step-specific operator checkpoints
- approving a concrete artifact produced by a repeated pipeline

These reviews are narrower and workflow-local.

Hermes may summarize or forward them, but should not collapse the two models into one indistinguishable queue.

## Existing Hermes hooks that support this split

Hermes already has:
- a native autonomy scheduler path in `gateway/run.py`
- a native autonomy review path for Telegram notifications
- an AutoWorkflow review integration in `gateway/autoworkflow_review.py`

That is good news.

It means the architecture already wants this split. We need to formalize and extend it, not rip it out.

## First implementation posture

For v1 of desired-state autonomy:
- broad model in Hermes
- narrow native executor in Hermes
- selective delegation to AutoWorkflow
- keep code-project execution as the first live autonomous domain
- expand into broader life and business domains only after the review and learning loop proves trustworthy

## Anti-patterns

Avoid these mistakes:
- shoving the whole autonomy model into AutoWorkflow YAML
- using workflow count as proof of autonomy maturity
- duplicating the same review concept in two places without clear ownership
- letting workflow-local confidence substitute for global judgment
- forcing obvious safe actions through workflow overhead
- making Hermes a thin wrapper around workflow runs

## Product sentence

Hermes decides what matters.

AutoWorkflow industrializes the work that has become repeatable.
