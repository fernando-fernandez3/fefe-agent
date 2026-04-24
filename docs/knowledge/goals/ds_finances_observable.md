# Knowledge: ds_finances_observable — Finances Become Cleaner and More Observable

> Research-backed decomposition for making household finances visible, reviewable, and less guess-driven.
> Last updated: 2026-04-22

---

## Goal Definition

Financial observability means Fernando can answer, quickly and reliably:
- where the money is
- where it went
- what is about to happen
- whether the trend is healthy

This file favors authoritative public institutions over vendor blogs.

---

## Authoritative source spine

### Budgeting and cash-flow visibility
- CFPB budgeting hub
  - https://www.consumerfinance.gov/consumer-tools/budgeting/
- Consumer.gov, making a budget
  - https://consumer.gov/managing-your-money/making-budget
- Consumer.gov, tracking your spending
  - https://consumer.gov/managing-your-money/tracking-your-spending
- CFPB, Your Money, Your Goals toolkit
  - https://www.consumerfinance.gov/consumer-tools/educator-tools/your-money-your-goals/
- FDIC Money Smart
  - https://www.fdic.gov/resources/consumers/money-smart/index.html

### Savings, liquidity, resilience
- CFPB, set savings goals
  - https://www.consumerfinance.gov/consumer-tools/budgeting/set-savings-goals/
- Federal Reserve SHED
  - https://www.federalreserve.gov/consumerscommunities/shed.htm

### Household dashboard and ratios
- CFPB financial well-being scale
  - https://www.consumerfinance.gov/data-research/research-reports/financial-well-being-scale/
- CFPB debt-to-income ratio explainer
  - https://www.consumerfinance.gov/ask-cfpb/what-is-a-debt-to-income-ratio-en-1791/
- AnnualCreditReport official portal
  - https://www.annualcreditreport.com/index.action
- IRS tax withholding estimator
  - https://www.irs.gov/individuals/tax-withholding-estimator

---

## What the sources directly support

### 1. Visibility starts with a complete money map
Government budgeting guidance consistently starts with listing all income, expenses, accounts, bills, and obligations.

**Implication:** Account inventory and transaction coverage are not optional. If there are uncategorized or hidden pockets, the system is not observable.

### 2. Budgeting is a forward-looking control loop
Budgeting is not just historical categorization. It is a plan, then a compare-to-actual review.

**Implication:** Observability must include both past spending and near-future expected inflows/outflows.

### 3. Liquidity and resilience deserve their own lane
Savings-goal and SHED-style resilience guidance show that “can we absorb an unexpected hit?” is distinct from generic net worth.

**Implication:** Emergency reserves should be measured separately from long-term assets.

### 4. Financial health needs both hard numbers and confidence / control
CFPB’s financial well-being work makes clear that money health is not just arithmetic, it is also predictability and control.

**Implication:** A household dashboard should include resilience and strain indicators, not just balances.

### 5. Review cadence matters
The institutional sources imply recurring review, not one-time setup.

**Implication:** The system needs weekly, monthly, quarterly, and annual checkpoints.

---

## Operational subdomains

### 1. Account and transaction visibility
What to track:
- all active accounts
- all recurring bills
- transaction coverage
- uncategorized spending rate

### 2. Budget and forecast
What to track:
- monthly plan
- actual vs. plan variance
- next 4-week cash outlook
- irregular/annual expense preparation

### 3. Emergency liquidity
What to track:
- emergency fund balance
- months of essential expenses covered
- refill plan after drawdown

### 4. Household dashboard
What to track:
- net cash flow
- debt-to-income ratio if relevant
- savings rate
- credit hygiene / report review
- tax withholding sanity

### 5. Review cadence
What to track:
- weekly transaction and bill review
- monthly close and variance review
- quarterly subscription / insurance / sinking-fund review
- annual tax / benefits / long-term goal review

---

## Inference layer, explicit

These are strong operating choices, but they are still choices:
- using “4-week forecast” as the default short horizon
- using net worth trend as a top-level household metric
- including ranch savings as a named household goal bucket
- using zero uncategorized spending as the definition of full observability

Those are sensible, but they are not mandated by one canonical framework.

---

## Suggested thresholds, provisional

| Signal | Green | Yellow | Red |
|---|---|---|---|
| Uncategorized spending | 0% | 1 to 5% | > 5% |
| Forecast visibility | 4+ weeks | current month only | reactive / unknown |
| Emergency reserve | 6+ months essential spend | 3 to 5 months | < 3 months |
| Budget variance | < 5% | 5 to 15% | > 15% |
| Review cadence | weekly + monthly maintained | inconsistent | mostly absent |

---

## How Hermes should use this file

When evaluating finance-related opportunities:
1. Which observability question is currently unanswered?
2. Is the fix about missing data, missing categorization, missing forecast, or missing review cadence?
3. What decision becomes easier once this is visible?
4. Is this a low-risk analysis task or a money-moving action that must stay human-gated?

The point is clarity. If a proposal does not improve clarity or control, it probably does not belong under this goal.
