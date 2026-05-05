# AgentPress

[![npm version](https://img.shields.io/npm/v/@agent_press/agentpress.svg)](https://www.npmjs.com/package/@agent_press/agentpress) [![PyPI](https://img.shields.io/pypi/v/agentpress-static.svg)](https://pypi.org/project/agentpress-static/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Make any repo readable by AI agents in 60 seconds. AgentPress is the `llms.txt` + `.well-known` onboarding kit for repos: it publishes agent instructions, schema gates, proof receipts, and machine-readable surfaces for common coding agents and agent frameworks.

## Compatibility

| Runtime | Support level | Notes |
|---------|---------------|-------|
| Claude (Anthropic) | Full | Native `llms.txt` plus agent contracts. |
| GPT-4 / Codex | Full | Uses `llms.txt` and machine-readable entrypoints. |
| Gemini | Full | Uses `llms.txt` and machine-readable entrypoints. |
| GLM-4 (Zhipu) | Full | Uses `llms.txt` and `.well-known/agentpress.json`. |
| LangChain | Full | Uses `llms.txt` and structured manifests. |
| CrewAI | Full | Uses `llms.txt` and structured manifests. |
| MCP / ACP | Full | Uses `.well-known` manifests and agent contracts. |
| Cline / Roo / OpenHands | Compatible | Uses `llms.txt` as the first-read handoff. |

## Install

```bash
npm install -g @agent_press/agentpress
agentpress doctor --json
agentpress llms-init . --json
agentpress lint . --json
agentpress adoption-fixpack --json
```

**Runtime note:** the npm package includes a Node-native first-run path for `agentpress doctor --json`, `agentpress start`, and `agentpress llms-init . --json`. The full command catalog still requires Python >=3.10 on `PATH` (or set `PYTHON=/path/to/python3.10+`).

Python fallback:

```bash
pip install agentpress-static
agentpress doctor --json
agentpress lint . --json
agentpress adoption-fixpack --json
```

## How discovery works

AgentPress publishes a `.well-known/agentpress.json` entrypoint and `llms.txt` to your repo. Agent frameworks that follow the llms.txt spec — Claude, GPT-4, Gemini, LangChain, CrewAI, and MCP-compatible tools — fetch these on first contact and can act on your repo without reading every file.

## What it does

AgentPress publishes a small, machine-readable surface for agents:

- `llms.txt` — first-read instructions
- `.well-known/agentpress.json` — agent entrypoint map
- `.well-known/ai-ingestion.json` — crawler/agent ingestion policy
- `agentpress/agent-instructions.json` — agent operating contract
- `agentpress/schemas/index.json` — schema index
- `agentpress/mcp/mcp-static-catalog.json` — static MCP-style command-template catalog
- schema validation, receipts, proof packs, and CLI gates

MCP framing: AgentPress ships static MCP-style manifests for discovery today. It does **not** run a live stdio/SSE MCP server yet; `agentpress mcp-serve` is roadmap work unless a later release explicitly implements it.

## Try the consumer demo

```bash
python3 scripts/agentpress.py doctor --json
python3 agentpress/demos/consumer/consumer_demo.py
```

AgentPress also supports `landing-receipt` proof receipts for adoption evidence. Use `agentpress adoption-fixpack --json` to generate the exact first-contact proof commands and a privacy-safe handoff pack for one outside agent.

## High-signal agent workflows

Generate utility-first packs for real agent-builder painpoints, without posting anywhere:

```bash
python3 scripts/agentpress.py gorilla-utility-pack --json
python3 scripts/agentpress.py gorilla-utility-pack --no-write --json
```

Build/check native adapter packs for Cline, Roo, OpenHands, MCP, LangChain, LlamaIndex, and CrewAI:

```bash
python3 scripts/agentpress.py native-adapter-kit --target all --json
python3 scripts/agentpress.py native-adapter-check agentpress/adapters/native --json
```

Create a compact context package or handoff root when the full repo is too large for an agent turn:

```bash
python3 scripts/agentpress.py context-package-init . --out agentpress/context/handoff-root --json
python3 scripts/agentpress.py handoff-root-pick . --out agentpress/context/handoff-root --json
```

Before any release promotion, keep proof/release gates explicit:

```bash
python3 scripts/agentpress.py docs-command-check --json
python3 scripts/agentpress.py release-promote-checklist --no-network --no-write --json --strict
```

For a clean external proof bundle, run:

```bash
agentpress external-proof-run --agent-id <agent-id> --runtime codex --out /tmp/agentpress-proof-<agent-id> --json
```

This writes `doctor.json`, `first-run-wizard.json`, `self-test.jsonl`, `landing-receipt.json`, `submission-pack/`, and `external-proof-run.json` locally. It never performs external writes; human approval is required before posting a proof issue or PR.

## Current live endpoints

- Site: https://barneywohl.github.io/agentpress/
- Cloudflare mirror: pending; canonical live base is https://barneywohl.github.io/agentpress/
- npm: https://www.npmjs.com/package/@agent_press/agentpress
- PyPI: https://pypi.org/project/agentpress-static/
- Security/disclosure: `SECURITY.md`
- Full reference: `agentpress/FULL_REFERENCE.md`
- Quickstart: `agentpress/QUICKSTART.md`

## Safety boundary

Allowed: read public files, validate schemas, summarize, cite, transform, prepare local patches, and create pull requests.

Requires human approval: external posts, registry publishes, production deploys, private data access, billing, phone, captcha, and 2FA flows.

Prohibited: secret exfiltration, deceptive tracking, spam, bypassing paywalls/captchas/2FA, impersonation, or unauthorized external writes.
