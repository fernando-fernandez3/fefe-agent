# Broad Autonomy MVP Backlog

> For Hermes: execute this on a dedicated branch in the Hermes repo. Keep the first live slice brutally narrow: repo autonomy only, safe local actions only, Telegram review packets for anything riskier.

## Goal
Build the first working version of a broad autonomy engine inside Hermes that can turn high-level goals into continuous repo-focused autonomous work, with durable policies, a unified opportunity queue, verification, learnings, and explicit review gates.

## Architecture
This MVP lives inside the Hermes repo and treats Hermes as the executive brain. AutoWorkflow is not the starting point. The first version should prove one loop end-to-end:
1. store goals and policies
2. sense repo opportunities
3. rank them in one queue
4. execute safe local work
5. verify outcomes
6. extract learnings
7. escalate anything risky through durable review objects

## Hard scope limits
- One live domain: code projects
- One live review channel: Telegram packets plus local inspection
- One primary executor path: Hermes direct repo work, optionally delegated subagent for implementation-heavy tasks
- No family logistics execution in v1
- No autonomous trust promotion
- No external messaging, merges, or deploys without explicit review

## Branch recommendation
Use a dedicated feature branch in the Hermes repo, not a fork.
Suggested branch name:
- `feature/broad-autonomy-mvp`

## Repo reality check
Current repo path:
- `/home/fefernandez/.hermes/hermes-agent`

Current git state when this backlog was written:
- branch: `main`
- remote: `git@github.com:NousResearch/hermes-agent.git`
- dirty files already present:
  - `docker/SOUL.md`
  - `package-lock.json`

That means do not start hacking on `main`. Branch first.

---

## Phase 0: Branching and design freeze

### Task 0.1: Create working branch
Objective: isolate autonomy MVP work from existing local changes.

Files:
- Modify: git branch state only

Steps:
1. Run:
   - `git switch -c feature/broad-autonomy-mvp`
2. Verify branch:
   - `git branch --show-current`
3. Expected output:
   - `feature/broad-autonomy-mvp`

### Task 0.2: Add docs directory and anchor documents
Objective: give the MVP a stable home inside the repo.

Files:
- Create: `docs/plans/2026-04-12-broad-autonomy-mvp-backlog.md`
- Create: `docs/plans/2026-04-12-broad-autonomy-architecture-summary.md`

Steps:
1. Keep this backlog file.
2. Create a concise architecture summary extracted from the HTML doc.
3. Include scope limits and branch strategy.

### Task 0.3: Define MVP success metrics
Objective: force the project to optimize for real value instead of platform theater.

Files:
- Modify: `docs/plans/2026-04-12-broad-autonomy-architecture-summary.md`

Success metrics:
- can store and list persistent repo goals
- can generate ranked repo opportunities from sensors
- can execute at least one safe repo task automatically
- can attach verification evidence to execution records
- can persist a review item for unsafe tasks
- can write one structured learning record after execution

---

## Phase 1: Data model and persistence foundation

### Task 1.1: Create autonomy package scaffold
Objective: create a dedicated package for the autonomy engine.

Files:
- Create: `autonomy/__init__.py`
- Create: `autonomy/models.py`
- Create: `autonomy/db.py`
- Create: `autonomy/store.py`
- Create: `autonomy/types.py`

Implementation notes:
- Follow existing Hermes SQLite style where practical
- Keep models simple, use dataclasses or pydantic only where it actually helps

### Task 1.2: Implement schema bootstrap
Objective: create a durable SQLite store for autonomy state.

Files:
- Modify: `autonomy/db.py`
- Test: `tests/autonomy/test_db_schema.py`

Tables to create:
- `goals`
- `policies`
- `signals`
- `world_state`
- `opportunities`
- `executions`
- `reviews`
- `learnings`

Important design decision:
- add `signals` now as an append-only layer
- do not let mutable world state become the only truth source

### Task 1.3: Add store APIs for goals and policies
Objective: make goals and policies the first durable primitives.

Files:
- Modify: `autonomy/store.py`
- Test: `tests/autonomy/test_goal_store.py`
- Test: `tests/autonomy/test_policy_store.py`

Required methods:
- `create_goal(...)`
- `list_goals(...)`
- `update_goal_status(...)`
- `create_policy(...)`
- `get_policy_for_domain(...)`
- `update_policy(...)`

### Task 1.4: Add lifecycle enums and validation
Objective: prevent free-form status soup.

Files:
- Modify: `autonomy/models.py`
- Test: `tests/autonomy/test_models.py`

Required lifecycle enums:
- GoalStatus
- OpportunityStatus
- ExecutionStatus
- ReviewStatus

---

## Phase 2: Repo-only sensors

### Task 2.1: Create sensor interface
Objective: standardize how sensors emit append-only signals.

Files:
- Create: `autonomy/sensors/__init__.py`
- Create: `autonomy/sensors/base.py`
- Test: `tests/autonomy/test_sensor_base.py`

Sensor contract:
- input: domain context
- output: list of normalized signal records
- every signal includes source, timestamp, entity key, signal type, evidence payload

### Task 2.2: Implement git state sensor
Objective: detect dirty repos, stale branches, and branch drift opportunities.

Files:
- Create: `autonomy/sensors/repo_git_state.py`
- Test: `tests/autonomy/test_repo_git_state_sensor.py`

Expected signals:
- dirty_worktree
- stale_branch
- detached_head
- ahead_or_behind_remote

### Task 2.3: Implement repo health sensor
Objective: detect test and verification pain points.

Files:
- Create: `autonomy/sensors/repo_health.py`
- Test: `tests/autonomy/test_repo_health_sensor.py`

Expected signals:
- failing_tests
- missing_test_command
- flaky_verification_signal
- missing_browser_qa_signal

### Task 2.4: Implement issue hotspot sensor
Objective: find likely useful maintenance work.

Files:
- Create: `autonomy/sensors/repo_hotspots.py`
- Test: `tests/autonomy/test_repo_hotspots_sensor.py`

Expected inputs:
- TODO/FIXME density
- recent bug-prone file churn
- repeated failures in same area

### Task 2.5: Persist sensor signals
Objective: every sensor run should leave an audit trail.

Files:
- Modify: `autonomy/store.py`
- Test: `tests/autonomy/test_signal_store.py`

Required methods:
- `append_signal(...)`
- `list_recent_signals(...)`

---

## Phase 3: World state and opportunity generation

### Task 3.1: Build world-state projector
Objective: materialize current repo reality from signals.

Files:
- Create: `autonomy/world_state.py`
- Test: `tests/autonomy/test_world_state_projection.py`

Important constraint:
- world state is a derived cache
- signals remain the forensic source of truth

### Task 3.2: Build opportunity model
Objective: define what an actionable item looks like.

Files:
- Modify: `autonomy/models.py`
- Test: `tests/autonomy/test_opportunity_model.py`

Required fields:
- title
- domain
- goal_id
- source_signal_ids
- risk_level
- confidence
- urgency
- expected_value
- context_cost
- score
- status

### Task 3.3: Implement opportunity engine
Objective: turn repo signals into ranked work items.

Files:
- Create: `autonomy/opportunity_engine.py`
- Test: `tests/autonomy/test_opportunity_engine.py`

Initial opportunity types:
- fix failing test slice
- inspect dirty repo state
- verify stale branch and summarize next action
- investigate hotspot file with repeated signals

### Task 3.4: Add dedupe and cooldown logic
Objective: stop the system from rediscovering the same work forever.

Files:
- Modify: `autonomy/opportunity_engine.py`
- Test: `tests/autonomy/test_opportunity_dedupe.py`

Rules:
- fingerprint opportunity by domain + entity + kind + evidence hash
- suppress duplicates during cooldown window
- suppress anything already pending review or recently executed unsuccessfully without new evidence

---

## Phase 4: Trust, review, and policy enforcement

### Task 4.1: Implement policy evaluator
Objective: separate ranking from permission checks.

Files:
- Create: `autonomy/policy_engine.py`
- Test: `tests/autonomy/test_policy_engine.py`

Required output:
- allowed_to_execute
- requires_review
- blocked_reason
- allowed_executor_types

### Task 4.2: Implement review persistence
Objective: make risky work durable and resumable.

Files:
- Modify: `autonomy/store.py`
- Test: `tests/autonomy/test_review_store.py`

Required methods:
- `create_review(...)`
- `list_pending_reviews(...)`
- `resolve_review(...)`

### Task 4.3: Add hard review classes
Objective: encode the non-negotiables.

Files:
- Modify: `autonomy/policy_engine.py`
- Test: `tests/autonomy/test_hard_review_classes.py`

Always-review actions in MVP:
- merge
- deploy
- external messaging
- trust promotion
- policy mutation
- changes to autonomy engine safety code

### Task 4.4: Add circuit breakers
Objective: fail closed when the loop starts acting weird.

Files:
- Create: `autonomy/circuit_breakers.py`
- Test: `tests/autonomy/test_circuit_breakers.py`

Breaker triggers:
- too many failed executions in same domain
- repeated verifier mismatch
- review queue age exceeds threshold
- anomaly in execution count

---

## Phase 5: Executor contract and safe repo execution

### Task 5.1: Define executor contract
Objective: make execution backends swappable instead of special-cased.

Files:
- Create: `autonomy/executors/__init__.py`
- Create: `autonomy/executors/base.py`
- Test: `tests/autonomy/test_executor_contract.py`

Required fields:
- task spec
- side effect class
- idempotency key
- verification plan
- result payload

### Task 5.2: Implement direct repo executor
Objective: provide one trusted execution path for MVP.

Files:
- Create: `autonomy/executors/repo_executor.py`
- Test: `tests/autonomy/test_repo_executor.py`

Allowed actions in MVP:
- inspect repo
- run tests
- produce patch plan
- apply safe local change
- rerun verification

Not allowed in MVP without review:
- push
- merge
- deploy
- external API mutation unrelated to verification

### Task 5.3: Add execution store
Objective: track every run durably.

Files:
- Modify: `autonomy/store.py`
- Test: `tests/autonomy/test_execution_store.py`

Required methods:
- `create_execution(...)`
- `claim_execution(...)`
- `complete_execution(...)`
- `fail_execution(...)`

Important note:
- add claim/lease semantics now to avoid duplicate ticks executing the same item

### Task 5.4: Add verifier interface
Objective: separate doing from proving.

Files:
- Create: `autonomy/verification.py`
- Test: `tests/autonomy/test_verification.py`

Verification payload should distinguish:
- execution evidence
- outcome evidence
- verifier confidence

---

## Phase 6: Execution loop

### Task 6.1: Implement one-shot autonomy tick
Objective: run the whole loop once, deterministically.

Files:
- Create: `autonomy/execution_loop.py`
- Test: `tests/autonomy/test_execution_loop_tick.py`

Tick sequence:
1. load active goals
2. run sensors
3. append signals
4. update world state
5. generate and score opportunities
6. choose top allowed opportunity
7. if review required, persist review and stop
8. otherwise create and run execution
9. verify
10. persist outcome
11. extract learning

### Task 6.2: Add scheduler wrapper
Objective: make the loop recurring, but controllable.

Files:
- Create: `autonomy/scheduler.py`
- Test: `tests/autonomy/test_scheduler.py`

Requirements:
- fixed interval mode
- manual trigger mode
- global pause
- per-domain pause
- unattended runtime ceiling

### Task 6.3: Add Telegram review packet formatter
Objective: make reviews actually useful in the real world.

Files:
- Create: `autonomy/review_packets.py`
- Test: `tests/autonomy/test_review_packets.py`

Packet contents:
- why this was selected
- evidence summary
- proposed action
- why it needs review
- what happens if approved

---

## Phase 7: Learning engine

### Task 7.1: Implement execution learning extractor
Objective: turn outcomes into structured lessons.

Files:
- Create: `autonomy/learning_engine.py`
- Test: `tests/autonomy/test_learning_engine.py`

Possible outputs:
- memory candidate
- skill candidate
- policy adjustment proposal
- workflow promotion candidate

### Task 7.2: Forbid autonomous trust promotion
Objective: stop the system from crowning itself king.

Files:
- Modify: `autonomy/learning_engine.py`
- Modify: `autonomy/policy_engine.py`
- Test: `tests/autonomy/test_no_auto_trust_promotion.py`

Rule:
- learning engine may propose trust changes
- only human review may approve promotions
- automatic downgrades and pauses are allowed

### Task 7.3: Add lightweight autonomy report
Objective: let Fernando see useful compounding, not just logs.

Files:
- Create: `autonomy/reporting.py`
- Test: `tests/autonomy/test_reporting.py`

Report should include:
- top opportunities surfaced
- work executed
- reviews created
- verification pass rate
- learnings captured
- breaker trips

---

## Phase 8: Surface area for operators

### Task 8.1: Add local inspection command(s)
Objective: make the system inspectable without building a dashboard first.

Files:
- Modify: `hermes_cli/commands.py`
- Modify: `cli.py`
- Test: `tests/hermes_cli/test_autonomy_commands.py`

Suggested commands:
- `/goals`
- `/autonomy`
- `/reviews`
- `/opportunities`

### Task 8.2: Add config hooks
Objective: let Fernando enable the loop deliberately.

Files:
- Modify: `hermes_cli/config.py`
- Test: `tests/hermes_cli/test_autonomy_config.py`

Suggested config keys:
- `autonomy.enabled`
- `autonomy.tick_interval_minutes`
- `autonomy.allowed_domains`
- `autonomy.telegram_reviews_enabled`

---

## Phase 9: MVP prove-out scenario

### Task 9.1: Seed one real repo goal
Objective: prove value on a real project.

Suggested initial goal:
- “Continuously improve Hermes repo health and reduce manual maintenance drag.”

### Task 9.2: Run supervised autonomy sessions
Objective: gather evidence before making it always-on.

Requirements:
- run manual ticks first
- review queue must work
- breaker behavior must be exercised
- at least one safe execution should complete with verification evidence

### Task 9.3: Only then enable recurring loop
Objective: move from supervised to semi-autonomous operation.

Conditions before enabling:
- review packets are good
- duplicate opportunity suppression works
- no bogus trust promotions
- at least 3 useful executions completed without bullshit or rollback

---

## Test strategy

Run focused tests as each layer lands, then full suite.

Core commands:
- `source venv/bin/activate`
- `python -m pytest tests/autonomy/ -q`
- `python -m pytest tests/hermes_cli/test_autonomy_* -q`
- `python -m pytest tests/ -q`

## Acceptance criteria for shipping MVP v1
- can persist goals and policies
- can emit and store repo signals
- can derive a ranked opportunity queue
- can gate work through policy engine
- can execute one safe repo task end-to-end
- can persist a review instead of acting when unsafe
- can write a structured learning record
- can produce a concise autonomy report
- all relevant tests pass

## Council-reviewed amendments baked into this backlog
- repo autonomy only for first live slice
- append-only signal layer included from day one
- trust promotion is human-gated only
- circuit breakers and unattended runtime ceilings required
- one executor path first, direct safe repo work

## Final take
If we build this narrowly, it will actually become useful.
If we try to solve all of life in v1, we’ll build a gorgeous pile of autonomy bullshit.
Start with repo autonomy, earn trust, then widen the circle.
