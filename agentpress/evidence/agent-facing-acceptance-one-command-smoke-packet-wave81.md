# Agent-facing acceptance one-command smoke packet (wave81)

- Status: `ok`
- Packet id: `wave81-smoke-packet-f3aac786c74c`
- First command: `npm run rc:agent-facing-acceptance-launchpad-card`
- Public action gate: `closed_until_jake_explicit_approval`
- Public actions taken: none
- External actions: none

## Paste-ready packet
1. Run: `npm run rc:agent-facing-acceptance-launchpad-card`
2. Verify generated evidence outputs:
   - `agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.json`
   - `agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.md`
3. Stop if any blocker appears; do not perform public actions without Jake's explicit approval.

## Blockers
- none

## Packet commands
- `npm run rc:agent-facing-acceptance-launchpad-card` — local_safe=True, inspection_only=True, public_action_free=True
- `python3 -m json.tool agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.json` — local_safe=True, inspection_only=True, public_action_free=True
- `python3 -m py_compile scripts/agent_facing_acceptance_one_command_smoke_packet.py` — local_safe=True, inspection_only=True, public_action_free=True
- `python3 -m pytest tests/test_agent_facing_acceptance_one_command_smoke_packet.py -q` — local_safe=True, inspection_only=True, public_action_free=True
- `npm pack --dry-run --json` — local_safe=True, inspection_only=True, public_action_free=True
