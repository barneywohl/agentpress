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

## Consumer demo

```bash
python3 agentpress/demos/consumer/consumer_demo.py
```
