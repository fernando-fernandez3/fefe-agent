# Desired-State Autonomy Backlog

> For Hermes: implement this in the existing Hermes autonomy system, not as a separate sidecar. Keep the current repo-autonomy slice working while expanding the data model upward into true desired-state autonomy.

## Goal

Upgrade Hermes autonomy from narrow repo goals to a real desired-state control plane that:
- stores Fernando’s desired states durably
- links each state to concrete assets and signal sources
- ranks opportunities across goals
- decides whether to act directly, open a Hermes review, or delegate into AutoWorkflow
- ingests workflow evidence back into Hermes
- produces daily digests tied to desired states

## Current reality in code

The autonomy package already exists and works for a repo-scoped MVP:
- `autonomy/models.py` has `Goal`, `Policy`, `Signal`, `Opportunity`, `Execution`, `Review`, `Learning`
- `autonomy/db.py` creates the current SQLite schema
- `autonomy/store.py` persists the existing autonomy objects
- `autonomy/execution_loop.py` runs the repo-only one-shot loop
- `gateway/run.py` already has both Hermes autonomy hooks and AutoWorkflow review hooks

The real gap is not “build autonomy from scratch”.

The real gap is this:
- `Goal` is too thin and too repo-domain-centric for Fernando’s desired-state model
- there is no first-class goal matrix or linked asset layer
- opportunities do not yet carry delegation routing
- Hermes does not yet ingest AutoWorkflow outputs as evidence into the main autonomy state
- daily digests are not a first-class autonomy artifact

## Non-goals for this phase

Do not do these yet:
- full family/admin execution
- automatic trust promotion
- forcing all actions through AutoWorkflow
- broad UI/dashboard work beyond what is needed for inspection
- replacing the current repo sensors before the new data model lands

---

## Phase 1: Expand the autonomy data model

### Task 1.1: Introduce a first-class desired-state model

Objective: replace the current too-thin goal shape with a desired-state-capable record while preserving backward compatibility for the repo MVP.

Files:
- Modify: `autonomy/models.py`
- Modify: `autonomy/db.py`
- Modify: `autonomy/store.py`
- Test: `tests/autonomy/test_desired_state_store.py`

Required model changes:
- add `DesiredState` dataclass or evolve `Goal` carefully into this richer shape
- required fields:
  - `id`
  - `title`
  - `description`
  - `why_it_matters`
  - `domain`
  - `priority`
  - `horizon`
  - `status`
  - `constraints`
  - `success_signals`
  - `progress_examples`
  - `review_thresholds`
  - `created_at`
  - `updated_at`

Decision:
- best move is likely to keep `goals` table for continuity but expand it to represent desired states explicitly, rather than adding a second half-overlapping top-level table.

Verification:
- store can create, fetch, list, and update a desired-state-shaped goal
- existing repo-goal tests still pass or are cleanly migrated

### Task 1.2: Add goal matrix records

Objective: give each desired state a durable linked-assets layer.

Files:
- Modify: `autonomy/models.py`
- Modify: `autonomy/db.py`
- Modify: `autonomy/store.py`
- Test: `tests/autonomy/test_goal_matrix_store.py`

Add a `goal_matrix_entries` table with fields like:
- `id`
- `goal_id`
- `asset_type` (`repo`, `doc`, `dashboard`, `workflow`, `skill`, `note`, `calendar`, `email_source`, `system`)
- `label`
- `locator`
- `weight`
- `metadata_json`
- `created_at`
- `updated_at`

Required store methods:
- `add_goal_matrix_entry(...)`
- `list_goal_matrix_entries(goal_id=...)`
- `update_goal_matrix_entry(...)`
- `remove_goal_matrix_entry(...)`

Verification:
- a desired state can be linked to multiple concrete assets
- entries can be weighted and listed deterministically

### Task 1.3: Add digest records

Objective: make daily digests first-class autonomy artifacts instead of ad hoc text.

Files:
- Modify: `autonomy/models.py`
- Modify: `autonomy/db.py`
- Modify: `autonomy/store.py`
- Test: `tests/autonomy/test_digest_store.py`

Add `daily_digests` table with:
- `id`
- `date_key`
- `summary`
- `content_json`
- `goal_ids_json`
- `opportunity_ids_json`
- `review_ids_json`
- `created_at`

Required store methods:
- `create_daily_digest(...)`
- `get_daily_digest(date_key)`
- `list_daily_digests(limit=...)`

---

## Phase 2: Upgrade opportunities from repo-only to control-plane objects

### Task 2.1: Add delegation routing to opportunities

Objective: let Hermes decide whether an opportunity should be executed directly, reviewed in Hermes, or delegated into AutoWorkflow.

Files:
- Modify: `autonomy/models.py`
- Modify: `autonomy/db.py`
- Modify: `autonomy/store.py`
- Modify: `autonomy/opportunity_engine.py`
- Test: `tests/autonomy/test_opportunity_routing.py`

Add fields to `Opportunity` and `opportunities` table:
- `delegation_mode` with enum values:
  - `direct_hermes`
  - `hermes_review`
  - `autoworkflow_run`
- `delegation_target` string, nullable
- `desired_outcome` text or JSON summary

Verification:
- repo-health opportunity can still route to `direct_hermes`
- repeatable pipeline opportunity can route to `autoworkflow_run`
- risky action can route to `hermes_review`

### Task 2.2: Add cross-goal scoring inputs

Objective: stop treating opportunities as isolated sensor outputs only.

Files:
- Modify: `autonomy/opportunity_engine.py`
- Modify: `autonomy/store.py`
- Test: `tests/autonomy/test_cross_goal_scoring.py`

Scoring should start using:
- desired-state priority
- input-source weight from goal matrix
- confidence
- urgency
- expected value
- context cost
- risk

Important:
- persist the actual scoring inputs used, not just the final score

Verification:
- higher-priority desired states win ties predictably
- weighted assets influence ranking in a visible way

---

## Phase 3: Teach Hermes about AutoWorkflow as an execution substrate

### Task 3.1: Add AutoWorkflow run evidence ingestion

Objective: ingest workflow outputs back into Hermes autonomy state.

Files:
- Modify: `autonomy/models.py`
- Modify: `autonomy/store.py`
- Create or modify: `autonomy/integrations/autoworkflow.py`
- Test: `tests/autonomy/test_autoworkflow_ingestion.py`

Required behavior:
- Hermes can attach workflow run evidence to an opportunity or execution
- workflow evidence should be stored as execution verification or linked evidence, not as opaque text blobs only
- Hermes should be able to answer:
  - what workflow ran
  - what artifacts it produced
  - whether it is awaiting workflow-local review
  - whether the output changed the top-level opportunity ranking

### Task 3.2: Add delegation handoff contract

Objective: make `autoworkflow_run` a real execution path, not a placeholder enum.

Files:
- Modify: `autonomy/execution_loop.py`
- Create: `autonomy/executors/autoworkflow_executor.py`
- Test: `tests/autonomy/test_autoworkflow_executor.py`

Executor contract should support:
- workflow identifier
- workflow config path or API target
- trigger metadata
- returned run ID
- returned review item IDs when relevant

Important:
- for v1, the executor can start conservative and only launch workflows or poll existing ones
- do not bury top-level judgment in the workflow executor

---

## Phase 4: Upgrade the loop from domain-first to desired-state-first

### Task 4.1: Seed and query desired states directly

Objective: make the autonomy loop operate from desired states rather than just `domain='code_projects'`.

Files:
- Modify: `autonomy/execution_loop.py`
- Modify: `autonomy/reporting.py`
- Modify: `cli.py`
- Test: `tests/autonomy/test_execution_loop_desired_states.py`

Required behavior:
- loop can load all active desired states
- loop can collect signals from assets linked through the goal matrix
- loop can still restrict actual execution to approved domains in v1

### Task 4.2: Keep the first live executor narrow

Objective: preserve safety while broadening planning.

Files:
- Modify: `gateway/run.py`
- Modify: `autonomy/execution_loop.py`
- Test: `tests/autonomy/test_gateway_autonomy_config.py`

Rule:
- broad desired-state planning is allowed
- live autonomous execution remains primarily code-project focused until later

This is how we avoid pretending the system is broader than the executor surface actually is.

---

## Phase 5: Daily digest and operator UX

### Task 5.1: Add desired-state daily digest generator

Objective: produce one concise daily digest tied to goals, opportunities, reviews, and learnings.

Files:
- Create or modify: `autonomy/digest.py`
- Modify: `autonomy/reporting.py`
- Modify: `gateway/run.py`
- Test: `tests/autonomy/test_daily_digest.py`

Digest should include:
- desired states touched
- meaningful progress made
- new or top opportunities
- pending decisions for Fernando
- risks, drift, or blockers
- what changed since last digest

### Task 5.2: Add operator views for goal matrix and delegation state

Objective: make the system inspectable before building dashboard theater.

Files:
- Modify: `cli.py`
- Modify: `hermes_cli/commands.py`
- Test: `tests/test_cli_autonomy_commands.py`

Minimum useful commands:
- `/goals` should show desired-state-rich output
- `/opportunities` should show delegation mode
- add a lightweight `/goal-matrix` view

---

## Phase 6: Seed Fernando’s real desired states

### Task 6.1: Add an initial seed command or fixture

Objective: load Fernando’s current desired states and linked assets without manual SQL nonsense.

Files:
- Create: `autonomy/seed.py`
- Modify: `cli.py`
- Test: `tests/autonomy/test_seed_desired_states.py`

Initial desired states to seed:
- Embarka becomes a real business
- Personal software projects compound instead of stall
- Finances become cleaner and more observable
- Agentic workflow skill compounds weekly
- Spanish fluency by end of year

Seed should also support initial goal-matrix entries for:
- Hermes repo
- Embarka repo
- relevant docs under `docs/`
- AutoWorkflow configs that belong in the execution plane

---

## Suggested build order

1. expand `goals` into desired-state-capable records
2. add `goal_matrix_entries`
3. add opportunity delegation fields
4. add AutoWorkflow ingestion and delegation executor
5. update loop/reporting/CLI for desired-state-first behavior
6. add daily digests
7. add seed command for Fernando’s actual desired states

## Acceptance test for this backlog

Hermes should be able to:
- store Fernando’s desired states durably
- attach linked assets through a goal matrix
- generate ranked opportunities across desired states
- mark an opportunity as `direct_hermes`, `hermes_review`, or `autoworkflow_run`
- ingest AutoWorkflow evidence back into the same autonomy record set
- produce a daily digest tied to desired states instead of isolated repo events
- keep the first live autonomous executor narrow and safe

## Branch recommendation

Use a dedicated branch.

Suggested branch:
- `feature/desired-state-autonomy`

## Final note

Do not overcomplicate this.

The hard part is not inventing new abstractions.

The hard part is cleanly extending the autonomy package that already exists so Hermes becomes the real control plane, while AutoWorkflow stays a powerful subordinate execution system.