# Desired-State Autonomy Progress

> Checkpoint file. Read this first at session start to resume where we left off.
> Each task has: `[status]` — pending | in-progress | done | paused
>
> Session that created this: 2026-04-22
> Source plan: `docs/plans/2026-04-22-desired-state-autonomy-plan.md`
> Scope: Knowledge layer upgraded, active skill promotion complete, DB enrichment materially complete, Embarka normalization started. Structured Embarka sensing is now partially wired.

---

## Infrastructure

- [done] Create `docs/knowledge/goals/` directory
- [done] Create `skills/goals-context/` directory
- [done] Create this checkpoint file
- [done] Upgrade goal knowledge files to require direct URLs and explicit inference labeling
- [done] Upgrade matching skill files to point back to the stronger knowledge layer
- [done] Promote the 7 goal-context skills into the active Hermes skill registry under `~/.hermes/skills/goals-context/`

---

## Goal 1: ds_embarka_business

- [done] Replace weak blog-style sourcing with authoritative PM / growth / UX / discovery sources
- [done] Add direct URLs for the source spine
- [done] Mark Embarka-specific metrics and moat claims as inference where appropriate
- [done] Rewrite knowledge file and matching skill
- [done] Update DB goal record with operational description, subdomains, active knowledge skill reference, and knowledge doc reference
- [done] Add matrix entry for the knowledge doc
- [done] Restore repo matrix entry so the desired-state sweep can see the Embarka repo directly
- [done] Add explicit Embarka subdomain metadata to repo / workflow / live-site / knowledge-doc matrix entries
- [done] Add URL sensing for the Embarka live site (`asset_type='url'`)
- [done] Make opportunity generation use matrix context like `subdomain`, `asset_label`, and `matrix_entry_id`
- [done] Normalize overlapping Embarka goals by pausing `goal_embarka_health` and treating `ds_embarka_business` as canonical
- [done] Extend AutoWorkflow sensing so feedback and competitor workflows can emit structured Embarka signals
- [done] Add first structured signals:
  - `feedback_onboarding_friction`
  - `feedback_family_constraint_gap`
  - `competitor_family_feature_threat`
  - `competitor_positioning_shift`
- [done] Route those structured signals into reviewable product opportunities instead of generic repo actions

## Goal 2: ds_software_compounds

- [done] Replace community / SEO-heavy sourcing with Basecamp, Lean, Kanban, and canonical portfolio-flow sources
- [done] Add direct URLs
- [done] Rewrite knowledge file and matching skill
- [done] Update DB goal record with operational description, subdomains, active knowledge skill reference, and knowledge doc reference
- [done] Add matrix entry for the knowledge doc

## Goal 3: ds_finances_observable

- [done] Replace vendor-blog-heavy sourcing with CFPB / FTC / FDIC / Fed / IRS anchors
- [done] Add direct URLs
- [done] Rewrite knowledge file and matching skill
- [done] Update DB goal record with operational description, subdomains, active knowledge skill reference, and knowledge doc reference
- [done] Add matrix entry for the knowledge doc

## Goal 4: ds_agentic_skill

- [done] Replace weak trend-piece sourcing with primary AI engineering, eval, MCP, and deliberate-practice sources
- [done] Add direct URLs
- [done] Rewrite knowledge file and matching skill
- [done] Update DB goal record with operational description, subdomains, active knowledge skill reference, and knowledge doc reference
- [done] Add matrix entry for the knowledge doc

## Goal 5: ds_spanish_fluency

- [done] Replace generic language-learning sources with SLA researchers and official proficiency frameworks
- [done] Add direct URLs
- [done] Rewrite knowledge file and matching skill
- [done] Update DB goal record with operational description, subdomains, active knowledge skill reference, and knowledge doc reference
- [done] Add matrix entry for the knowledge doc

## Goal 6: ds_ultimate_father

- [done] Replace weak fatherhood sourcing with developmental science, parenting guidance, and pediatric sources
- [done] Add direct URLs
- [done] Rewrite knowledge file and matching skill
- [done] Update DB goal record with operational description, subdomains, active knowledge skill reference, and knowledge doc reference
- [done] Add matrix entry for the knowledge doc

## Goal 7: ds_ultimate_husband

- [done] Replace vague relationship sourcing with peer-reviewed relationship-science sources and validated measures
- [done] Add direct URLs
- [done] Rewrite knowledge file and matching skill
- [done] Update DB goal record with operational description, subdomains, active knowledge skill reference, and knowledge doc reference
- [done] Add matrix entry for the knowledge doc

---

## Verification completed

- [done] `skills_list(category='goals-context')` shows all 7 promoted goal-context skills
- [done] `ds_embarka_business` DB row points at the active skill and knowledge doc and includes operational subdomains
- [done] `goal_embarka_health` is paused as an overlapping non-canonical Embarka goal
- [done] Embarka matrix entries now carry subdomain metadata
- [done] Added tests for:
  - URL sensor behavior
  - sensor registry `url` mapping
  - healthy-signal suppression in opportunity generation
  - subdomain-aware workflow failure titles/routing
  - persistence of matrix-entry context into opportunity evidence
  - structured AutoWorkflow feedback / competitor signal extraction
- [done] Targeted autonomy test slice passes (`21 passed`)

---

## Current state

As of 2026-04-22:
- all 7 goal knowledge files exist
- all 7 matching goal-context skill files exist
- all 7 are promoted into the active Hermes skill registry and show up in `skills_list(category='goals-context')`
- all 7 goal DB rows reference:
  - the active skill name
  - the knowledge doc path
  - the operational subdomains
- all 7 goals have doc matrix entries pointing at their knowledge files
- `ds_embarka_business` is now the canonical Embarka desired-state goal
- `goal_embarka_health` is paused to stop split-brain ranking
- desired-state sweep now preserves matrix-entry context into signal/opportunity evidence
- desired-state sweep can sense `url` assets, which makes the Embarka live site a real input instead of dead metadata
- healthy signals like `site_healthy`, `system_present`, `doc_recently_modified`, and `workflows_running` are ignored instead of cluttering the opportunity queue
- AutoWorkflow review items for Embarka feedback and competitor-gap workflows can now emit first-pass semantic product signals instead of only generic workflow-health signals

- artifact-driven Embarka semantic sensing is now partially wired:
- schema-aware candidate parsing is now partially wired on top of artifact sensing:
- direct structured feedback parsing is now partially wired when feedback artifacts include `canonical_key` / `implementation_hint`
  - direct feedback-derived signals now include:
    - `feedback_family_logistics_gap`
    - `feedback_trip_memory_gap`
    - `feedback_collaboration_gap`
    - `feedback_booking_confidence_gap`
  - competitor candidate keys now map to tighter threats like:
    - `competitor_trip_change_management_threat`
  - feedback artifact text now maps to tighter gaps like:
    - `feedback_itinerary_editing_gap`
    - `feedback_family_profile_capture_gap`
    - `feedback_booking_readiness_gap`
  - competitor workflow artifacts at `/home/fefernandez/embarka/.autoworkflow/competitor-gap-issues/`
  - feedback workflow artifacts at `/home/fefernandez/autoworkflow/.autoworkflow/feedback/embarka-intake/`
- artifact-derived signals now include:
  - `feedback_mobile_usability_gap`
  - `feedback_trip_output_trust_gap`
  - `competitor_collaboration_feature_threat`
  - `competitor_budget_visibility_threat`

---

## Remaining work

- [done] strengthen structured-signal extraction by reading richer workflow artifacts instead of only review-queue text heuristics
  - feedback artifacts now read candidate keys from `candidates.json` as well as canonical keys from `discovered.jsonl`
  - feedback and competitor artifact evidence now carries filtered per-signal matches with source path/type, matched keys/keywords, and snippets
- [done] add richer Embarka-specific signals beyond the first four, likely around trip-output trust, mobile usability, and booking/conversion friction
- decide whether structured competitor/feedback signals should stay review-only or sometimes dispatch AutoWorkflow directly
- decide whether `doc_stale` opportunities should remain review-only or eventually route into a lightweight maintenance executor
- normalize any future broad-goal onboarding so it does not create a second overlapping Embarka goal again
- consider whether family `journal` assets need a dedicated sensor instead of staying as currently inert matrix types

---

## Notes for next session

- Knowledge files live at `docs/knowledge/goals/ds_*.md`
- Active skills live at `~/.hermes/skills/goals-context/ds_*/SKILL.md`
- Repo-local source skills still exist at `hermes-agent/skills/goals-context/ds_*/SKILL.md`
- The new standard is: authoritative source spine, direct URLs, explicit inference boundaries, operational subdomains, active skill promotion, DB references to the knowledge layer, matrix-entry metadata preserved into opportunities, and structured Embarka signals where workflow text makes them obvious
- The next meaningful phase is better semantic extraction from real workflow artifacts, starting with Embarka feedback and competitor outputs
