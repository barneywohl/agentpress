# AgentPress agent-facing acceptance seal verifier quickstart (wave78)

- Status: `ok`
- Generated at: `2026-05-10T16:55:05Z`
- Quickstart: `wave78-quickstart-8b64c590e1b938a5`
- Seal: `wave77-seal-0449f9cc9e223888`
- Certificate: `wave73-certificate-5c0855d73346ea07`
- Source receipt: `wave72-readiness-78dfb73f11e85b4e`
- Lane count: `6/6`
- Fresh-agent commands: `5`
- Public action gate: `closed_until_jake_explicit_approval`
- Public publish/push/deploy/outreach/payment/secret access: `not executed`
- Public actions taken: `[]`
- External actions: `[]`

## Ordered fresh-agent verification commands
1. `npm run rc:agent-facing-acceptance-rehearsal-seal` — Regenerate the wave77 sealed acceptance receipt locally. Expected: status ok and seal_id wave77-seal-0449f9cc9e223888
2. `npm run rc:agent-facing-acceptance-seal-verifier-quickstart` — Verify this wave78 quickstart receipt and package inclusion locally. Expected: status ok, six replay lanes, package files included, public gate closed
3. `python3 -m json.tool agentpress/evidence/agent-facing-acceptance-seal-verifier-quickstart-wave78.json >/tmp/agentpress-wave78-json.tool.out` — Inspect the machine-readable quickstart receipt for a fresh agent handoff. Expected: JSON parses and lists ordered verification commands plus artifact inventory
4. `npm pack --dry-run --json` — Confirm the source distribution contains the verifier script, test, and evidence files. Expected: required_included entries are true and no publish is performed
5. `python3 -m pytest tests/test_agent_facing_acceptance_seal_verifier_quickstart.py -q` — Run the focused regression test suite for wave78. Expected: all wave78 guardrail tests pass

## Artifact inventory
- `agentpress/evidence/agent-facing-acceptance-rehearsal-seal-wave77.json` loaded=True status=ok lanes=6 gate=closed_until_jake_explicit_approval
- `agentpress/evidence/agent-facing-acceptance-recipient-rehearsal-wave76.json` loaded=True status=ok lanes=6 gate=closed_until_jake_explicit_approval
- `agentpress/evidence/agent-facing-acceptance-transfer-checklist-wave75.json` loaded=True status=ok lanes=6 gate=closed_until_jake_explicit_approval
- `agentpress/evidence/agent-facing-acceptance-certificate-replay-drill-wave74.json` loaded=True status=ok lanes=6 gate=closed_until_jake_explicit_approval
- `agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.json` loaded=True status=ok lanes=6 gate=closed_until_jake_explicit_approval
- `agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json` loaded=True status=ok lanes=6 gate=closed_until_jake_explicit_approval
- `agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json` loaded=True status=ok lanes=6 gate=closed_until_jake_explicit_approval
- `agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json` loaded=True status=ok lanes=6 gate=None

## Cross-checks
- `wave77_matches_wave76_certificate_id` ok=True
- `wave77_matches_wave76_source_receipt_id` ok=True
- `wave77_matches_wave76_lane_count` ok=True
- `wave77_matches_wave76_command_count` ok=True
- `wave77_matches_wave76_transfer_step_count` ok=True
- `wave77_matches_wave76_rehearsed_step_count` ok=True
- `wave77_matches_wave76_rehearsed_lane_count` ok=True
- `wave77_matches_wave75_certificate_id` ok=True
- `wave77_matches_wave75_source_receipt_id` ok=True
- `wave77_matches_wave75_lane_count` ok=True
- `wave77_matches_wave75_command_count` ok=True
- `wave77_matches_wave75_transfer_step_count` ok=True

## Package inclusion checks
- `scripts/agent_facing_acceptance_seal_verifier_quickstart.py` exists=True package_files=True
- `tests/test_agent_facing_acceptance_seal_verifier_quickstart.py` exists=True package_files=True
- `agentpress/evidence/agent-facing-acceptance-seal-verifier-quickstart-wave78.json` exists=True package_files=True
- `agentpress/evidence/agent-facing-acceptance-seal-verifier-quickstart-wave78.md` exists=True package_files=True

## Blockers
- None
