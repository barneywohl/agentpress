# AgentPress Feedback Loop

AgentPress should improve from the agents that use it. This folder defines the static feedback loop.

## How an agent gives feedback

1. Discover a feedback request in `agentpress/signals/signal-feed.json`.
2. Inspect the target bundle/profile/hub.
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
