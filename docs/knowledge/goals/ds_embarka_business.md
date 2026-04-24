# Knowledge: ds_embarka_business — Embarka Becomes a Real Business

> Research-backed decomposition for Embarka as a family-focused AI travel product.
> Standard: authoritative frameworks first, Embarka-specific implications second, explicit inference labels always.
> Last updated: 2026-04-22

---

## Goal Definition

Embarka should become a durable business by helping families complete trustworthy trip plans faster and with less cognitive load than generic travel tools.

This file is deliberately split into:
- **Source-backed framework**
- **Embarka implication**
- **Inference / local assumption**

That keeps the reasoning auditable instead of letting everything blur into model guesswork.

---

## Authoritative source spine

### North Star metric and product measurement
- John Cutler, Amplitude, North Star Metric framework
  - https://amplitude.com/blog/north-star-metric
- Google HEART framework for UX measurement
  - https://research.google/pubs/the-heart-framework-for-measuring-ux/

### Growth and funnel decomposition
- Dave McClure, AARRR
  - https://500hats.typepad.com/500blogs/2007/09/startup-metrics.html
- Brian Balfour, retention as the prerequisite for scalable growth
  - https://www.reforge.com/blog/retention-series-introduction
- Andrew Chen, retention as the strongest PMF signal
  - https://andrewchen.com/retention-is-king/

### Customer-value framing
- Clayton Christensen et al., Jobs to Be Done, Harvard Business Review
  - https://hbr.org/2016/09/know-your-customers-jobs-to-be-done
- Strategyn, Outcome-Driven Innovation / JTBD framing
  - https://strategyn.com/jobs-to-be-done/

### Onboarding and activation design
- Nielsen Norman Group, onboarding guidance
  - https://www.nngroup.com/articles/onboarding/
- Wes Bush, activation framing
  - https://productled.com/blog/activation/

### Product operating cadence
- Eric Ries, Lean Startup principles
  - https://theleanstartup.com/principles
- Teresa Torres, continuous discovery habits
  - https://www.producttalk.org/2021/08/continuous-discovery-habits/
- Marty Cagan / SVPG, product operating model
  - https://www.svpg.com/product-operating-model/

---

## Decomposition that is directly supported by the sources

### 1. Customer job clarity
**Source-backed point:** JTBD says the product should be organized around the progress a user is trying to make, not just demographics.

**Embarka implication:** The top-level product question is not “how do we build an AI travel app?” It is “what progress is a family trying to make when travel planning feels overwhelming?”

**Working job statement, inference:**
“When I am planning a trip with kids, I want a plan that already accounts for family constraints, pacing, and logistics, so I can stop piecing everything together manually and feel confident booking.”

### 2. One value metric, not a vanity dashboard
**Source-backed point:** A North Star metric should represent delivered customer value and connect to long-term business outcomes.

**Embarka implication:** The primary metric must be about successful planning, not pageviews or chat turns.

**Recommended NSM, inference:**
**Monthly families who complete a high-intent trip plan**

A “high-intent trip plan” should eventually be operationalized as something like saved, shared, exported, or moved toward booking.

### 3. Activation has to equal real value, fast
**Source-backed point:** Onboarding and activation should move users to value quickly, with only the minimum necessary friction.

**Embarka implication:** Activation is not “finished signup.” It is the first trustworthy family-relevant plan.

**Recommended activation event, inference:**
User provides family/trip context and receives a plan they are willing to save, share, or act on.

### 4. Retention matters more than top-of-funnel bragging
**Source-backed point:** Retention is the real proof of product value. Acquisition without retention is a leak.

**Embarka implication:** Do not overweight launch noise, SEO, or signups if families do not return for future planning or continue within the same planning episode.

### 5. Product should run as a discovery system, not a feature factory
**Source-backed point:** Lean Startup, Continuous Discovery, and SVPG all converge on the same thing: run explicit hypotheses, test them quickly, and organize around outcomes.

**Embarka implication:** Embarka should be managed as a loop:
- identify the family planning bottleneck
- test a solution in small scope
- measure activation / retention movement
- keep only what actually improves the planning experience

---

## Operational subdomains for Embarka

These are the right subdomains because they map cleanly to the source spine above.

### 1. Trip creation UX
Why it exists:
- supported by HEART, NN/g onboarding, and activation framing
- if users cannot get to value quickly, nothing else matters

What to watch:
- time to first useful plan
- drop-off by intake step
- rate of completed first plans
- trust signal after first output

### 2. Family-specific differentiation
Why it exists:
- supported by JTBD / ODI thinking
- the product needs a clear “why this instead of generic AI” answer

What to watch:
- use of family-specific inputs and constraints
- adoption of family-only planning features
- evidence that users perceive Embarka as “built for families” rather than “generic planner with a thin skin”

### 3. Retention and repeat planning
Why it exists:
- supported by Balfour and Chen
- real business value requires repeat use or continued movement through the trip lifecycle

What to watch:
- return rate within the same trip-planning episode
- repeat planning across future trips
- saved/shared/reopened plans

### 4. Revenue and monetization readiness
Why it exists:
- a real business has to capture value, not just create interest

What to watch:
- premium conversion
- booking-assist clickthrough if applicable
- willingness to pay for lower-stress family planning

### 5. Discovery and learning cadence
Why it exists:
- supported by Lean Startup, Torres, and SVPG
- if you stop learning from families, the moat dies

What to watch:
- weekly customer signal intake
- hypothesis backlog
- time from insight to tested change

---

## What is still inference, not source fact

These may be good bets, but they are still bets:
- that “families with kids” is the best initial segment
- that collaborative family planning should be a wedge feature
- that saved/shared/exported plans are the right definition of “high intent”
- that the best moat is family logistics rather than price, booking, or inspiration

Those need validation with actual Embarka usage, interviews, and production behavior.

---

## Suggested metric stack

### Primary metric
- Monthly families who complete a high-intent trip plan

### Input metrics
- family signups
- activation rate to first useful plan
- time to first useful plan
- return within planning episode
- plan save/share/export rate
- repeat planning rate
- paid conversion or monetization proxy

### UX checks via HEART
- Happiness: user trust / usefulness rating
- Engagement: plan revisits, edits, shares
- Adoption: family-profile completion, feature adoption
- Retention: repeat planning / revisit
- Task Success: plan completion and booking readiness

---

## Review thresholds, provisional

These are operating thresholds, not claims from the literature.

| Signal | Green | Yellow | Red |
|---|---|---|---|
| Time to first useful plan | <= 5 min | 5 to 10 min | > 10 min |
| Activation to first useful plan | > 50% | 25 to 50% | < 25% |
| Saved/shared/exported plan rate | > 30% | 10 to 30% | < 10% |
| Repeat planning / revisit | rising | flat | falling |
| Discovery cadence | weekly customer signal review | irregular | mostly absent |

---

## How Hermes should use this file

When evaluating Embarka work, ask in order:
1. Which family-planning job does this help?
2. Does it improve activation, retention, or monetization readiness?
3. Is it improving the family-specific moat, or is it generic product churn?
4. What metric should move if this is worth doing?
5. What evidence would prove the move worked?

If those answers are fuzzy, the proposed work is probably premature.
