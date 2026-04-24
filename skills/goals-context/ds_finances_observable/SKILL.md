---
name: ds_finances_observable-context
description: Research-grounded household finance observability context. Load when reviewing cash flow, budgeting, savings visibility, or finance dashboards.
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [desired-state, finances, budget, cash-flow, observability, household-finance]
    goal_id: ds_finances_observable
    knowledge_file: docs/knowledge/goals/ds_finances_observable.md
---

# Finance Observability Context — Source-Grounded Lens

## Source spine
- CFPB budgeting, https://www.consumerfinance.gov/consumer-tools/budgeting/
- Consumer.gov budget, https://consumer.gov/managing-your-money/making-budget
- Consumer.gov spending tracking, https://consumer.gov/managing-your-money/tracking-your-spending
- CFPB Your Money Your Goals, https://www.consumerfinance.gov/consumer-tools/educator-tools/your-money-your-goals/
- FDIC Money Smart, https://www.fdic.gov/resources/consumers/money-smart/index.html
- Federal Reserve SHED, https://www.federalreserve.gov/consumerscommunities/shed.htm
- CFPB financial well-being, https://www.consumerfinance.gov/data-research/research-reports/financial-well-being-scale/
- CFPB DTI, https://www.consumerfinance.gov/ask-cfpb/what-is-a-debt-to-income-ratio-en-1791/

## What you are steering
Finances are observable when Fernando can quickly see current state, near-term cash flow, resilience, and trend without guessing.

## Default subdomains
1. Account and transaction visibility
2. Budget and forecast
3. Emergency liquidity
4. Dashboard metrics
5. Review cadence

## Auto-do
- Summarize known state from connected data sources
- Flag uncategorized spending or missing categories
- Surface upcoming bills or cash-flow pinch points
- Suggest dashboard gaps or review-cadence gaps
- Prepare finance summaries that improve clarity without moving money

## Escalate
- Any transfer, trade, payment, or purchase decision
- Investment allocation changes
- Insurance changes
- Tax filing decisions
- Any action that changes financial state rather than just explaining it
