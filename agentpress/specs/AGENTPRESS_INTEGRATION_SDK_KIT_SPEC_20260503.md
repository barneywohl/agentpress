# AgentPress Integration SDK Kit Spec — 2026-05-03

## Real feature

AgentPress now ships copy-paste, zero-dependency SDK clients for external agents and a smoke test proving the integration endpoints resolve.

## Commands

```bash
python3 scripts/agentpress.py integration-sdk-kit --json
python3 scripts/agentpress.py sdk-smoke --json
```

## Outputs

- `agentpress/integrations/sdk/python/agentpress_sdk.py`
- `agentpress/integrations/sdk/js/agentpress-sdk.mjs`
- `agentpress/integrations/sdk/manifest.json`
- `agentpress/integrations/sdk/sdk-smoke.json`

## Safety

Read-only SDK clients. No credentials, no write API, no wallet/payment calls.
