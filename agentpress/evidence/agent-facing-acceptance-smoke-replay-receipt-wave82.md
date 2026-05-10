# Agent-facing acceptance smoke replay receipt (wave82)

- Status: `ok`
- Receipt id: `wave82-smoke-replay-0895c3137302`
- Replayed command: `npm run rc:agent-facing-acceptance-launchpad-card`
- Replay return code: `0`
- Public action gate: `closed_until_jake_explicit_approval`
- Public actions taken: none
- External actions: none

## Deterministic success criteria
- wave81, wave80, and wave79 load as ok with empty blockers
- selected command equals wave81 paste_ready_packet.first_command, wave80 first_command_selection.selected, and wave79 recommended_next_command
- selected command replay exits 0 in local inspection-only mode
- all wave81 packet commands remain local_safe, inspection_only, public_action_free, and forbidden-command free
- package dry-run includes the wave82 script, test, JSON receipt, and Markdown receipt
- public_actions_taken and external_actions remain empty

## Deterministic failure criteria
- missing, blocked, non-ok, or public/external contaminated prior evidence
- selected command mismatch across wave81, wave80, or wave79
- selected command or packet command contains publish/push/deploy/outreach/payment/secret text
- selected command replay, local inspections, pytest, or npm pack dry-run fails
- any public_actions_taken or external_actions are recorded

## Blockers
- none

## Expected replay outputs
- `agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json`
- `agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.md`
- `agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json`
- `agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.md`
