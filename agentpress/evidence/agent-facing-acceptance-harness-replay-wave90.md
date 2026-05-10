# Agent-facing acceptance harness replay (wave90)

- Status: `ok`
- Evidence ID: `wave90-harness-5d12fdb148d1a5be`
- Safe paste command: `npm run rc:agent-facing-acceptance-smoke-replay-receipt-verifier --silent`
- Replay return code: `0`
- Public action gate: `closed_until_jake_explicit_approval`
- Public actions taken: `[]`
- External actions: `[]`

## Painpoint solved
A recipient can replay the handoff/proof packet with one local CLI and get machine-readable pass/fail evidence instead of manually interpreting scattered receipts.

## Expected output checks
- `agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json` exists=True status=ok
- `agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md` exists=True status=n/a
- `agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.json` exists=True status=ok
- `agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.md` exists=True status=n/a

## Blockers
- None
