# Knowledge: ds_pool_automation — Pool/Spa Automation Home Assistant Guide and Product

> Research-backed decomposition for documenting Fernando's lived HA + ESPHome pool/spa setup (in-ground pool with integrated spillover spa, dedicated heater, San Antonio hard-water context), then packaging as a paid configuration bundle. Target $29–49 price.
> Standard: authoritative home-automation / pool-equipment / info-product sources first, Fernando-specific implications second, explicit inference labels always.
> Last updated: 2026-04-25

---

## Goal Definition

A paid configuration bundle (and optional companion guide) that lets a Home Assistant user with a Pentair / Jandy / Hayward pool reliably automate equipment, lighting, heating, and the spillover-spa flow. Anchored on Fernando's actual installation: in-ground pool, integrated spillover spa, dedicated spa heater, string lights, hard San Antonio water.

Two-stage product:
- Stage 1: Document own setup (free knowledge, builds audience, validates demand)
- Stage 2: Package as paid bundle (configs, blueprints, install guide, troubleshooting, hard-water notes)

The market gap is real: Pentair / Jandy / Hayward HA integrations are inconsistent, community-maintained, and lack a polished paid resource. Pool owners are high-disposable-income and overlap heavily with the HA enthusiast segment.

---

## Authoritative source spine

### Home Assistant and ESPHome
- Home Assistant official documentation
  - https://www.home-assistant.io/docs/
- Home Assistant Community Forum
  - https://community.home-assistant.io/
- ESPHome documentation
  - https://esphome.io/
- Home Assistant blueprints and packages
  - https://www.home-assistant.io/docs/automation/using_blueprints/

### Pool equipment authority
- Pentair pool product documentation
  - https://www.pentair.com/en-us/products/residential/pool-spa.html
- Jandy / Zodiac product documentation
  - https://www.jandy.com/
- Hayward pool product documentation
  - https://www.hayward-pool.com/shop/en/pools/c-1
- CDC, Healthy Swimming pool chemistry guidance
  - https://www.cdc.gov/healthywater/swimming/

### Water quality and treatment
- EPA, drinking water hardness and treatment overview (hardness logic transfers)
  - https://www.epa.gov/sdwa
- WQA (Water Quality Association) hardness reference
  - https://www.wqa.org/learn-about-water/perceptible-issues/scale-deposits

### Info-product strategy (shared with ds_bbq_booklet)
- Amy Hoy and Alex Hillman, Stacking the Bricks
  - https://stackingthebricks.com/
- Indie Hackers community case studies
  - https://www.indiehackers.com/
- Nathan Barry, Authority playbook
  - https://nathanbarry.com/

---

## What the sources directly support

### 1. The HA ecosystem is the right home for this product
**Source-backed point:** Home Assistant's documentation, community forum, and blueprints show a mature, large, technically sophisticated user base actively integrating diverse hardware.

**Goal implication:** The product format should feel native to HA users: YAML packages, blueprints, ESPHome configs, repeatable install steps. Not a generic "smart home" PDF.

### 2. Pool equipment integrations are first-party but inconsistent
**Source-backed point:** Pentair / Jandy / Hayward each have proprietary protocols and varying official integration support. Community integrations often fill the gap with varying reliability.

**Goal implication:** The bundle must be brand-honest about which equipment is supported, what each integration's failure modes are, and where an ESPHome bridge is the better path. Vague "works with most pools" is the failure mode to avoid.

### 3. Spillover spa adds a control-flow problem worth solving
**Source-backed point:** Pool-equipment documentation distinguishes pool-only, dedicated-spa, and spillover-spa configurations. The spillover variant has shared water, distinct heater control, and valve actuation that varies by manufacturer.

**Goal implication:** The integrated-spillover-spa flow is the differentiator. Most generic pool-automation guides skip this. Fernando's installation makes him a credible primary source.

### 4. Hard water creates real-world failure modes the product should address
**Source-backed point:** WQA and EPA references confirm hardness causes scale, equipment wear, and chemistry instability. San Antonio is in a known hard-water region.

**Goal implication:** Hardness-aware automation rules (e.g., chemistry monitoring cadence, pump/heater protective shutoffs, salt-cell maintenance schedules) are content the rest of the market underweights. Lean into this.

### 5. Audience-led product validation works the same here as for the booklet
**Source-backed point:** Hoy/Hillman, Indie Hackers, and Nathan Barry all argue that audience builds before product, and free knowledge funnels paid product.

**Goal implication:** Stage-1 free documentation should live publicly (HA forum, GitHub, blog, Reddit) and build the audience. Stage-2 bundle then converts a known audience instead of cold-launching.

---

## Operational subdomains

### 1. Lived setup documentation
What to watch:
- Equipment inventory and brand list
- HA / ESPHome configs in version control
- Automation list (lights, heating, spillover, pump schedule, chemistry alerts)
- Diagrams (electrical, plumbing, network)

### 2. Audience build
What to watch:
- HA forum posts and engagement
- r/homeassistant and r/poolspa presence
- GitHub repo with public configs
- Email list / interest list growth

### 3. Product packaging
What to watch:
- Bundle scope (which equipment, which automations)
- Install guide format (PDF + YAML files? Video? Both?)
- Pricing decision ($29, $39, $49)
- Refund / support posture

### 4. Distribution and launch
What to watch:
- Landing page live and converting
- HA forum / community placement
- GitHub-based discovery (SEO via repo README)
- Social proof from real installs

### 5. Recurring updates and support
What to watch:
- HA / ESPHome version compatibility cadence
- Customer questions creating product update backlog
- Time invested per support request
- Recurring revenue path (annual config refresh?) vs. one-time

---

## What is still inference, not source fact

- That $29–49 is the right price (HA users may pay more for genuine time-savings; pool-equipment-aware buyers may anchor higher)
- That Pentair-first is the right starting brand (Hayward and Jandy are also large; could split bundles by brand)
- That GitHub + HA forum is the right primary distribution (could be Patreon, Gumroad, Substack)
- That the spillover-spa angle is a strong enough wedge (could need to expand to general pool/spa automation with spillover as a featured chapter)
- That recurring updates are necessary (could ship a frozen bundle with a v2 release model)

---

## Suggested metric stack

### Primary metric
- Bundle shipped and revenue earned (real $, not promises)

### Input metrics
- Public configs / blueprints published
- HA forum engagement (posts, replies, helpful votes)
- GitHub stars / forks on the public configs
- Email / interest list signups

### Post-launch metrics
- Units sold (week 1, month 1, month 3)
- Refund rate
- Support questions per buyer
- Compatibility issues per HA / ESPHome release

---

## Review thresholds, provisional

| Signal | Green | Yellow | Red |
|---|---|---|---|
| Public configs in version control | comprehensive | partial | none |
| HA forum / community engagement | active and helpful | sporadic | none |
| Email / interest list at launch | ≥150 | 50–150 | <50 |
| Conversion rate on landing page | ≥3% | 1–3% | <1% |
| Refund rate (post-launch) | <5% | 5–15% | >15% |
| Compatibility issues per HA release | 0–1 | 2–4 | ≥5 |

---

## How Hermes should use this file

When evaluating pool-automation work, ask in order:
1. Is this advancing lived setup documentation, audience build, packaging, distribution, or recurring support? If none, deprioritize.
2. Is this generalizing to "all pool automation" or staying anchored on the lived (spillover spa, hard water, San Antonio) setup? Default to anchored.
3. Will this build audience first, then convert? Or build product first and hope?
4. Does this respect equipment-brand realities (specific models, specific protocols, specific failure modes)?
5. Is this a one-time setup or a perpetual support burden disguised as a product? Flag clearly.

If the answer is "generalizing too early" or "perpetual support burden," the proposed work is probably the wrong shape.
