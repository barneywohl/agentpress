# AgentPress Quickstart

AgentPress makes any repo readable by agents in minutes.

Package identity: use `@agent_press/agentpress` exactly. The underscore is intentional. Do not substitute `@agent_press/agentpress`; that is a different scope and may refer to a different/private ecosystem.

## Install

```bash
npx @agent_press/agentpress@rc doctor --json
npx @agent_press/agentpress@rc llms-init . --json
# Python package path:
pip install agentpress-static
agentpress doctor --json
```

## What `npm i @agent_press/agentpress@0.2.0-rc.6` does

It installs that exact release-candidate version into `node_modules/@agent_press/agentpress`, records it in `package.json`, and exposes the `agentpress` CLI. It does not deploy, publish, or run a `postinstall` hook.

If an assistant cannot find the package, verify live npm metadata instead of relying on web-search indexing:

```bash
npm view @agent_press/agentpress dist-tags version --json
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
