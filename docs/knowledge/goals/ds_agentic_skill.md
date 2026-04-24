# Knowledge: ds_agentic_skill — Agentic Workflow Skill Compounds Weekly

> Research-backed decomposition for compounding Fernando's ability to build, evaluate, and improve agentic workflows.
> Last updated: 2026-04-22

---

## Goal Definition

Agentic skill compounds when each workflow run leaves behind better patterns, better evaluations, better tool contracts, and better operational judgment for the next run.

This file intentionally separates:
- canonical learning science
- primary AI agent sources
- operational inference for Hermes

---

## Authoritative source spine

### Deliberate practice and feedback
- Ericsson et al., deliberate practice
  - https://doi.org/10.1037/0033-295X.100.3.363
- Hattie and Timperley, power of feedback
  - https://doi.org/10.3102/003465430298487

### Agent design patterns
- Anthropic, building effective agents
  - https://www.anthropic.com/engineering/building-effective-agents
- ReAct paper
  - https://arxiv.org/abs/2210.03629
- AutoGen paper
  - https://arxiv.org/abs/2308.08155
- Anthropic, think tool
  - https://www.anthropic.com/engineering/claude-think-tool

### Evals and measurement
- OpenAI evals getting started
  - https://cookbook.openai.com/examples/evaluation/getting_started_with_openai_evals
- Anthropic TAU-bench
  - https://www.anthropic.com/engineering/developing-and-improving-ai-agents-with-tau-bench
- SWE-bench
  - https://www.swebench.com/
  - https://arxiv.org/abs/2312.06674
- NIST AI RMF
  - https://www.nist.gov/itl/ai-risk-management-framework

### Tool and interface design
- OpenAI function calling
  - https://platform.openai.com/docs/guides/function-calling
- OpenAI structured outputs
  - https://platform.openai.com/docs/guides/structured-outputs
- Model Context Protocol spec
  - https://modelcontextprotocol.io/specification/2025-03-26

### Operational learning loops
- Google SRE workbook, postmortem culture
  - https://sre.google/workbook/postmortem-culture/
- Reflexion
  - https://arxiv.org/abs/2303.11366

---

## What the sources directly support

### 1. Skill improves through deliberate reps plus feedback
Deliberate-practice literature says improvement requires repeated attempts on comparable tasks with meaningful feedback and correction.

**Implication:** Agentic skill cannot compound if every workflow is a totally new snowflake with no review loop.

### 2. Agent systems need explicit patterns
Primary AI-agent sources now converge on repeatable patterns like routing, tool use, orchestrator-worker, critique loops, and reasoning-plus-action.

**Implication:** A reusable pattern library is a first-class asset.

### 3. Evals are part of the product, not decoration
Provider and benchmark sources all say the same thing in different language: if you do not measure agent performance, regressions will hide in vibes.

**Implication:** Each serious workflow needs pass/fail checks, comparison cases, or benchmark-like examples.

### 4. Tool contracts determine reliability
Function calling, structured outputs, and MCP all reinforce the same point: brittle tool interfaces produce brittle agents.

**Implication:** Tool fluency means schema fluency, failure-mode fluency, and interoperability.

### 5. Operational learning has to survive the single run
Postmortem culture and Reflexion-style work both point at the same need: capture lessons and feed them back into the next attempt.

**Implication:** If a workflow solved something non-obvious and nothing durable was extracted, skill did not really compound.

---

## Operational subdomains

### 1. Deliberate practice cadence
What to track:
- repeated runs on comparable task classes
- speed / quality trend
- explicit review after execution

### 2. Workflow pattern library
What to track:
- routing patterns
- orchestrator-worker patterns
- evaluator-optimizer patterns
- reflection / retry patterns

### 3. Evaluation discipline
What to track:
- regression sets
- benchmark-like tasks
- failure taxonomies
- outcome metrics, not just model confidence

### 4. Tool and interface fluency
What to track:
- tool schema quality
- structured outputs
- resumability / checkpointing
- MCP or equivalent interoperability

### 5. Operational learning loop
What to track:
- postmortems
- extracted skills
- memory updates
- whether the next run got measurably easier

---

## Inference layer, explicit

These are operating choices built on the source spine:
- measuring compounding weekly
- using “new skill extracted” as one of the top health indicators
- treating Hermes skill files as the main persistence layer for procedural learning
- preferring tool-first workflows over prompt-only flows in most real work

Those are strong choices, but they are still choices.

---

## Suggested thresholds, provisional

| Signal | Green | Yellow | Red |
|---|---|---|---|
| New reusable pattern extracted | >= 1 / week | 1 every 2 weeks | none in 2+ weeks |
| Useful autonomous outputs | several / week | occasional | mostly noise |
| Eval discipline | regression checks common | ad hoc | almost absent |
| Tool contract quality | structured and reliable | mixed | brittle / implicit |
| Postmortem / learning capture | routine | occasional | mostly lost |

---

## How Hermes should use this file

When evaluating agentic-workflow work:
1. What repeatable pattern is being exercised?
2. How will we tell if this run is better than the last one?
3. Which part failed, planning, tool contract, eval, or operational loop?
4. What durable artifact should exist after success, skill, memory, benchmark, or tool improvement?

If the answer is “none,” the workflow is likely just burning tokens.
