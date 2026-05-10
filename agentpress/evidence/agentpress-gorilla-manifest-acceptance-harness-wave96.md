# AgentPress Gorilla manifest acceptance harness (wave96)

- Status: `ok`
- Harness ID: `wave96-gorilla-manifest-acceptance-7245fbf9e8bd`
- Source manifest: `agentpress/gorilla/glm-bootstrap-conveyor-wave87.json`
- Public actions taken: `[]`
- External actions: `[]`
- Payment actions taken: `[]`

## Painpoint solved

Turns the Gorilla bootstrap conveyor manifest into a single recipient-facing local acceptance harness with exact commands, safety checks, and expected proof artifacts.

## Acceptance steps
- 1. `inspect_receipt` — `(inspect only)` — `inspection-ready`
- 2. `run_first_useful_command` — `python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json` — `command-ready`
- 3. `capture_proof` — `python3 scripts/agentpress.py proof-capture --task-id glm-gorilla-bootstrap-conveyor --evidence-dir agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof --artifacts agentpress/gorilla/glm-bootstrap-conveyor-wave87.json --commands 'python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json' --json` — `command-ready`

## Safety gate

Jake explicit approval required; no public action performed.

## Blockers
- None
