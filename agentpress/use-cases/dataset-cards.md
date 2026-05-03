# Use AgentPress for Dataset Cards

Reference bundle: [`../examples/dataset-card-reuse/`](../examples/dataset-card-reuse/)

Best for: datasets, model eval packs, RAG corpora, benchmark cards, data catalogs.

Agents need:
- provenance,
- licensing/reuse boundaries,
- source claims,
- freshness windows,
- evaluation rows,
- missing-check reporting.

Run:

```bash
python3 scripts/agentpress.py validate agentpress/examples/dataset-card-reuse --json
python3 scripts/agentpress.py audit agentpress/examples/dataset-card-reuse --json
python3 scripts/agentpress.py eval agentpress/examples
```
