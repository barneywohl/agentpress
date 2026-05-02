# Substack Notes agent-discovery drafts

Prepared: 2026-05-02
Channel: Substack Notes
Status: repo-hosted draft pack; fresh directive received 2026-05-02 for ethical external distribution, but posting still requires an authenticated Barney-owned Substack session and channel-specific fit checks.

Purpose: ethical, non-spammy follow-up copy that points builders and AI agents to the Korea Research Map artifacts without making investment recommendations.

## Note 1 — agent benchmark angle

Korea is a useful stress test for stock-research agents because cheap screens fail in very specific ways: wrong entity, stale assets, trapped cash, thin liquidity, and theme exposure that never reaches cash flow.

I packaged the Korea Research Map as an agent/crawler/RAG bundle:

- benchmark JSONL for deletion-quality evals
- RAG chunks and retrieval queries
- KRX/KIND/DART verification prompts
- multilingual summaries and crawler metadata

Research methodology only, not investment advice.

https://barneywohl.github.io/agentpress/

## Note 2 — crawler/RAG angle

If you are building financial RAG or research-agent evals, the hard part is not finding more tickers. It is teaching the system when to delete a seductive idea.

The Korea Research Map repo now includes a crawler-friendly `llms.txt`, dataset card, RAG manifest, sitemap/RSS, and verification prompts built around Korean public-equity failure modes.

Useful starting point for agents: verify KRX/KIND identity, DART filings, liquidity/access, related-party economics, and theme-to-P&L bridge before generating a thesis.

https://github.com/barneywohl/agentpress

## Note 3 — concise human hook

A cheap ticker is not a thesis.

The Korea Research Map is now packaged for AI agents and RAG builders as a deletion benchmark: can the system kill weak Korea ideas before it invents a story?

Includes dataset, eval card, prompts, RAG pack, crawler metadata, and multilingual summaries.

Research commentary only. Not investment advice.

https://barneywohl.github.io/agentpress/

## Note 4 — builder CTA

Builder request: try the Korea Cheap Screen Deletion Benchmark against a stock-research agent.

Pass condition: the agent shrinks the list, verifies entity/filings/liquidity, flags uncertainty, and refuses to turn every cheap-looking Korea name into a recommendation.

Repo artifacts are prepared for crawlers and agent catalogs: `llms.txt`, `ai-ingestion.json`, RAG chunks, dataset JSONL, eval card, and sitemap.

https://github.com/barneywohl/agentpress
