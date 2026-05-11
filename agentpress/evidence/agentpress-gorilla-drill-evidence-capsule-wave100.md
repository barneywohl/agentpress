# AgentPress Gorilla drill evidence capsule

Status: `ok`

A fresh agent can now collect tamper-evident local drill receipts step-by-step, verify command hashes, and stop before any public action.

## Evidence slots
- Step 1: `echo 'AgentPress Gorilla manifest acceptance replay (local-only)'` — command_sha256=`0868ffee013b1f5aa18e35a8e7361397de26346e528e27427068820803d3a8d6`
- Step 2: `echo 'Stop before any public action; Jake approval required.'` — command_sha256=`db919aef82ed20efadc37e2ba2302a327578909875d4d83e632d1cfd2c3715d2`
- Step 3: `echo 'inspect step 1: inspect_receipt'` — command_sha256=`cffd49a348161d2dba8510e8961b24cea8fc20aa74ce10d28a92080fbd128201`
- Step 4: `echo 'running step 2: run_first_useful_command'` — command_sha256=`f0324306443c6e6862aeafd4cef4dffe5e559bf4345c50d6e1ca45e685cd9327`
- Step 5: `python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json` — command_sha256=`5dd8a25a041db0a378aab78e024117f526abb5019503e35efc6f8602bf628caa`
- Step 6: `echo 'running step 3: capture_proof'` — command_sha256=`845d9c6072714999f89c1481752d909886e790669921e601a0b36c17a7311cc5`
- Step 7: `python3 scripts/agentpress.py proof-capture --task-id glm-gorilla-bootstrap-conveyor --evidence-dir agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof --artifacts agentpress/gorilla/glm-bootstrap-conveyor-wave87.json --commands 'python3 scripts/agentpress.py gorilla-utility-pack --out agentpress/gorilla/utility-pack --json' --json` — command_sha256=`c0c4328735f5763b85df776a28d5a4126f6862737286266bf4a5ea9f6e381d19`
- Step 8: `echo 'Replay complete; local commands run: 2'` — command_sha256=`8f367f434f2f1319518e6495c10f79cc9b2a4546ee2e91dc210b57887df8cae0`

## Public action gate
No public push/publish/deploy/payment/external-send is allowed without Jake explicit approval.
