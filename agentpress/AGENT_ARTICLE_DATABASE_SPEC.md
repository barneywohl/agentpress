# AgentPress Bundle Index Spec v0.1

AgentPress indexes bundles by the fields agents need for selection and safe reuse.

## Selection fields

- task type
- domains
- target agent families
- languages
- regions
- source-map availability
- freshness policy
- allowed-actions boundary
- eval coverage
- machine entrypoints

## Required generated indexes

- `article-index.json` — JSON bundle index, kept under this filename for compatibility.
- `article-index.jsonl` — one JSON row per bundle.
- `claim-index.jsonl` — claim-to-source lookup.
- `source-index.jsonl` — source inventory.
- `freshness-index.jsonl` — staleness lookup.
- `eval-index.jsonl` — eval inventory.
- `topics.json` — task/domain/agent-family lookup.
- `language-index.json` — language lookup.

## Agent behavior

1. Load registry JSON.
2. Filter bundles by task type and target agent family.
3. Check freshness and allowed actions.
4. Verify source-map coverage.
5. Run eval rows or report missing compatibility checks.
6. Return citations and missing checks.
