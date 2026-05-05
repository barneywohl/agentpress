# AgentPress native adapter: MCP

Purpose: expose AgentPress's static catalog and validation receipts to MCP-capable agents without credentials or external side effects.

## Install

```bash
npm install -g @agent_press/agentpress@rc
# or consume static resources directly from:
# https://barneywohl.github.io/agentpress/agentpress/mcp/mcp-static-catalog.json
```

## MCP resource mapping

Use `mcp-agentpress-static-server.json` as the static server descriptor. Minimum resources:

```json
{
  "resources": [
    "agentpress/tools/agentpress-tools.json",
    "agentpress/mcp/mcp-static-catalog.json",
    "agentpress/approvals/approval-gates.json",
    "agentpress/policies/tool-permission-policy.json",
    "agentpress/schemas/public/public-schema-bundle.json"
  ]
}
```

## Smoke command

```bash
agentpress mcp-catalog --json
agentpress tool-contract-check --json
agentpress tool-output-sample-generate --check --json
```

## Proof command

```bash
agentpress landing-receipt \
  --agent-id mcp-client-local \
  --runtime mcp \
  --discovery-channel native-adapter \
  --capability static_catalog_read \
  --out /tmp/mcp-agentpress-receipt.json \
  --json
agentpress submission-pack --receipt /tmp/mcp-agentpress-receipt.json --out /tmp/mcp-agentpress-submit --json
```

## Safety policy

- Static resources only by default.
- No credentialed MCP tools are required for AgentPress discovery.
- External writes must be separately approved and logged.
- Do not claim MCP ecosystem adoption until an independent MCP client receipt is accepted.

## Common remediation

- Catalog mismatch: run `agentpress tool-contract-check --json`.
- Sample drift: run `agentpress tool-output-sample-generate --check --json`, regenerate only if expected.
- Schema error: validate against `agentpress/schemas/public/public-schema-bundle.json` and submit a blocker receipt.
