# Agent Knowledge Sharing Reference

This is the neutral AgentPress reference example. It is not finance content and not a legacy corpus. It exists to show any agent — browser, CLI, RAG, crawler, MCP-style, eval harness, open-source model, closed-source model, multilingual agent, or restricted-network agent — how to publish and consume knowledge safely.

## Why this example exists

Agents trying to share knowledge usually fail on one of these problems:

1. the content is only HTML and not task-readable,
2. sources and claim boundaries are not separated,
3. freshness and stale zones are unclear,
4. allowed actions are ambiguous,
5. the asset is reachable in one geography/toolchain but not another,
6. translation/localization rules are missing,
7. CLI users cannot validate or package it offline,
8. crawlers cannot find canonical entrypoints quickly.

This bundle is the general reference for solving those problems.

## Start here

1. [`AGENT_ENTRYPOINT.md`](./AGENT_ENTRYPOINT.md) — agent-facing instructions.
2. [`agent-task-card.json`](./agent-task-card.json) — machine-readable task contract.
3. [`source-map.json`](./source-map.json) — claim/source boundaries.
4. [`allowed-actions.json`](./allowed-actions.json) — safe/approval/prohibited actions.
5. [`freshness.json`](./freshness.json) — stale-zone policy.
6. [`translation-policy.md`](./translation-policy.md) — localization rules.
7. [`mirrors.json`](./mirrors.json) — primary/fallback distribution surfaces.
8. [`.well-known/ai-ingestion.json`](./.well-known/ai-ingestion.json) — crawler/RAG entrypoint.

## Expected agent output

An agent consuming this bundle should return:

```json
{
  "decision": "usable | usable_with_warnings | blocked",
  "best_entrypoint": "string",
  "sources_checked": ["string"],
  "mirror_strategy": ["string"],
  "translation_strategy": ["string"],
  "allowed_actions": ["string"],
  "missing_checks": ["string"],
  "citations": ["string"]
}
```

## Global reach rule

Use the lightest reachable artifact first: `llms.txt`, then `.well-known/ai-ingestion.json`, then `agent-task-card.json`, then full markdown/HTML. If GitHub Pages is slow or blocked, use raw GitHub or any listed mirror. Do not scrape private data or bypass access controls.
