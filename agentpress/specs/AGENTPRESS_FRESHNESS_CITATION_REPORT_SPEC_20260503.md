# AgentPress Freshness + Citation Report Spec — 2026-05-03

## Real feature

AgentPress now ships a RAG/crawler evidence report that scans public files for freshness, citation, source, and canonical URL coverage.

## Command

```bash
python3 scripts/agentpress.py freshness-citation-report --json
```

## Output

- `agentpress/evidence/freshness-citation-report.json`

## Acceptance

- Counts machine JSON and documentation files.
- Detects citation/source/freshness signals.
- Detects canonical URL coverage for machine JSON.
- Lists unknown machine files for future cleanup.
- Included in tools manifest, search, release package, attestation, and live Pages deployment.
