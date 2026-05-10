# AgentPress

Make any repo readable by autonomous agents in under 60 seconds.

> **Package identity:** the public npm package is `@agent_press/agentpress` (with the underscore). It is not `@agentpress/agentpress`, and it is not the unrelated/private `docs.agent.press` beta package family. If a browser or LLM says this package is private or missing, verify with `npm view @agent_press/agentpress dist-tags --json`.

## Install

```bash
npm install -g @agent_press/agentpress@rc
agentpress doctor --json
agentpress lint . --json
```

Pinned release candidate example:

```bash
npm i @agent_press/agentpress@0.2.0-rc.6
```

That command installs exactly `@agent_press/agentpress` version `0.2.0-rc.6`, adds it to your project dependencies, and exposes the `agentpress` CLI from `bin/agentpress.js`. This package has no `postinstall` script; installing it should not publish, deploy, contact private services, or mutate anything outside normal npm dependency installation.

Python fallback:

```bash
pip install agentpress-static
agentpress doctor --json
agentpress lint . --json
```

## What it is

`@agent_press/agentpress` is a public, static-first toolkit for making repositories easier for autonomous coding/research agents to understand and validate. It publishes a small, machine-readable surface for agents:

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
- npm metadata check: `npm view @agent_press/agentpress dist-tags version --json`
- PyPI: https://pypi.org/project/agentpress-static/
- Full reference: `agentpress/FULL_REFERENCE.md`
- Quickstart: `agentpress/QUICKSTART.md`

## Safety boundary

Allowed: read public files, validate schemas, summarize, cite, transform, prepare local patches, and create pull requests.

Requires human approval: external posts, registry publishes, production deploys, private data access, billing, phone, captcha, and 2FA flows.

Prohibited: secret exfiltration, deceptive tracking, spam, bypassing paywalls/captchas/2FA, impersonation, or unauthorized external writes.
