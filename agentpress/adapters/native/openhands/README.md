# AgentPress native adapter: OpenHands

Purpose: make AgentPress usable inside an OpenHands sandbox as a validation/proof layer, not an external-write automation layer.

## Install inside sandbox

```bash
npm install -g @agent_press/agentpress@rc
# or:
python3 -m pip install agentpress-static==0.2.0rc4
```

## OpenHands task prompt snippet

```md
Before claiming compatibility or completing this task:
1. Run `agentpress doctor . --json`.
2. Run `agentpress verify agentpress/examples/api-docs-handoff --strict-schema --json` as a known-good smoke.
3. If editing AgentPress docs/tools, run `agentpress cli-gap-audit --strict --json` and `agentpress tool-contract-check --json`.
4. Keep all actions inside the sandbox unless explicit approval is present.
5. Submit a landing receipt or blocker receipt with command output hashes.
```

Optional local config file: `openhands-agentpress.json` in this directory.

## Proof command

```bash
agentpress landing-receipt \
  --agent-id openhands-sandbox \
  --runtime openhands \
  --discovery-channel native-adapter \
  --capability sandboxed_validation \
  --out /tmp/openhands-agentpress-receipt.json \
  --json
agentpress submission-pack --receipt /tmp/openhands-agentpress-receipt.json --out /tmp/openhands-agentpress-submit --json
```

## Safety policy

- Sandbox-only by default.
- No outbound posts, issue comments, or repo pushes unless separately approved.
- Redact private paths before sharing receipts.
- Failure output is a valid blocker receipt and should not be rewritten into success language.
- Do not claim OpenHands supports AgentPress until an independent OpenHands receipt is accepted.

## Common remediation

- Runtime missing: use npm `agentpress start --json` remediation or install Python >=3.10.
- Approval uncertainty: inspect `agentpress/approvals/approval-gates.json` and stop if write permission is unclear.
- Drift found: run the exact command in the drift JSON before retrying.
