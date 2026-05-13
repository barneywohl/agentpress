# AgentPress

> `robots.txt` told crawlers what to crawl.
> `llms.txt` told LLMs what to read.
> **`agents.txt` tells autonomous AI agents what they're allowed to do.**

AgentPress drops an `agents.txt` and the supporting machine-readable surfaces into any repo in **under 60 seconds**, so coding agents (Claude Code, Cursor, Devin, Aider, Continue, Replit Agent) know what's allowed, what's prohibited, and what requires human approval.

## Install

```bash
npm install -g @agent_press/agentpress
agentpress init
```

Python fallback:
```bash
pip install agentpress-static
agentpress init
```

## What `agentpress init` does

In one interactive minute it adds:

- **`agents.txt`** at the repo root — the human + machine-readable contract
- **`.well-known/agentpress.json`** — structured entrypoint map for tools
- **`.well-known/ai-ingestion.json`** — crawler/agent ingestion policy
- **`agentpress/agent-instructions.json`** — operating contract with allowed/prohibited/requires-human-approval boundaries
- **GitHub Action template** — CI lint that fails PRs which violate the contract
- **README badge** — proof of adoption that links back to AgentPress

## CLI

| Command | What it does |
|---|---|
| `agentpress init` | Interactive wizard to drop `agents.txt` + supporting files |
| `agentpress lint .` | Validate the agent-readable surfaces; CI-friendly (exit 0/1, `--json`) |
| `agentpress doctor` | Health check — verify install, files, schema validity |
| `agentpress receipt` | Generate a cryptographic proof receipt that an agent ran a check |

## The safety contract

Every `agents.txt` declares three sets of actions:

- **Allowed** — agents may do these without asking. (read code, run tests, file PRs)
- **Requires human approval** — agents must pause for sign-off. (schema migrations, billing changes, deploys)
- **Prohibited** — agents must refuse. (secret exfiltration, deceptive tracking, bypassing 2FA)

This is the contract. AgentPress generates it, validates it, and gives you receipts.

## Why now

Coding agents are landing PRs in 2026. Most repos have no machine-readable answer to "what's safe?" `agents.txt` is the answer — same lineage as `robots.txt`, `sitemap.xml`, `llms.txt`. Adopt early, sleep better.

## Live endpoints

- Site: <https://agentpress.pages.dev/>
- npm: <https://www.npmjs.com/package/@agent_press/agentpress>
- PyPI: <https://pypi.org/project/agentpress-static/>
- Spec: [`agentpress/QUICKSTART.md`](agentpress/QUICKSTART.md)
- Full reference: [`agentpress/FULL_REFERENCE.md`](agentpress/FULL_REFERENCE.md)

## License

MIT. See [LICENSE](LICENSE).
