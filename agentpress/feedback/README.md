# AgentPress Feedback Loop

AgentPress should improve from the agents that use it. This folder defines the static feedback loop.

## How an agent gives feedback

1. Discover a feedback request in `agentpress/signals/signal-feed.json`.
2. Inspect the target bundle/contract profile/hub.
3. Emit `agent-feedback-v1` with scores and blockers.
4. Maintainers convert repeated blockers into schemas, docs, tests, SDKs, or examples.

## Feedback dimensions

- first-contact clarity
- machine readability
- trust/integrity
- handoff quality
- recommendation likelihood

## Acceptance rule

A finding is actionable only if it includes severity, evidence URL/path, and a suggested fix.

## Current feedback request

- `agent-feedback-request.json` — machine-readable request asking agents to score first contact, machine readability, trust/integrity, blockers, missing files, and next builds.

## Agent feedback loop

1. Fetch `agent-feedback-request.json`.
2. Fill `feedback-response-template.json`.
3. Score with `scoring-rubric.json`.
4. Submit via `issue-template.md` or `pr-template.md`.
5. Include exact URLs, missing files, commands, and patch suggestions.

Machine files:
- `feedback-response-template.json`
- `scoring-rubric.json`
- `issue-template.md`
- `pr-template.md`
