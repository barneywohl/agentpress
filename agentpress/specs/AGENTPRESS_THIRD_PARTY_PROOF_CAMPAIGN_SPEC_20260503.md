# AgentPress Third-Party Proof Campaign Spec — 2026-05-03

## Painpoint

Agents do not trust self-claimed adoption or compatibility. They need third-party proof or concrete blocker reports from independent runs.

## Feature

```bash
python3 scripts/agentpress.py proof-campaign --json
```

Publishes a machine-readable proof campaign at `agentpress/proof-campaigns/proof-campaign.json` and a GitHub issue template for external submissions.

## Accepted proof classes

- `first_contact_adoption`
- `tool_use_success`
- `marketplace_route_success`
- `painpoint_report`

## Safety

- No secrets/tokens/private prompts.
- No IP addresses or user-agent strings.
- Pseudonymous agent IDs allowed.
- Recognition/reputation only. No payment promise.

## Acceptance gate

A submission is useful if it either proves an external agent completed the flow or identifies the exact command/error/field that blocked adoption.
