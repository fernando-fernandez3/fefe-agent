# Hermes to AutoWorkflow Mapping

Working map of which jobs belong directly in Hermes versus inside AutoWorkflow.

## Rule of thumb

If the task is mostly judgment, prioritization, cross-goal reasoning, or interruption policy, keep it in Hermes.

If the task is mostly a repeatable pipeline with stable inputs, stable outputs, and operator review value, put it in AutoWorkflow.

## Current examples

### 1. Embarka competitor gap issues

Config:
- `/home/fefernandez/embarka/autoworkflow-competitor-gap-issues.yml`

What it does:
- scheduled discovery from Reddit and feeds
- synthesizes ranked gap candidates
- drafts an issue
- audits the artifacts
- pauses for approval before issue creation

Verdict:
- Keep in AutoWorkflow

Why:
- clearly repeatable
- cron-based
- multi-step
- artifact-heavy
- approval-gated
- benefits from workflow-local audit and replay

Hermes should own:
- deciding that Embarka is a top desired state
- deciding this workflow is worth running and monitoring
- interpreting resulting issue candidates against broader product priorities
- deciding whether competitor-gap work outranks other Embarka opportunities

AutoWorkflow should own:
- the collection, synthesis, draft, audit, and create-issue pipeline

### 2. Ticket triage example

Config:
- `/home/fefernandez/autoworkflow/examples/ticket-triage/autoworkflow.yml`

Verdict:
- AutoWorkflow pattern

Why:
- batch workflow
- draft mode
- approval loop
- stable queue-processing shape

This is basically the canonical AutoWorkflow job type.

### 3. Embarka bug fixer example

Config:
- `/home/fefernandez/autoworkflow/examples/embarka-bug-fixer/autoworkflow.yml`

Verdict:
- Hybrid, but primary home is Hermes-first

Why:
- fixing one bug is often still judgment-heavy and close to Hermes’s native repo autonomy path
- if it becomes a repeated factory job fed from a queue, then AutoWorkflow becomes more valuable

Practical rule:
- one-off or high-judgment bug selection, Hermes
- repeated queued bug-fix pipeline with standard validation and review, AutoWorkflow

## Desired-state ownership map

### Keep directly in Hermes

- desired states and priorities
- goal matrix
- per-goal linked assets
- cross-goal opportunity ranking
- deciding what to work on next
- deciding when not to interrupt Fernando
- daily digest generation
- cross-domain learnings
- review thresholds and trust policy
- direct Telegram review packets for strategic approvals

### Push into AutoWorkflow

- recurring competitor scans
- recurring feedback intake and synthesis
- repeated draft queues
- event-driven issue drafting
- recurring audit/report pipelines
- batch research ingestion
- webhook-triggered processing flows
- replay-worthy collection and transformation pipelines

### Hybrid zone

These start in Hermes and get promoted later if they repeat enough:
- code issue remediation
- content production loops
- research brief generation
- financial anomaly reporting pipelines
- Spanish practice content pipelines

## Promotion checklist

Promote a Hermes pattern to AutoWorkflow when:
- it ran at least a few times with nearly the same structure
- the inputs and outputs are now stable
- replay would help debug it
- operator review benefits from workflow artifacts
- batching would save attention
- the work is becoming operational instead of strategic

Keep it in Hermes when:
- the real challenge is deciding whether the work matters
- the task needs cross-goal tradeoffs
- the output is highly context-sensitive
- the action is small enough that workflow overhead is stupid

## Immediate build direction

1. Expand Hermes autonomy from repo goals to desired states.
2. Add a goal matrix with linked assets.
3. Add a delegation field on opportunities:
   - `direct_hermes`
   - `hermes_review`
   - `autoworkflow_run`
4. Add ingestion of AutoWorkflow run outputs back into Hermes evidence.
5. Keep the first promotion target focused on Embarka and product research workflows.

## Immediate candidates for AutoWorkflow under this model

Best current candidates:
- Embarka competitor gap issues
- Embarka feedback polling and synthesis
- content draft queues
- repeated research digests

Best current candidates to keep direct in Hermes:
- top-level daily prioritization
- deciding which desired state to push today
- deciding which surfaced issue or proposal deserves Fernando’s attention
- safe repo work inside the Hermes repo itself

## Bottom line

Hermes should feel like your chief of staff.

AutoWorkflow should feel like the specialized operations team Hermes dispatches when a job is repetitive enough to deserve its own factory.