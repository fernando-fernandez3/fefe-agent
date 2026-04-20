# Codex Phase Instructions

Branch: `feature/desired-state-sweep`
Full spec: `docs/desired-state-execution-spec.md`
Backlog context: `docs/plans/2026-04-18-desired-state-autonomy-backlog.md`

All work goes on the same branch. Commit, push, and run tests after each phase.
Test command: `python3 -m pytest tests/autonomy/ -x -q --tb=short -o "addopts="`

---

## Phase B: AutoWorkflow Executor + Evidence

**Create these files:**

1. `autonomy/executors/autoworkflow_executor.py` — Executor for `delegation_mode == 'autoworkflow_run'`. Follows `BaseExecutor` contract in `autonomy/executors/base.py`. Uses httpx to POST to AutoWorkflow's launch API. Accepts base_url + api_token as constructor args or from env vars `AUTOWORKFLOW_BASE_URL` / `AUTOWORKFLOW_API_TOKEN`. Returns run_id in outcome on success. Handles connection errors gracefully.

2. `autonomy/evidence.py` — Evidence dataclass (id, opportunity_id, goal_id, source, executor_run_id, outcome, artifacts, impact_summary, recorded_at). Functions: `record_evidence(store, evidence)`, `list_evidence_for_goal(store, goal_id)`, `list_evidence_for_opportunity(store, opportunity_id)`.

3. `tests/autonomy/test_autoworkflow_executor.py` — Mock httpx, test success/failure/missing-target.

4. `tests/autonomy/test_evidence.py` — Test record + list against temp DB.

**Modify these files:**

5. `autonomy/db.py` — Add `evidence` table matching the Evidence dataclass. Add indexes on goal_id and opportunity_id.

6. `autonomy/store.py` — Add `create_evidence()`, `list_evidence_by_goal()`, `list_evidence_by_opportunity()`.

7. `autonomy/desired_state_sweep.py` — After successful execution or autoworkflow dispatch, call `record_evidence()`.

**Commit message:** `feat(autonomy): add AutoWorkflow executor and evidence ingestion`

---

## Phase C: Daily Digest + Delivery

**Create these files:**

1. `autonomy/digest_generator.py` — `DigestGenerator` class. `generate(self) -> DailyDigest`. Covers: activity in last 24h, accomplishments, pending reviews, top 3 opportunities, drift/risks (goals with no activity 7+ days), next planned action. Idempotent (returns existing digest if already generated today).

2. `autonomy/digest_delivery.py` — `format_digest_for_telegram(digest: DailyDigest) -> str`. Plain text, structured sections, 1-3 lines each. No markdown tables.

3. `tests/autonomy/test_daily_digest.py` — Test generation with/without activity, idempotency.

4. `tests/autonomy/test_digest_delivery.py` — Test Telegram formatter output.

**Modify these files:**

5. `gateway/run.py` — After `_maybe_run_autonomy_scheduler_tick`, check if past configured digest time (default 08:00 local) and today's digest not generated. If so, generate + deliver via Telegram. Read config from `autonomy.daily_digest.delivery_time` and `autonomy.daily_digest.channel`.

**Commit message:** `feat(autonomy): add daily digest generator with Telegram delivery`

---

## Phase D: Seed + Config + CLI

**Create these files:**

1. `autonomy/seed.py` — `seed_desired_states(store) -> dict`. Seeds 5 desired states + matrix entries + policies for learning/personal domains. Idempotent. See the seed data in `docs/desired-state-execution-spec.md` under "Fernando's Real Desired States".

2. `tests/autonomy/test_seed_desired_states.py` — Test creates 5 goals, correct matrix entries, idempotent, policies exist.

**Modify these files:**

3. `gateway/run.py` — In `_handle_gateway_autonomy_seed_command`, also call `seed_desired_states(store)` and report count.

4. `cli.py` — Add/upgrade `/goals` command (prints desired states: title, priority, status, horizon, # matrix entries) and `/goal-matrix` command (prints entries grouped by goal).

5. `hermes_cli/config.py` — Recognize `autonomy.mode`, `autonomy.max_actions_per_tick`, `autonomy.daily_digest.enabled`, `autonomy.daily_digest.delivery_time`, `autonomy.daily_digest.channel`.

**Commit message:** `feat(autonomy): add desired-state seed, config schema, and CLI commands`
