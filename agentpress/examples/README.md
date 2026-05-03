# AgentPress Use-Now References

Each directory is a copyable instruction bundle for a large audience. Pick the one closest to your site, copy the structure, then run the AgentPress CLI gates.

## Pick a reference

| Audience | Reference | What it teaches agents |
|---|---|---|
| API/docs teams | [`api-docs-handoff/`](./api-docs-handoff/) | How to expose endpoints, source boundaries, allowed actions, freshness, and integration guidance safely. |
| Ops/SRE/security teams | [`incident-runbook-sharing/`](./incident-runbook-sharing/) | How to publish runbooks with escalation gates, read-only steps, stale zones, and approval boundaries. |
| Data/ML/RAG teams | [`dataset-card-reuse/`](./dataset-card-reuse/) | How to publish provenance, licensing, freshness, source claims, and reuse constraints. |
| Knowledge-base/help-center teams | [`agent-knowledge-sharing/`](./agent-knowledge-sharing/) | How to publish multilingual/mirrored knowledge that agents can cite and safely transform. |
| Agent framework/eval builders | [`universal-agent-reachability/`](./universal-agent-reachability/) | How to test whether browser agents, coding agents, RAG systems, crawlers, MCP-style agents, and eval harnesses can all use one bundle. |

## Use a reference

```bash
python3 scripts/agentpress.py validate agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py audit agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py score agentpress/examples/api-docs-handoff
python3 scripts/agentpress.py build agentpress/examples/api-docs-handoff --out /tmp/agentpress-api-docs
```

## Required files in every bundle

- `README.md`
- `AGENT_ENTRYPOINT.md`
- `agent-task-card.json`
- `source-map.json`
- `freshness.json`
- `allowed-actions.json`
- `.well-known/ai-ingestion.json`
- `llms.txt`
- `sitemap.xml`
- `citation-policy.md`
- `disclaimer.md`
- `evals/*.jsonl`
