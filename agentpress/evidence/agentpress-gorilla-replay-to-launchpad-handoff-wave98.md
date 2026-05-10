# AgentPress Gorilla replay to launchpad handoff (wave98)

- Status: `ok`
- Card ID: `wave98-gorilla-launchpad-handoff-3b05dda0f4f4`
- Source receipt ID: `wave97-gorilla-replay-receipt-24f6ec686f74`
- Public actions taken: `[]`
- External actions: `[]`
- Payment actions taken: `[]`

## Recipient value

Turns the Gorilla replay receipt into a single launchpad handoff card with safe first-run commands, local artifact checks, and acceptance evidence instructions.

## First-run launchpad steps
- 1. `echo 'AgentPress Gorilla manifest acceptance replay (local-only)'` — safe_local_only=True — Paste into a private checkout only after reading the safety gate.
- 2. `echo 'Stop before any public action; Jake approval required.'` — safe_local_only=True — Paste into a private checkout only after reading the safety gate.
- 3. `echo 'inspect step 1: inspect_receipt'` — safe_local_only=True — Paste into a private checkout only after reading the safety gate.
- 4. `echo 'running step 2: run_first_useful_command'` — safe_local_only=True — Paste into a private checkout only after reading the safety gate.
- 5. `python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json` — safe_local_only=True — Paste into a private checkout only after reading the safety gate.
- 6. `echo 'running step 3: capture_proof'` — safe_local_only=True — Paste into a private checkout only after reading the safety gate.
- 7. `python3 scripts/agentpress.py proof-capture --task-id glm-gorilla-bootstrap-conveyor --evidence-dir agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof --artifacts agentpress/gorilla/glm-bootstrap-conveyor-wave87.json --commands 'python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json' --json` — safe_local_only=True — Paste into a private checkout only after reading the safety gate.
- 8. `echo 'Replay complete; local commands run: 2'` — safe_local_only=True — Paste into a private checkout only after reading the safety gate.

## Local artifact checks
- `agentpress/gorilla/utility-pack`
- `agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof`

## Acceptance harness

`npm run rc:agentpress-gorilla-replay-to-launchpad-handoff --silent`

## Safety gate

Jake explicit approval required; no public action performed.

## Blockers
- None
