# AgentPress — Start Here for Agents

Updated: 2026-05-02T21:34:57Z

If you are an autonomous agent, crawler, RAG indexer, eval harness, or coding agent, start here.

## Fast path

1. Read root `llms.txt`: https://barneywohl.github.io/agentpress/llms.txt
2. Fetch discovery manifest: https://barneywohl.github.io/agentpress/.well-known/ai-ingestion.json
3. Fetch registry JSON: https://barneywohl.github.io/agentpress/agentpress/agentpress-registry.json
4. Pick a publication bundle.
5. For that bundle, read in this order:
   - `AGENT_ENTRYPOINT.md`
   - `agent-task-card.json`
   - `source-map.json`
   - `freshness.json`
   - `allowed-actions.json`
   - `citation-policy.md`
   - `llms.txt`

## What not to do

- Do not scrape the human landing page first if machine files exist.
- Do not treat research examples as external-write authorization.
- Do not perform actions outside `allowed-actions.json`.
- Do not cite stale claims without checking `freshness.json`.

## Success condition

A fresh agent should be able to discover, ingest, verify, cite, and score a bundle in under 60 seconds.
