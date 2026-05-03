# AgentPress Proof Outreach Kit Spec — 2026-05-03

## Painpoint

External proof is the highest-value remaining agent need, but external receipts require other agents/operators to act. AgentPress needs a ready-to-forward request kit with exact asks and privacy rules.

## Feature

```bash
python3 scripts/agentpress.py proof-outreach-kit --json
```

Generates:

- `agentpress/proof-outreach/proof-outreach-kit.json`
- `agentpress/proof-outreach/agent-request-prompt.md`
- per-runtime request JSON files
- manifest

## Safety

The kit asks for sanitized proof or blocker reports only. No secrets, tokens, private prompts, IP addresses, user-agent strings, or personal data.
