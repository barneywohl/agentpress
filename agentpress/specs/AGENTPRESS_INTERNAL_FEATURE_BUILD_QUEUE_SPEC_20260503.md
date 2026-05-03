# AgentPress Internal Feature Build Queue Spec — 2026-05-03

## Purpose

The tool/CLI coverage matrix is not just a public report. AgentPress uses it internally to select and build the next features.

## CLIs

```bash
python3 scripts/agentpress.py feature-build-queue --json
python3 scripts/agentpress.py build-queue-pick --json
python3 scripts/agentpress.py build-queue-complete --feature "..." --commit <sha> --evidence <url> --json
```

## Inputs

- `agentpress/tools/tool-coverage.json`
- `agentpress/painpoints/agent-painpoints.json`
- `agentpress/adoption/adoption-status.json`

## Policy

Build priority is:

1. unblocked tool coverage gaps
2. agent painpoints
3. adoption/proof gaps
4. strategic expansions by persona

Blocked items remain visible only with `--include-blocked`.
