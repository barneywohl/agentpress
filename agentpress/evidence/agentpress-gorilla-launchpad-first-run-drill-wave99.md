# AgentPress Gorilla launchpad first-run drill

Status: `ok`

## Steps
- Step 1: `echo 'AgentPress Gorilla manifest acceptance replay (local-only)'` — safe_local_only=True
- Step 2: `echo 'Stop before any public action; Jake approval required.'` — safe_local_only=True
- Step 3: `echo 'inspect step 1: inspect_receipt'` — safe_local_only=True
- Step 4: `echo 'running step 2: run_first_useful_command'` — safe_local_only=True
- Step 5: `python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json` — safe_local_only=True
- Step 6: `echo 'running step 3: capture_proof'` — safe_local_only=True
- Step 7: `python3 scripts/agentpress.py proof-capture --task-id glm-gorilla-bootstrap-conveyor --evidence-dir agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof --artifacts agentpress/gorilla/glm-bootstrap-conveyor-wave87.json --commands 'python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json' --json` — safe_local_only=True
- Step 8: `echo 'Replay complete; local commands run: 2'` — safe_local_only=True

## Public action gate
No public push/publish/deploy/payment/external-send is allowed without Jake explicit approval.
