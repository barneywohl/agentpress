# AgentPress MVP

AgentPress is the working implementation of the "Substack for agents" idea: a simple static publication generator for content that agents can ingest, execute, evaluate, crawl, and cite.

## What it creates

Each AgentPress publication includes:

- `README.md` — human overview
- `AGENT_ENTRYPOINT.md` — task instructions for AI agents
- `agent-task-card.json` — machine-readable objective, input/output contract, scoring rubric
- `source-map.json` — claims/sources/citation map
- `freshness.json` — timestamp, stale zones, and refresh policy
- `allowed-actions.json` — safe agent action boundaries
- `citation-policy.md` — citation rules and disclaimer framing
- `.well-known/ai-ingestion.json` — machine-readable ingestion manifest
- `llms.txt` — compact crawler/LLM brief
- `sitemap.xml` — crawl surface
- `CITATION.cff` — citation metadata
- `disclaimer.md` — research-only/legal framing


## Master spec

The active build spec is [`MASTER_SPEC.md`](MASTER_SPEC.md). It defines the required publication bundle, CLI commands, schemas, scoring rubric, registry roadmap, and immediate execution plan. Current sprint tasks are tracked in [`EXECUTION_BOARD.md`](EXECUTION_BOARD.md); today's same-day chunk backlog is [`TODAY_CHUNKS.md`](TODAY_CHUNKS.md).

## Agent usability standard

AgentPress publications should pass the [Agent Usability Standard](AGENT_USABILITY_STANDARD.md): a fresh agent should understand, verify, cite, and act on the publication in under 60 seconds without scraping guesswork.

## CLI

```bash
python3 scripts/agentpress.py init out-dir --title "My Agent Benchmark"
python3 scripts/agentpress.py validate out-dir
python3 scripts/agentpress.py audit out-dir
python3 scripts/agentpress.py score out-dir
python3 scripts/agentpress.py build out-dir --out public-dir
python3 scripts/agentpress.py list
python3 scripts/agentpress.py list --json
python3 scripts/agentpress.py build-all agentpress/examples --out public/agentpress --clean
python3 scripts/validate_agentpress_assets.py
```

Score emits a machine-readable report plus badge markdown, e.g. `![AgentPress score](https://img.shields.io/badge/AgentPress-100%2F100-blue)`.


## Schemas and CI

Machine-readable contracts live in [`schemas/`](./schemas/). The repository CI workflow runs:

```bash
python3 scripts/validate_agentpress_assets.py
python3 scripts/agentpress.py build agentpress/examples/liquidity-trap --out /tmp/agentpress-liquidity
python3 -m build
python3 -m pip install dist/*.whl
agentpress init /tmp/agentpress-package-smoke --title "Package Smoke" --canonical "https://example.com/package-smoke/"
agentpress audit /tmp/agentpress-package-smoke
agentpress score /tmp/agentpress-package-smoke
agentpress build /tmp/agentpress-package-smoke --out /tmp/agentpress-package-smoke-public
python3 scripts/check_agentpress_availability.py --root .
```

This keeps generated bundles parseable, auditable, scorable, installable, and static-host deployable.


## Installable CLI

This repo includes package metadata so agents and developers can install the CLI locally:

```bash
pipx install .
agentpress --help
agentpress init /tmp/my-agent-site --title "My Agent Site"
```

The direct repo command remains supported for zero-install usage. See [`RELEASE_NOTES.md`](RELEASE_NOTES.md) for the package smoke-test and release gate.

## Reference examples

See the [examples mini-registry](./examples/README.md).

- [`examples/api-docs-handoff`](./examples/api-docs-handoff/) — neutral API documentation handoff reference
- [`examples/incident-runbook-sharing`](./examples/incident-runbook-sharing/) — neutral operations/runbook sharing reference
- [`examples/dataset-card-reuse`](./examples/dataset-card-reuse/) — neutral dataset card reuse reference

## Why this matters

A normal website is optimized for human attention. AgentPress is optimized for agent execution:

1. the agent knows what task to run
2. the task has a schema
3. the output can be scored
4. the files are crawlable
5. citations/disclaimers are explicit

This repo is the reference implementation.
## Global agent discovery surface

AgentPress now exposes root-level and product-level discovery for a global world of agents:

- [`AGENT_START_HERE.md`](AGENT_START_HERE.md) — fast path for autonomous agents
- [`WHAT_AGENTS_WANT.md`](WHAT_AGENTS_WANT.md) — build target from agent needs
- [`GLOBAL_AGENT_COMPATIBILITY_MATRIX.md`](GLOBAL_AGENT_COMPATIBILITY_MATRIX.md) — compatibility by agent family
- [`protocols/README.md`](protocols/README.md) — OpenAPI, MCP-style, feed, and registry surfaces
- [`feeds/agentpress-feed.json`](feeds/agentpress-feed.json) and [`feeds/rss.xml`](feeds/rss.xml) — crawler/update feeds
- Root `.well-known/ai-ingestion.json` and `.well-known/agentpress.json` — stable discovery manifests
