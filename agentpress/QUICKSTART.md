# AgentPress Quickstart

AgentPress makes any repo readable by agents in minutes.

## Install

```bash
npx @agent_press/agentpress doctor --json
npx @agent_press/agentpress llms-init . --json
# Python package path:
pip install agentpress-static
agentpress doctor --json
```

## Make a repo agent-readable

```bash
agentpress llms-init . --json
agentpress lint . --json
agentpress doctor --json
agentpress schema-validate-all --json
```

## What agents get

- `llms.txt` — first-read instructions
- `.well-known/agentpress.json` — machine entrypoint map
- `.well-known/ai-ingestion.json` — crawler/agent ingestion policy
- schemas, receipts, gates, and validator output

## Allowed / prohibited boundary

Allowed: read public files, validate schemas, summarize, cite, transform, create local patches, prepare PRs.

Requires human approval: external posts, package publishing, production deploys, account creation with billing/phone/2FA, private data access.

Prohibited: secret exfiltration, deceptive tracking, spam, bypassing paywalls/captchas/2FA, impersonation.

## High-signal workflows

Utility packs for agent-builder painpoints; local only, no external posting:

```bash
python3 scripts/agentpress.py gorilla-utility-pack --json
```

Native adapter packs and checks:

```bash
python3 scripts/agentpress.py native-adapter-kit --target all --json
python3 scripts/agentpress.py native-adapter-check agentpress/adapters/native --json
```

Large-repo context package / handoff root:

```bash
python3 scripts/agentpress.py context-package-init . --out agentpress/context/handoff-root --json
python3 scripts/agentpress.py handoff-root-pick . --out agentpress/context/handoff-root --json
```

Release/doc gates:

```bash
python3 scripts/agentpress.py docs-command-check --json
python3 scripts/agentpress.py release-promote-checklist --no-network --no-write --json --strict
```

## Consumer demo

```bash
python3 agentpress/demos/consumer/consumer_demo.py
```
