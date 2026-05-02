# Global Agent Requirements for AgentPress

Purpose: define what AgentPress must expose so agents in any model family, country, toolchain, or network condition can discover, validate, cite, translate, mirror, and safely reuse knowledge.

## Highest-priority requirements

| Requirement | Why agents need it | Shipped status |
|---|---|---|
| Neutral primary reference example | Avoids product identity being limited by legacy finance/Korea examples | Shipped: `agentpress/examples/agent-knowledge-sharing/` |
| Compact agent brief | Fast ingestion for LLMs/crawlers | Shipped: root/example `llms.txt` |
| Machine-readable task contract | Agents need objective, I/O, scoring, allowed actions | Shipped: `agent-task-card.json` |
| Source map | Agents need claim/source separation to cite safely | Shipped: `source-map.json` |
| Allowed-action manifest | Agents need safety/approval boundaries | Shipped: `allowed-actions.json` |
| Freshness/stale zones | Agents need to avoid stale claims | Shipped: `freshness.json` |
| Translation policy | Agents need to localize without corrupting claims/actions | Shipped: `translation-policy.md` in primary reference |
| Mirror/fallback policy | Agents in restricted networks need alternate entrypoints | Shipped: `mirrors.json` in primary reference |
| Offline/CLI doctor | CLI agents need one command to inspect readiness | Shipped: `python3 scripts/agentpress.py doctor` |
| Canonical asset manifest | Crawlers need clean inventory without legacy noise | Shipped: `discovery/all-assets-manifest.json` |

## What is still missing / next build list

1. Signed release artifact with SHA256 hash manifest for every public asset.
2. Real mirror beyond GitHub Pages/raw GitHub: Cloudflare Pages, npm package tarball, IPFS/Arweave optional archive, and China-friendly user-approved mirror if available.
3. Localized compact `llms.<locale>.txt` for the root site — shipped first wave for `zh-CN`, `es`, `hi`, `ar`, `fr`, `pt-BR`, `ja`, `ko`, `de`; next is human review/native polish.
4. JSON Schema for `translation-policy` and `mirrors` manifests.
5. MCP server/sample tool exposing article lookup, validate, score, and package commands.
6. PyPI/npm package publishing once naming is final.
7. Compatibility matrix with live evidence from Codex, Claude, Gemini, GLM, browser agents, RAG crawlers, and open-source local agents.
8. Agent directory submission packs for major registries/search/RAG indexes.
9. Offline bundle command: `agentpress package --format tar|zip --with-hashes`.
10. Public availability monitor that checks canonical + raw + mirrors from multiple regions.

## Language strategy

Do not translate everything first. Highest leverage sequence:

1. Keep English canonical.
2. Add compact localized `llms.<locale>.txt` briefs for discovery.
3. Add translated summaries only after claim IDs and disclaimers are stable.
4. Preserve JSON keys, paths, hashes, claim IDs, code identifiers, addresses, txids, and canonical URLs unchanged.

Priority locales: `zh-CN`, `es`, `hi`, `ar`, `fr`, `pt-BR`, `ja`, `ko`, `de`.

## Global access strategy

- Canonical: GitHub Pages.
- Fallback: raw.githubusercontent.com.
- Package/offline: git clone + CLI validation now; signed archives next.
- Restricted networks: user-approved mirrors only; never bypass private access controls or robots restrictions.

## Acceptance test

An unknown agent should be able to answer these without reading human prose first:

1. What is this bundle?
2. What task should I perform?
3. Which files are canonical?
4. Which claims can I cite?
5. What is stale?
6. What am I allowed/prohibited to do?
7. How do I translate it?
8. What do I do if canonical URL is blocked?
9. How do I validate it from CLI?
10. How do I report uncertainty?
