---
name: ds_spanish_fluency-context
description: Research-grounded Spanish-learning context built from SLA sources. Load when evaluating study plans, practice ideas, or fluency progress.
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [desired-state, spanish, SLA, fluency, ACTFL, CEFR, vocabulary]
    goal_id: ds_spanish_fluency
    knowledge_file: docs/knowledge/goals/ds_spanish_fluency.md
---

# Spanish Fluency Context — Source-Grounded Lens

## Source spine
- Krashen, https://www.sdkrashen.com/content/books/principles_and_practice.pdf
- Swain input/output, https://journals.sagepub.com/doi/10.1177/026553228500200301
- Swain output hypothesis, https://web.stanford.edu/group/pirelli/cgi-bin/wordpress/wp-content/uploads/2012/05/Swain-2005-The-output-hypothesis-theory-and-research.pdf
- Paul Nation vocabulary, https://www.wgtn.ac.nz/lals/resources/paul-nations-resources/publications/books/vocabulary-related-publications
- Four Strands, https://www.wgtn.ac.nz/lals/resources/paul-nations-resources/publications/books/the-four-strands
- ACTFL, https://www.actfl.org/educator-resources/actfl-proficiency-guidelines/
- CEFR, https://rm.coe.int/common-european-framework-of-reference-for-languages-learning-teaching/16809ea0d4

## What you are steering
Real fluency requires enough understandable input, enough forced output, enough retrieval practice, and enough honest assessment to avoid fooling yourself.

## Default subdomains
1. Input volume
2. Output practice
3. Vocabulary and retrieval
4. Externalized assessment
5. Balanced program design

## Auto-do
- Suggest balanced study moves that hit the current bottleneck
- Flag fake-productivity study patterns
- Translate vague goals into ACTFL / CEFR-aligned can-do checks
- Recommend more input or output depending on the current gap

## Escalate
- Any expensive program purchase
- Formal test registration
- Major curriculum switch when there is not yet evidence the current one failed
