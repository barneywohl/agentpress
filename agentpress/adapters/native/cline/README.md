# AgentPress native adapter: Cline

Purpose: make AgentPress copy/pasteable for Cline users without claiming external adoption.

## Install

```bash
npm install -g @agent_press/agentpress@rc
# or, for Python-first users:
python3 -m pip install agentpress-static==0.2.0rc4
```

## Cline setup snippet

Add AgentPress as a local CLI-backed workflow in your Cline project instructions:

```md
Use AgentPress before claiming repository/tool compatibility:
1. Run `agentpress doctor . --json`.
2. Run `agentpress llms-init . --json` if llms.txt or .well-known/agentpress.json is missing.
3. Run `agentpress verify agentpress/examples/api-docs-handoff --strict-schema --json` for a known-good bundle smoke.
4. Before external writes, inspect `agentpress/approvals/approval-gates.json` and require explicit approval.
5. If the run fails, produce a blocker receipt instead of claiming support.
```

Optional local config file: `cline-agentpress.json` in this directory.

## Proof command

```bash
agentpress landing-receipt \
  --agent-id cline-local \
  --runtime cline \
  --discovery-channel native-adapter \
  --capability validate_agentpress_bundle \
  --out /tmp/cline-agentpress-receipt.json \
  --json
agentpress submission-pack --receipt /tmp/cline-agentpress-receipt.json --out /tmp/cline-agentpress-submit --json
```

## Safety policy

- No external writes by default.
- No credentials are required.
- Treat failed setup as useful evidence: submit a blocker receipt instead of editing claims.
- Do not claim Cline supports AgentPress unless a real Cline user/run submits an accepted receipt.

## Common remediation

- Python missing: run `agentpress start --json` for npm-side remediation, or install Python >=3.10.
- Missing surfaces: run `agentpress llms-init . --json`.
- Schema failure: run `agentpress verify <bundle> --strict-schema --json` and attach the JSON error to the blocker receipt.
