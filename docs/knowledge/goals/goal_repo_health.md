# Knowledge: goal_repo_health — Code Quality and Architecture Health Across Primary Repos

> Research-backed decomposition for maintaining code quality and architectural health across the three primary repos: Embarka, autoworkflow, and fefe-agent (Hermes).
> Standard: authoritative engineering sources first, repo-specific implications second, explicit inference labels always.
> Last updated: 2026-04-25

---

## Goal Definition

Repo health means: code is understandable, changes are safe, dependencies are current, tests are honest, architecture supports the next change instead of fighting it. Decay in any of the three primary repos directly increases human review burden and slows every other goal that depends on them.

The three repos tracked under this goal:
- `/home/fefernandez/embarka` — Embarka product
- `/home/fefernandez/autoworkflow` — autoworkflow platform
- `/home/fefernandez/.hermes/hermes-agent` — fefe-agent (Hermes) fork

Each is tracked via `goal_matrix_entries` with weight 1.0; a single rolled-up health score covers all three.

---

## Authoritative source spine

### Refactoring and code design
- Martin Fowler, Refactoring catalog
  - https://refactoring.com/catalog/
- Martin Fowler, Refactoring (book) reference
  - https://martinfowler.com/books/refactoring.html
- Michael Feathers, Working Effectively with Legacy Code (book)
  - https://www.oreilly.com/library/view/working-effectively-with/0131177052/

### Code health and architecture
- Adam Tornhill, Software Design X-Rays / CodeScene foundations
  - https://codescene.com/blog/
- Google Engineering Practices (code review, small CLs)
  - https://google.github.io/eng-practices/

### Testing
- Google Testing Blog (test sizes, hermetic tests)
  - https://testing.googleblog.com/
- Kent Beck, Test-Driven Development perspective
  - https://www.kentbeck.com/

### Dependency health and security
- OWASP Top Ten
  - https://owasp.org/www-project-top-ten/
- GitHub Dependabot documentation
  - https://docs.github.com/en/code-security/dependabot
- CISA Secure by Design
  - https://www.cisa.gov/securebydesign

### Documentation
- Daniele Procida, Diátaxis framework (tutorial / how-to / reference / explanation)
  - https://diataxis.fr/

---

## What the sources directly support

### 1. Health is observable, not aspirational
**Source-backed point:** Software design analysis (Tornhill et al.) treats code as a measurable system: hotspots, change-coupling, complexity drift can all be tracked.

**Repo implication:** Each of the three repos should produce repeatable health signals: file hotspots, complexity trend, dependency staleness, test coverage trend, recent-change risk score.

### 2. Small, frequent changes beat big-bang rewrites
**Source-backed point:** Google's CL guidance and Fowler's refactoring discipline both center on small, reviewable changes that preserve behavior.

**Repo implication:** Refactoring opportunities should be sized to fit one PR. Big rewrites should require explicit goal-level decisions, not be smuggled in.

### 3. Tests are honest only when they fail when behavior breaks
**Source-backed point:** Test-size guidance (Google) and TDD literature emphasize tests at the right level: small, fast, deterministic, with integration coverage where contracts matter.

**Repo implication:** Don't optimize for coverage percentage. Optimize for tests that actually catch regressions during a real change. A 60% suite that catches the bug beats a 90% suite that doesn't.

### 4. Dependencies decay silently
**Source-backed point:** OWASP and CISA repeatedly find outdated/transitive dependencies as a top vulnerability vector. Dependabot/Snyk-style automation closes this loop.

**Repo implication:** Each repo needs an automated dependency-update cadence with the human reviewing only the changes that matter (security, breaking).

### 5. Documentation rot is a code-health signal
**Source-backed point:** Diátaxis splits docs by purpose; misaligned or outdated docs in any quadrant signal that the system has drifted from its description.

**Repo implication:** Drift between README/CLAUDE.md and actual behavior is a health signal. Treat doc drift the same as test drift — a real bug.

---

## Operational subdomains

### 1. Code structure and architecture
What to watch:
- Hotspot files (high churn + high complexity)
- Layer violations (e.g., adapter calling agent internals)
- Circular dependencies
- Module size growth

### 2. Test reliability
What to watch:
- Test pass rate on main
- Flaky test count
- Test runtime (wall clock for full suite)
- Coverage for changed lines (not absolute coverage)

### 3. Dependency posture
What to watch:
- Direct dependencies behind by N major versions
- Known CVEs in transitive deps
- License surprises
- Lockfile drift between repos

### 4. Documentation alignment
What to watch:
- README freshness (last updated vs. last meaningful code change)
- Code-doc drift in CLAUDE.md / AGENTS.md
- Missing docs for primary entry points

### 5. CI and pre-commit hygiene
What to watch:
- CI pass rate on main
- Time from push to green
- Pre-commit hook coverage and skip rate

---

## What is still inference, not source fact

- That a single rolled-up health score across three repos is the right abstraction (it might mask repo-specific decay)
- That weight=1.0 across the three repos is appropriate (Embarka has business pressure, autoworkflow is the platform, Hermes is the agent core — they may not deserve equal weight)
- That refactoring opportunities should be sized to one PR each (some architectural changes legitimately need bigger CLs with deliberate review)

---

## Suggested metric stack

### Primary metric
- Rolled-up health score across the three repos (weighted average of subdomain signals)

### Input metrics
- Hotspot file count per repo
- Test pass rate on main per repo
- Direct dependencies behind by major version (count)
- Open CVEs (count, severity-weighted)
- README/CLAUDE.md drift signal (last meaningful code change vs. last doc update)
- CI pass rate on main per repo

---

## Review thresholds, provisional

| Signal | Green | Yellow | Red |
|---|---|---|---|
| Test pass rate on main | >98% | 90–98% | <90% |
| CI pass rate (last 7 days) | >95% | 80–95% | <80% |
| Direct deps behind major version | 0–2 | 3–5 | >5 |
| Open high/critical CVEs | 0 | 1–2 | ≥3 |
| Hotspot files (high churn × high complexity) | 0–2 per repo | 3–5 | >5 |
| Doc-code drift (days since doc update on changed module) | <30 | 30–90 | >90 |

---

## How Hermes should use this file

When evaluating repo-health work, ask in order:
1. Which of the three repos does this affect, and why this one first?
2. Is this a small reversible change or a structural one that needs a goal-level decision?
3. Will this improve a measurable signal in the metric stack, or is it cosmetic?
4. Are tests and docs moving in lockstep with code, or drifting?
5. Could this be a recurring auto-fix (dependency bump, lint fix) instead of a one-off PR?

If the answers are fuzzy, the proposed work is probably aesthetic rather than load-bearing.
