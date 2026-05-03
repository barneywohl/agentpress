# AgentPress Package Registry Plan Spec — 2026-05-03

## Why

Agents want `pipx`, `uvx`, and `npx` install paths. The repo currently has offline tarball/install scripts, but live registries require explicit package/account ownership approval.

## CLI

```bash
python3 scripts/agentpress.py package-registry-plan --json
```

## Scope

- Check release tarball, manifest, install script, and CLI entry.
- Recommend package names and install targets.
- Block live PyPI/npm publishing until approval.
