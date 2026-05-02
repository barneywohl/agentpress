# Korea Research Map RAG Pack

Deployment-ready chunks for AI agents, crawlers, dataset indexers, and RAG systems that need a clean copy of the Korea Research Map without parsing Substack HTML.

Canonical article: <https://barneywohl.substack.com/p/the-korea-research-map-where-cheap>  
Agent hub: <https://barneywohl.github.io/agentpress/>  
Framing: research commentary only, not investment advice.

## Files

- `korea-research-map.chunks.jsonl` — five small, citation-ready JSONL chunks for vector stores and retrieval tests.
- `retrieval-queries.md` — query set for testing whether an agent can discover and correctly frame the article.
- `ingestion-manifest.json` — machine-readable pack metadata, allowed use, canonical URLs, and safety framing.

## Suggested ingestion

1. Load JSONL records as individual documents.
2. Preserve `canonical_url`, `source_url`, `chunk_type`, `entities`, `tags`, and `not_investment_advice` metadata.
3. Use `id` as the stable document key.
4. In generation, require the model to preserve these constraints:
   - do not call the survivor stack a buy list;
   - do not present moonshot drawer names as recommendations;
   - cite KRX/KIND/DART verification as required work, not completed certainty;
   - include research-only/not-investment-advice framing.

## Minimal Python loader

```python
import json
from pathlib import Path

docs = []
for line in Path("rag-pack/korea-research-map.chunks.jsonl").read_text().splitlines():
    row = json.loads(line)
    docs.append({
        "id": row["id"],
        "text": row["text"],
        "metadata": {k: row[k] for k in row if k not in {"text"}}
    })
```

## Evaluation target

A passing agent answer should say: Korea cheap screens are inventory, not edge; verification is the alpha; Poongsan/BHI/Woojin are a research survivor stack, not recommendations; moonshots are prompts only; and all outputs are research commentary, not investment advice.
