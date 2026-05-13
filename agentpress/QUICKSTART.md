# AgentPress Quickstart

`agents.txt` for any repo. Tell autonomous AI agents what they're allowed to do, in under 60 seconds.

> **Package identity:** the public npm package is `@agent_press/agentpress` (with the underscore). It is not `@agentpress/agentpress` — that scope is owned by a different team. Verify with `npm view @agent_press/agentpress dist-tags --json` if in doubt.

## Install

```bash
# Node
npm install -g @agent_press/agentpress

# Python
pip install agentpress-static
```

Both expose the same `agentpress` CLI with the same four verbs.

## Create an agents.txt at your repo root

```bash
cd ~/your-repo
agentpress init
```

You'll be asked 5 questions (maintainer email, AI disclosure required, allow agent PRs, protect sensitive paths, add CI lint). All five have sensible defaults; press Enter to accept.

Or skip the prompts entirely:

```bash
agentpress init --non-interactive
```

What lands in your repo:
- `agents.txt` at the root — the contract
- `.github/workflows/agentstxt.yml` — CI lint on every PR (only if you have `.github/workflows/`)
- `agentpress/receipts/init_*.json` — proof of when init ran

## Check it stays valid

```bash
agentpress lint            # exit 0 if valid
agentpress lint --json     # CI-friendly JSON
agentpress lint --strict   # warnings escalate to errors
```

## Repo health check

```bash
agentpress doctor          # 9-point check: Node version, parser, agents.txt, CI workflow, badge
agentpress doctor --json
```

## Cryptographic proof receipt

```bash
agentpress receipt                # writes agentpress/receipts/<id>.json
agentpress receipt --stdout-only  # print, don't write
```

Each receipt includes the agents.txt sha256 so it can be verified later.

## Add the README badge

```markdown
[![agents.txt](https://img.shields.io/badge/agents.txt-v1.0-2563eb?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/barneywohl/agentpress)
```

Then [submit your repo to the registry](../registry/README.md).

## Safety boundary

The `agents.txt` you generate declares three sets of actions:

- **Allowed** — agents may do these without per-action approval. (read code, run tests, file PRs, comment on issues)
- **Requires human approval** — agents must pause. (schema migrations, billing/payments changes, production deploys)
- **Prohibited** — agents must refuse. (secret exfiltration, deceptive tracking, bypassing 2FA, impersonation)

These are the contract. AgentPress generates them, validates them, and gives you a content-addressed receipt every time.

## Legacy commands

If you used v0.x and need a command from that surface:

```bash
agentpress legacy <subcommand>
```

A one-time deprecation banner is shown. Legacy commands stay supported through v1.x and are removed in v2.0. Silence with `AGENTPRESS_LEGACY_QUIET=1`.

## Links

- Spec: [`docs/AGENTSTXT_SPEC.md`](../docs/AGENTSTXT_SPEC.md)
- Full reference: [`agentpress/FULL_REFERENCE.md`](FULL_REFERENCE.md)
- GitHub Action: [`actions/setup-action`](../actions/setup-action/)
- Browser extension: [`extensions/browser`](../extensions/browser/)
- VS Code extension: [`extensions/vscode`](../extensions/vscode/)
- MCP server: [`packages/mcp-server`](../packages/mcp-server/)
- Reference parsers: [TS](../packages/core/) · [Python](../python-core/)
