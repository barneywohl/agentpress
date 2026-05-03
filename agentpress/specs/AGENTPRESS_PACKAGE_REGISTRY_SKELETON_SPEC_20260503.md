# AgentPress Package Registry Skeleton Spec — 2026-05-03

## Painpoint

Agents want `pipx`, `uvx`, and `npx` install paths. Live publishing is blocked until package/account ownership is approved.

## Feature

```bash
python3 scripts/agentpress.py package-registry-skeleton --json
python3 scripts/agentpress.py package-registry-dry-run --json
```

Creates safe PyPI/npm skeletons with version `0.0.0`, private/no-publish posture, and dry-run validation.
