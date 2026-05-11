# AgentPress Gorilla receipt acceptance launchpad packet

- Status: `ok`
- Packet: `wave102-gorilla-receipt-acceptance-launchpad-packet`
- Public publish/push/deploy: `False`; Jake approval required: `True`
- First command: `echo 'AgentPress Gorilla manifest acceptance replay (local-only)'`

## Receipt acceptance criteria
- source verifier status is ok
- all Gorilla drill step receipts are accepted
- receipt command hashes match the wave100 capsule
- first command is local-only and does not request secrets
- stop before push/publish/deploy/payment/external-send unless Jake explicitly approves

## Failure-stop rules
- any nonzero command exit
- missing or nonlocal generated artifact path
- command hash mismatch versus capsule
- public action, payment, external send, URL fetch, or secret/token request
- package registry proof missing script/test/evidence/source files

## Local artifacts to attach
- `agentpress/evidence/agentpress-gorilla-receipt-acceptance-launchpad-packet-wave102.json`
- `agentpress/evidence/agentpress-gorilla-receipt-acceptance-launchpad-packet-wave102.md`
- `agentpress/evidence/agentpress-gorilla-evidence-receipt-verifier-wave101.json`
- `agentpress/evidence/agentpress-gorilla-drill-evidence-capsule-wave100.json`
- `agentpress/evidence/agentpress-gorilla-launchpad-first-run-drill-wave99.json`

## Blockers
- none
