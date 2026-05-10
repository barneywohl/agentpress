# Agent-facing acceptance replay drill recipient packet (wave86)

- Status: `ok`
- Generated at: `2026-05-10T19:28:55Z`
- Packet: `wave86-recipient-9dfb55c37058dc81`
- Source wave85 receipt: `wave85-replay-cebe1bbdebc11a53`
- Safe paste command count: `1`
- Safe paste command: `npm run rc:agent-facing-acceptance-smoke-replay-receipt-verifier --silent`
- Replay return code: `0`
- Public action gate: `closed_until_jake_explicit_approval`
- Public actions taken: `[]`
- External actions: `[]`

## Fresh-agent instructions
- Stay local-only in this repository.
- Run exactly the single safe paste command listed in this packet.
- Inspect the generated JSON and Markdown evidence files.
- If any blocker appears, stop and record the blocker locally.
- Do not take any public-write or account-touching action before Jake explicit approval.

## Go criteria
- wave85 status is ok
- blockers is empty
- selected_command_replay_returncode is 0
- command_chain_verified is true
- expected_output_count is at least 4
- no missing criteria
- public_action_gate is closed_until_jake_explicit_approval
- public_actions_taken and external_actions are empty

## Stop criteria
- wave85 status is not ok
- blockers is not empty
- selected_command_replay_returncode is not 0
- command_chain_verified is not true
- expected_output_count is below 4
- missing criteria are present
- public_actions_taken or external_actions are not empty

## Blockers
- None
