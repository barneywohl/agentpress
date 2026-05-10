# AgentPress recipient sealed transcript launchpad replay card (wave95)

- Status: `ok`
- Card ID: `wave95-recipient-launchpad-replay-card-6915bc497752`
- Source handoff ID: `wave92-handoff-739ca4be26f7a23b`
- Public actions taken: `[]`
- External actions: `[]`

## Recipient action

Read this card, inspect the sealed local commands, then run only the listed local checks in a private workspace if assigned by Jake/operator.

## One-card replay steps
- 1. `python3 scripts/agentpress.py launchpad --json` => `local-ready`
- 2. `npm run rc:agent-facing-launchpad-recovery-card --silent` => `local-ready`
- 3. `npm run rc:agent-facing-acceptance-harness-replay-wave90 --silent` => `local-ready`

## Operator next command

`npm run rc:agentpress-recipient-sealed-transcript-launchpad-replay-card --silent`

## Gate

Jake explicit approval required; no public action performed.

## Blockers
- None
