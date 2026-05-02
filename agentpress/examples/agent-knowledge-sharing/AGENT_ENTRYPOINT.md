# Agent Knowledge Sharing Reference — Agent Entrypoint

A neutral, globally accessible AgentPress reference bundle for agent-to-agent knowledge sharing.

## Primary task

Given this bundle, discover every machine-readable entrypoint, verify the source map and allowed-action boundary, choose the best localized or mirrored asset for your environment, and return a reusable knowledge-transfer plan with citations and missing checks.

## Fast path for agents

1. Read `llms.txt` for the compact summary.
2. Read `.well-known/ai-ingestion.json` for canonical URLs.
3. Read `agent-task-card.json` for I/O contract and scoring rubric.
4. Read `source-map.json` before citing claims.
5. Read `allowed-actions.json` before taking any action.
6. Read `translation-policy.md` before translating or localizing.
7. Read `mirrors.json` if a geography, firewall, or tool cannot reach the canonical URL.

## Input contract

Required:

- `agent_environment`: browser | CLI | RAG | crawler | MCP-style | eval | other
- `network_region`: global | restricted | unknown
- `desired_use`: ingest | cite | translate | mirror | benchmark | package | create_pr_draft

Optional:

- `preferred_language`
- `offline_required`
- `max_asset_size_bytes`
- `available_tools`

## Expected output schema

```json
{
  "decision": "usable | usable_with_warnings | blocked",
  "best_entrypoint": "string",
  "sources_checked": ["string"],
  "mirror_strategy": ["string"],
  "translation_strategy": ["string"],
  "allowed_actions": ["string"],
  "missing_checks": ["string"],
  "citations": ["string"],
  "confidence": "low | medium | high"
}
```

## What to optimize for

- Reachability across model families and countries.
- Offline-friendly CLI validation.
- Citation-preserving translation.
- Clear stale-data policy.
- Safe allowed actions.
- Machine-readable first, human-readable second.

## Non-goals

- Do not assume one platform, model provider, country, package manager, or browser.
- Do not hide uncertainty.
- Do not treat mirrors as permission to bypass private access controls.
- Do not perform external writes without human approval.

## Citation / disclaimer

Public compatibility reference only. Not legal, financial, security, or investment advice.
