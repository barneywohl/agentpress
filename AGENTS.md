# AGENTS.md — AgentPress Canonical Repo

AgentPress is the product: an agent-native article database and static publishing layer for AI agents.

## Start here

1. `llms.txt`
2. `.well-known/agentpress.json`
3. `.well-known/ai-ingestion.json`
4. `agentpress/articles/article-index.json`
5. `agentpress/AGENT_ARTICLE_DATABASE_SPEC.md`
6. `agentpress/schemas/README.md`

## Product rule

Do not treat historical Korea research files as the product identity. They are legacy stress-test material only. Product-facing work should optimize for:

- agent-native articles,
- article database indexes,
- task cards,
- source maps,
- freshness policies,
- allowed actions,
- eval artifacts,
- multilingual/global discovery,
- MCP/OpenAPI/RAG/crawler compatibility.

## Validation before shipping

```bash
python3 scripts/check_agentpress_positioning.py
python3 scripts/agentpress.py index-articles
python3 scripts/validate_agentpress_assets.py
python3 scripts/check_agentpress_availability.py --root .
```

External deploys should be pushed to `barneywohl/agentpress` and verified on `https://barneywohl.github.io/agentpress/`.
