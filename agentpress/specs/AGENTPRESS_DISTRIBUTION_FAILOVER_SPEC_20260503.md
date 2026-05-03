# AgentPress Distribution Failover Spec — 2026-05-03

## Painpoint

Agents need resilient fetch/install paths. If GitHub Pages is unavailable, an agent should have deterministic fallback URLs and know to verify package hashes before executing anything.

## Features

```bash
python3 scripts/agentpress.py distribution-kit --json
python3 scripts/agentpress.py distribution-mirrors --json
python3 scripts/agentpress.py mirror-status --json
python3 scripts/agentpress.py failover-plan --json
```

## Mirrors

- GitHub Pages primary static site
- Raw GitHub main fallback
- jsDelivr CDN fallback

## Safety

Failover does not relax verification. Agents must verify release/package hashes before executing fetched artifacts.
