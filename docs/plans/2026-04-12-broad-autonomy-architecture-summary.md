# Broad Autonomy Architecture Summary

## Goal
Turn high-level goals into continuous autonomous repo-focused work inside Hermes, with durable policies, explicit reviews, verification, and learnings.

## MVP shape
- One live domain: code projects
- One review channel: Telegram
- One primary executor: direct safe repo work inside Hermes
- No autonomous trust promotion
- No merges, deploys, or external messaging without review

## Core loop
1. Load active goals and policies
2. Run repo sensors
3. Append immutable signals
4. Project current world state
5. Generate and rank opportunities
6. Apply policy gate
7. Execute safe work or create review
8. Verify outcome
9. Persist execution record
10. Extract learning

## Core storage objects
- goals
- policies
- signals
- world_state
- opportunities
- executions
- reviews
- learnings

## Council amendments
- Repo autonomy only for first live slice
- Add append-only signal layer from day one
- Human-gate all trust promotion
- Add circuit breakers and unattended runtime ceilings
- Start with one executor path only

## Success metrics
- Goals and policies persist durably
- Repo signals are captured and queryable
- A ranked opportunity queue exists
- Unsafe work becomes a persisted review instead of running
- One safe repo task executes end-to-end with verification evidence
- One learning record is written from a real execution
