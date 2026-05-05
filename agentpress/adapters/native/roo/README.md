# AgentPress native adapter: Roo

Purpose: give Roo users a concrete custom-mode pattern for AgentPress validation and proof receipts.

## Install

```bash
npm install -g @agent_press/agentpress@rc
# or:
python3 -m pip install agentpress-static==0.2.0rc4
```

## Roo custom-mode snippet

Create a Roo custom mode with this operating rule:

```md
AgentPress mode:
- Read `.well-known/agentpress.json`, `llms.txt`, and `agentpress/mcp/mcp-static-catalog.json` before repository claims.
- Run `agentpress doctor . --json` and preserve output.
- Run `agentpress docs-command-check --json` before editing docs/tool claims.
- Respect `agentpress/approvals/approval-gates.json`; never perform external writes without explicit approval.
- Finish by creating either a landing receipt or a blocker receipt.
```

Optional local config file: `roo-agentpress.json` in this directory.

## Proof command

```bash
agentpress landing-receipt \
  --agent-id roo-local \
  --runtime roo \
  --discovery-channel native-adapter \
  --capability docs_command_check \
  --out /tmp/roo-agentpress-receipt.json \
  --json
agentpress submission-pack --receipt /tmp/roo-agentpress-receipt.json --out /tmp/roo-agentpress-submit --json
```

## Safety policy

- Use read-only checks until a human explicitly approves writes.
- Blocker receipts are valid proof; do not hide failures.
- No telemetry, secrets, or private repo content should be submitted.
- Do not claim Roo adoption until an independent Roo receipt is reviewed.

## Common remediation

- Missing AgentPress files: `agentpress llms-init . --json`.
- Broken tool schema: `agentpress tool-contract-check --json`.
- Stale samples: `agentpress tool-output-sample-generate --check --json`.
