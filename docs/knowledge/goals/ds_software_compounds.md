# Knowledge: ds_software_compounds — Personal Software Projects Compound Instead of Stall

> Research-backed decomposition for keeping a personal software portfolio shipping instead of rotting in half-finished repos.
> Last updated: 2026-04-22

---

## Goal Definition

Software compounds when projects produce reusable assets, reliable shipping habits, and clearer next steps over time.

This file uses original or canonical sources where possible, then translates them into solo-builder operating rules.

---

## Authoritative source spine

### Project selection and shaping
- Basecamp, Getting Real, “What’s your problem?”
  - https://basecamp.com/gettingreal/02.2-whats-your-problem
- Eric Ries, Lean Startup principles
  - https://theleanstartup.com/principles
- Basecamp, Shape Up, “Set appetites, not estimates”
  - https://basecamp.com/shapeup/2.2-chapter-08

### Scope control and shipping
- Basecamp, Getting Real, “Build Less”
  - https://basecamp.com/gettingreal/02.1-build-less
- Basecamp, Getting Real, “Fixed time + budget, flex scope”
  - https://basecamp.com/gettingreal/03.3-fixed-time-flex-scope
- Basecamp, Getting Real, “Launch now”
  - https://basecamp.com/gettingreal/03.7-launch-now
- Scrum Guide 2020
  - https://www.scrumguides.org/docs/scrumguide/v2020/2020-Scrum-Guide-US.pdf

### Portfolio management and flow
- Basecamp, Shape Up, “The Betting Table”
  - https://basecamp.com/shapeup/3.3-chapter-12
- Kanban University, WIP limits
  - https://kanban.university/kanban-wip-limits/
- Scaled Agile Framework, Lean Portfolio Management
  - https://scaledagileframework.com/lean-portfolio-management/
- Lean Enterprise Institute, Small Batch
  - https://www.lean.org/lexicon-terms/small-batch/

### Anti-stall discipline
- Basecamp, Getting Real, “Long lists don’t get done”
  - https://basecamp.com/gettingreal/04.6-long-lists
- Basecamp, Getting Real, “Two lists”
  - https://basecamp.com/gettingreal/03.5-two-lists

---

## What the sources directly support

### 1. Only work on projects with a clear problem
A project should begin with a concrete problem, not vague enthusiasm.

**Implication:** If a repo cannot answer “what problem is this solving, for whom?” it should not get active cycles.

### 2. Pick appetite first, then fit scope inside it
Shape Up and Getting Real both hammer the same point: time is fixed, scope flexes.

**Implication:** Solo work should be bounded before coding starts.

### 3. Shipping cadence is a control system
Scrum and Shape Up both depend on recurring increments and recurring finish lines.

**Implication:** A project without regular release points is not compounding, it is accumulating uncertainty.

### 4. Portfolio limits matter
Betting-table and WIP-limit thinking both say the same thing: too many active bets destroy flow.

**Implication:** A solo builder should actively limit concurrent projects.

### 5. Smaller batches reduce stall risk
Lean small-batch logic applies cleanly to software.

**Implication:** Shipping many small finished slices beats aiming at one giant perfect release.

---

## Operational subdomains

### 1. Project selection discipline
What to track:
- explicit problem statement
- clear user or use case
- reason this deserves an active cycle now

### 2. Scope control
What to track:
- fixed appetite for each cycle
- v1 exclusion list
- features cut vs. time extended

### 3. Shipping cadence
What to track:
- time since last deploy or real release
- whether each cycle ends in something runnable, testable, or publishable

### 4. Portfolio management
What to track:
- active bets count
- paused vs. killed vs. active state
- maintenance burden across projects

### 5. Reuse and compounding assets
What to track:
- extracted libraries, docs, skills, templates, or infrastructure shared across projects

---

## Inference layer, explicit

These are practical operating rules derived from the sources, not direct quotes:
- active WIP for personal projects should stay very low
- every active project should have a Now list and a Later list
- paused projects should be archived intentionally rather than left as ambient guilt
- a release can be public, private, internal, or even just a stable usable increment, as long as it creates real feedback

---

## Suggested thresholds, provisional

| Signal | Green | Yellow | Red |
|---|---|---|---|
| Active projects at once | 1 to 2 | 3 | 4+ |
| Last meaningful ship | < 2 weeks | 2 to 8 weeks | > 8 weeks |
| Next task clarity | immediate | vague | unknown |
| Appetite discipline | fixed time, cut scope | mixed | deadline slips by default |
| Reuse extraction | regular | occasional | almost never |

---

## How Hermes should use this file

When evaluating personal project work:
1. Is this the highest-value bet right now?
2. Does it fit inside a bounded appetite?
3. What is the smallest shippable increment?
4. Should another project be paused to make room for this?
5. What artifact will compound after this ship, code, docs, skill, template, or workflow?

If the work has no problem statement, no appetite, and no clear increment, it is stall fuel.
