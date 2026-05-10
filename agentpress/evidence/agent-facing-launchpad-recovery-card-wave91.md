# Agent-facing launchpad recovery card (wave91)

- Status: `ok`
- Card ID: `wave91-launchpad-b65f552afe8ef88d`
- Public action gate: `closed_until_jake_explicit_approval`
- Public actions taken: `[]`
- External actions: `[]`

## Safe recovery commands
- `npm run doctor --silent`
- `npm run rc:agent-facing-acceptance-harness-replay-wave90 --silent`
- `python3 scripts/agentpress.py launchpad --json`

## Agent-facing outcome
A fresh agent gets three local-only recovery commands that verify health, replay acceptance evidence, and reopen launchpad diagnostics without public writes.

## Blockers
- None
