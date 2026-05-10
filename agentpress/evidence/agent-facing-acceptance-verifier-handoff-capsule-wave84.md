# Agent-facing acceptance verifier handoff capsule (wave84)

- Status: `ok`
- Generated at: `2026-05-10T19:01:45Z`
- Capsule: `wave84-handoff-890b4511b3858705`
- Source certificate: `wave83-verifier-8a1e6b342218c46c`
- Safe paste command: `npm run rc:agent-facing-acceptance-smoke-replay-receipt-verifier --silent`
- Command chain verified: `True`
- Replay return code: `0`
- Expected output count: `4`
- Public action gate: `closed_until_jake_explicit_approval`
- Public actions taken: `[]`
- External actions: `[]`

## Fresh-agent inspection files
- `agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json`
- `agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md`
- `agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json`
- `agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.json`
- `agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json`

## Stop/go criteria

Go if:
- wave83 status is ok and blockers is empty
- command_chain_verified is true
- selected_command_replay_returncode is 0
- expected_output_count is at least 4
- public_action_gate is closed_until_jake_explicit_approval
- public_actions_taken and external_actions are empty
Stop if:
- any blocker is present
- the verifier command exits non-zero
- any recommended command contains publish/push/deploy/outreach/payment/secret text
- any public or external action is required before Jake approval

## Blockers
- None
