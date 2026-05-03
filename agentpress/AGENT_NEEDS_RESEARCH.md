# AgentPress — What Agents Need

Generated: 2026-05-02

AgentPress should solve the practical problems agents hit when trying to use a human-first website: unclear entrypoints, hidden source evidence, missing task contracts, stale data, unsafe action boundaries, no runtime-specific instructions, no multilingual metadata, and no contract profile/identity layer for agent knowledge.

## Core problems agents have

| Problem | Why it matters | AgentPress feature |
|---|---|---|
| No obvious machine entrypoint | Agents waste context guessing where to start. | `llms.txt`, `.well-known/agentpress.json`, `.well-known/ai-ingestion.json`, `AGENT_ENTRYPOINT.md` |
| Human prose but no task contract | Agents cannot know expected inputs/outputs. | `agent-task-card.json` with schema, objective, required fields, scoring rubric |
| Claims without source map | RAG/coding agents hallucinate or cite unsupported pages. | `source-map.json`, `citation-policy.md`, verified claim IDs |
| Stale or temporal claims | Agents cannot know when data must be refreshed. | `freshness.json`, stale zones, last reviewed timestamp |
| Unsafe ambiguity around actions | Agents do not know what they may read/write/call. | `allowed-actions.json` with public, approval-required, prohibited actions |
| Browser-only discovery | Crawlers/RAG systems miss content hidden behind UI. | Static markdown, JSON, JSONL, sitemap, JSON Feed, RSS, OpenAPI map |
| Protocol fragmentation | MCP-style/coding/browser agents look for different surfaces. | Protocol pack: MCP static resources, OpenAPI, schemas, feed manifests |
| No eval artifact | Builders cannot verify whether ingestion worked. | `evals/*.jsonl`, score rubric, validation CLI |
| No localization metadata | Global agents/languages cannot choose the right artifact. | language/region/persona metadata and optional `llms.<locale>.txt` |
| No reusable agent contract profile | Agent knowledge is scattered across repos, chats, docs, and memory. | Agent contract profile pages: public capability/knowledge/contract profile bundles |

## Feature requirements by agent family

### Browser agents
- Agent fallback page with visible links to machine files.
- Short start path and no login requirement for public metadata.
- Screenshot-friendly page states and clear CTA hierarchy.

### Coding agents
- Repo-native docs, schemas, CLI, validation commands, examples, and changelog.
- `AGENTS.md`/`llms.txt` style project conventions.
- Small files with deterministic formats.

### RAG / indexing agents
- Chunkable markdown and JSONL.
- Source maps with claim IDs.
- Freshness windows and stale zones.
- Canonical URLs and raw fallbacks.

### Search crawlers
- `robots.txt`, `sitemap.xml`, RSS/JSON Feed, canonical URLs.
- Stable no-auth public URLs.
- Query maps that describe intent without keyword stuffing.

### MCP-style agents
- Resource, prompt, and tool-like descriptions even when served statically.
- Typed schemas and transport-agnostic capability descriptions.
- Clear separation of read-only resources and write/action tools.

### Eval harnesses
- Machine-readable expected output schemas.
- JSONL examples.
- Scoring rubric and pass/fail conditions.
- Negative/adversarial cases.

### Global / multilingual agents
- Language tags per bundle.
- Locale-specific summaries or `llms.<locale>.txt` stubs.
- Unicode-safe filenames/URLs and region metadata.
- Explicit translation policy: translate instructions, not source claims unless verified.

## Research-informed external signals

Public docs and ecosystem signals point in the same direction:
- `llms.txt` is becoming a common agent discovery/understanding file.
- MCP-style systems expect discoverable resources, prompts, tools, schemas, and descriptions.
- Agent frameworks emphasize memory/state, context providers, middleware, tool integration, and observability.
- Coding-agent ecosystems increasingly rely on repo-local instructions, skills, schemas, and installable examples.

## Agent implementation rule

AgentPress should not just publish articles. It should publish **agent-operable knowledge objects**:

1. agent fallback page,
2. agent entrypoint,
3. machine task card,
4. source/citation map,
5. freshness/state policy,
6. allowed-action boundary,
7. eval harness,
8. protocol manifests,
9. language/region metadata,
10. optional agent/contract profile identity page.


## Jake correction: database before contract profiles

The immediate product should be a whole database of agent-native articles set up the way agents want: indexable by task type, claims, sources, freshness, language, domain, eval coverage, and allowed actions. Contract profiles can come later as a view over who/what maintains article collections.

See `AGENT_ARTICLE_DATABASE_SPEC.md`.

## Build priority

1. Finish universal reachability + manifest cleanup.
2. Add contract profile schema for agent knowledge pages.
3. Add multilingual metadata/stubs.
4. Add MCP/OpenAPI/schema completeness checks.
5. Add evals for each major agent family.
6. Add contract profile generator CLI command.
