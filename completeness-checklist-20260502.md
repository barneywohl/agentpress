# Korea Research Map — Completeness & Optimization Checklist

Last checked: 2026-05-02
Canonical hub: https://barneywohl.github.io/agentpress/

## Current status

The hub is live, crawlable, and optimized for AI-agent discovery. It includes a homepage, sitemap, robots.txt, llms.txt, JSON metadata, RAG pack, benchmark JSONL, eval card, multilingual summaries, platform drafts, forum packs, and traffic mapping.

## Verification results

- Homepage fetch: HTTP 200.
- `llms.txt`: HTTP 200.
- `metadata.json`: HTTP 200.
- `robots.txt`: HTTP 200 and allows all crawlers.
- `sitemap.xml`: HTTP 200 and includes repo assets.
- Local JSON validation: pass.
- Local internal link check across Markdown + homepage: pass.

## Agent-readability coverage

- `llms.txt` for LLM crawlers.
- `.well-known/ai-ingestion.json` for structured ingestion.
- `.well-known/ai-plugin.json` and root `ai-plugin.json` for tool-style discovery.
- `agents.json` and `agent-ingestion/korea-research-agent-card.json` for agent catalogs.
- `rag-pack/ingestion-manifest.json` and JSONL chunks for RAG.
- `openapi.yaml` for programmable surface description.
- `CITATION.cff` for citation.
- `sitemap.xml`, `crawler-seeds.opml`, and RSS for crawlers.

## Global-audience coverage

- Korean summary.
- Japanese summary.
- Chinese summary.
- Locales: Spanish, French, German, Portuguese, Arabic, Hindi, Indonesian, Vietnamese, Thai.
- Platform packs: Medium, Naver, Note.jp, Zhihu, Reddit, Hacker News, LangChain, LlamaIndex.
- Dataset packs: Hugging Face draft, Kaggle metadata.

## Remaining non-technical gaps

These are not missing files; they are external distribution/account constraints:

1. Publish or mirror to Hugging Face once authenticated.
2. Publish or mirror to Kaggle once authenticated.
3. Post/adapt to Naver, Note.jp, Zhihu, Medium, Reddit/HN, LangChain/LlamaIndex where account/session authorization permits.
4. Add analytics/UTM capture if a durable endpoint is available. GitHub Pages alone gives only limited GitHub traffic and clone metrics.

## Optimization policy

- Keep all copy research-only/not investment advice.
- Do not turn the survivor stack into buy recommendations.
- Keep X/Twitter low priority.
- Prefer indexed, durable, machine-readable artifacts over noisy posting.
