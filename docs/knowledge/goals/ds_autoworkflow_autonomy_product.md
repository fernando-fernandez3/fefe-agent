# Knowledge: ds_autoworkflow_autonomy_product — Autoworkflow and Autonomy Platform Ships and Matures

> Research-backed decomposition for the meta-leverage layer: the autoworkflow + autonomy platforms (fefe-agent / Hermes integration) that direct many AI subscriptions on goals that compound.
> Standard: authoritative agent-design and reliability sources first, platform-specific implications second, explicit inference labels always.
> Last updated: 2026-04-25

---

## Goal Definition

This is the platform that lets one human direct many AI subscriptions (Anthropic, OpenAI, others) on goals that compound. It includes:

- Desired-state sweeps that detect drift between intent and reality
- Opportunity scoring that picks the next best action
- Policy enforcement that respects domain trust levels
- Executor reliability across Codex, Claude, and other backends
- Review surfaces (digest, review packets, war room) that keep the human in the loop without becoming the bottleneck
- Sensors and learning loops that improve the system as it runs

The platform is healthy when it produces useful work overnight, surfaces only what needs review, and never silently fails.

---

## Authoritative source spine

### Agent design and architecture
- Anthropic, Building Effective Agents
  - https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, Claude Computer Use research
  - https://www.anthropic.com/news/3-5-models-and-computer-use
- OpenAI, Practices for Governing Agentic AI Systems
  - https://openai.com/index/practices-for-governing-agentic-ai-systems/
- LangChain, LangGraph documentation (multi-agent orchestration patterns)
  - https://langchain-ai.github.io/langgraph/

### Reliability and operability
- Google, Site Reliability Engineering book (especially monitoring and toil)
  - https://sre.google/books/
- Google, Site Reliability Workbook
  - https://sre.google/workbook/table-of-contents/

### Product loop and discovery
- Eric Ries, Lean Startup principles
  - https://theleanstartup.com/principles
- Marty Cagan / SVPG, product operating model
  - https://www.svpg.com/product-operating-model/
- Teresa Torres, continuous discovery habits
  - https://www.producttalk.org/2021/08/continuous-discovery-habits/

### Human-in-the-loop and trust calibration
- DARPA Explainable AI program overview
  - https://www.darpa.mil/program/explainable-artificial-intelligence
- NIST AI Risk Management Framework
  - https://www.nist.gov/itl/ai-risk-management-framework

---

## What the sources directly support

### 1. Agents should be composed, not monolithic
**Source-backed point:** Anthropic's agent guidance separates workflows (predictable orchestration) from agents (LLM-driven decisions). The right architecture mixes both: deterministic flow for high-confidence steps, model decisions only where they earn their cost.

**Platform implication:** autoworkflow handles deterministic flow; fefe-agent (Hermes) handles judgment calls. Don't blur the line. Every model call inside autoworkflow should be defensible against "could this be a deterministic step?"

### 2. Reliability is a product feature, not an afterthought
**Source-backed point:** SRE practice treats reliability as a measurable contract (SLOs, error budgets, toil reduction). Autonomous systems without an error budget mindset turn into ambient guilt.

**Platform implication:** Track digest-on-time rate, sweep-completion rate, executor success rate, review-packet freshness. When any of these drops, the budget is being spent. Toil reduction is a first-class goal.

### 3. Trust must be earned per domain, not granted globally
**Source-backed point:** OpenAI agent-governance guidance and NIST RMF both stress graduated autonomy: narrow, observable, reversible actions earn the right to broader scope.

**Platform implication:** The policies table in autonomy.db is the contract. Trust-level expansion happens per domain after evidence of reliability, not as a global flag.

### 4. The review surface is the human-AI interface, not a log
**Source-backed point:** XAI (explainable AI) research consistently finds that explanation quality determines trust calibration: too much detail and the human disengages; too little and they over- or under-trust.

**Platform implication:** Digest and review packets must surface decisions and tradeoffs, not raw output. One-line context + recommendation + decision lever beats firehose every time.

### 5. Discovery cadence beats feature volume
**Source-backed point:** Lean / Continuous Discovery / SVPG converge on outcome-driven product loops with explicit hypotheses.

**Platform implication:** Each platform change should be tied to an opportunity-scoring or digest-quality outcome. "We added a sensor" is not a milestone; "filter ratio improved from X to Y after sensor added" is.

---

## Operational subdomains

### 1. Desired-state sweeps and opportunity scoring
What it does: scans goal_matrix_entries, detects drift, generates ranked opportunities.
What to watch:
- Sweep frequency and completion rate
- Opportunities-generated-per-sweep
- Opportunity-to-execution conversion rate
- Score calibration (do high-score opportunities actually pay off?)

### 2. Executor reliability
What it does: runs Codex tasks, Claude tasks, autoworkflow runs, research jobs.
What to watch:
- Success rate per executor type
- Median time-to-complete by task class
- Rate of executions requiring human reviver vs. self-recovering
- Hung-inference incidents (per 2026-04-23 Hermes hung-inference investigation, watchdogs must actually fire)

### 3. Policy enforcement and trust-level evolution
What it does: gates auto-execute vs. queue-for-review per domain.
What to watch:
- Per-domain trust level over time
- Approval-required actions actually requiring approval (no leakage)
- Auto-executed actions causing review-required outcomes (this should trend down)

### 4. Review surfaces (digest, review packets, war room)
What it does: presents work to human in scannable form.
What to watch:
- Forward ratio (Claudia / human filter): target ≤30% reaches Fernando
- Time-from-digest-to-decision
- Decisions reversed on second look (rate)

### 5. Learning engine and feedback loop
What it does: captures outcome data into learnings table for future runs.
What to watch:
- Learnings written per week
- Learnings applied to subsequent decisions
- Concept drift in opportunity scoring

---

## What is still inference, not source fact

- That the current schema (goals, opportunities, executions, learnings, review_packets) is the right factoring long-term — it may need normalization or denormalization based on usage data
- That trust-level-2 with narrow allowed_actions is the right next step from trust-level-1 — could be that we need finer-grained gradations
- That a daily digest at fixed time is the right cadence — threshold-triggered may emerge as better
- That Codex is the right primary executor for code work and Claude for judgment — could shift as model capabilities evolve

---

## Suggested metric stack

### Primary metric
- Useful-work-per-week the human accepts (count of approved review packets translating to real outcomes)

### Input metrics
- Sweep completion rate
- Opportunities-generated-per-sweep
- Executor success rate (per class)
- Forward ratio at Claudia layer (≤30%)
- Forward ratio at Fernando layer (target: most items resolve in one pass)
- Toil hours per week (manual work the human did that should have been automated)

### Reliability metrics
- Hung-inference incidents per week
- Watchdog fire rate vs. expected
- Backup freshness for autonomy.db

---

## Review thresholds, provisional

| Signal | Green | Yellow | Red |
|---|---|---|---|
| Daily digest delivered on time | ≥6 of 7 days | 4–5 of 7 | ≤3 of 7 |
| Forward ratio (Claudia → Fernando) | ≤30% | 30–60% | >60% |
| Executor success rate | >90% | 75–90% | <75% |
| Hung-inference incidents (weekly) | 0 | 1–2 | ≥3 |
| Auto-executed → required-review-after | <5% | 5–15% | >15% |

---

## How Hermes should use this file

When evaluating platform work, ask in order:
1. Does this make the system produce more useful work overnight, surface less noise, or fail less silently?
2. Is this changing a deterministic flow that should stay deterministic, or adding judgment where judgment was missing?
3. Does this earn additional trust per domain, or grant it prematurely?
4. What metric should move if this is worth doing?
5. Will this reduce toil for Fernando, or create new toil disguised as features?

If the answers are fuzzy, the proposed platform work is probably premature.
