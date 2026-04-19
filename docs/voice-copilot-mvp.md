# Voice Copilot MVP

Accepted product spec for Hermes voice-first development workflow.

## User experience

- Start from an iPhone Shortcut.
- Use iPhone plus any Bluetooth headset for audio I/O.
- One tap starts a continuous conversation.
- Hermes acts like a spoken copilot, not a chatbot.
- Spoken replies should be concise but not clipped.
- Reliability matters more than raw latency.

## Priority jobs

1. Brainstorm ideas
2. Review code changes
3. Hear PR summaries
4. Approve actions by voice
5. Merge PRs
6. Create issues/tasks

## Default approvals

Pre-approved in the voice workflow:

- Read repo state
- Create design docs
- Email Fernando
- Draft PRs
- Open issues in Fernando-owned repos

Explicit spoken approval still required:

- Merge PRs
- Other risky or destructive actions

Approval phrase for v1: `approve and merge`

When the user says to merge a PR, Hermes should interpret that as merge after CI passes.

## Delivery behavior

- Final receipts land in Telegram with links.
- Intermediate noise should stay low.
- Failures get a brief summary and an automatic safe retry when possible.

## Session defaults

- No wake word in v1.
- Session context should persist naturally inside the chat.
- Interrupt speech immediately when the user starts talking.
- Email only goes to Fernando in v1.

## Server-side implementation for v1

The server-side entrypoint is `/copilot` in the Telegram chat.

- `/copilot on` enables the voice-first copilot session and turns on voice replies for voice messages.
- `/copilot off` stops the session and returns the chat to text-only replies.
- `/copilot status` shows whether the session is active.

Recommended iPhone Shortcut behavior:

1. Open the Hermes Telegram chat.
2. Send `/copilot on`.
3. Hand off audio to the Bluetooth headset.

This keeps the transport simple for v1 while using Hermes's existing Telegram voice note, STT, TTS, and repo automation paths.

## Acceptance test

Fernando can trigger Hermes from an iPhone Shortcut, talk through a Bluetooth headset, brainstorm ideas, have Hermes submit a PR and summarize it, then explicitly approve and have Hermes merge it after CI passes.