# AgentPress

Make any repo readable by autonomous agents in under 60 seconds.

## Install

```bash
npm install -g @agent_press/agentpress
agentpress doctor --json
agentpress lint . --json
```

Python fallback:

```bash
pip install agentpress-static
agentpress doctor --json
agentpress lint . --json
```

## What it does

AgentPress publishes a small, machine-readable surface for agents:

- `llms.txt` — first-read instructions
- `.well-known/agentpress.json` — agent entrypoint map
- `.well-known/ai-ingestion.json` — crawler/agent ingestion policy
- `agentpress/agent-instructions.json` — agent operating contract
- `agentpress/schemas/index.json` — schema index
- schema validation, receipts, proof packs, and CLI gates

## Try the consumer demo

```bash
python3 scripts/agentpress.py doctor --json
python3 agentpress/demos/consumer/consumer_demo.py
```

AgentPress also supports `landing-receipt` proof receipts for adoption evidence.

## Current live endpoints

- Site: https://agentpress.pages.dev/
- npm: https://www.npmjs.com/package/@agent_press/agentpress
- PyPI: https://pypi.org/project/agentpress-static/
- Full reference: `agentpress/FULL_REFERENCE.md`
- Quickstart: `agentpress/QUICKSTART.md`

## Safety boundary

Allowed: read public files, validate schemas, summarize, cite, transform, prepare local patches, and create pull requests.

Requires human approval: external posts, registry publishes, production deploys, private data access, billing, phone, captcha, and 2FA flows.

Prohibited: secret exfiltration, deceptive tracking, spam, bypassing paywalls/captchas/2FA, impersonation, or unauthorized external writes.
