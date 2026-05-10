# AgentPress agent-facing acceptance harness replay matrix (wave70)

- Status: `ok`
- Generated at: `2026-05-10T13:54:29Z`
- Public publish/push/deploy/outreach/payment/secret access: `not executed`
- Public actions taken: `[]`
- External actions: `[]`

## Lanes

### GLM/gorilla bootstrap conveyor (`glm_gorilla_bootstrap_conveyor`)
- Passed: `True`
- Required sources: `final_acceptance_snapshot, route_run_receipt_collector`
- Replay steps:
  1. Load final acceptance snapshot and route-run receipt collector evidence.
  2. Confirm agent-facing next step exists and is local-only.
  3. Rehearse bootstrap handoff as data only; do not execute public command fragments.

### Launchpad (`launchpad`)
- Passed: `True`
- Required sources: `launch_signal_simulator, final_acceptance_snapshot`
- Replay steps:
  1. Load simulated launch signals and final acceptance checklist.
  2. Confirm launch readiness remains simulated/local until Jake approval.
  3. Replay operator capture checklist as non-sending local review steps.

### Comms hub (`comms_hub`)
- Passed: `True`
- Required sources: `route_run_receipt_collector, public_action_guardrail_audit`
- Replay steps:
  1. Load route-run receipt and guardrail audit.
  2. Confirm any send/outreach/push category remains gated.
  3. Produce only local copy/paste rehearsal data, with no outbound message.

### Marketplace (`marketplace`)
- Passed: `True`
- Required sources: `route_run_receipt_collector, final_acceptance_snapshot`
- Replay steps:
  1. Load route claim/receipt path and package inclusion snapshot.
  2. Confirm package/evidence handoff can be inspected by an agent.
  3. Rehearse marketplace adoption route locally without publish/latest promotion.

### Safety guardrails (`safety_guardrails`)
- Passed: `True`
- Required sources: `public_action_guardrail_audit, post_approval_cutover_rehearsal`
- Replay steps:
  1. Load public action audit and post-approval rehearsal evidence.
  2. Confirm public_publish_push gate is closed in rehearsal outputs.
  3. Scan replay steps for forbidden public command fragments and keep execution false.

### Acceptance harness (`acceptance_harness`)
- Passed: `True`
- Required sources: `final_acceptance_snapshot, post_approval_cutover_rehearsal`
- Replay steps:
  1. Load final acceptance and wave69 rehearsal evidence.
  2. Confirm status ok/blockers [] across required sources.
  3. Emit this matrix JSON/Markdown as the next agent-facing acceptance harness artifact.

## Blockers
- None

## Verification commands
- `npm run rc:agent-facing-acceptance-harness-replay-matrix --silent`
- `python3 -m py_compile scripts/agent_facing_acceptance_harness_replay_matrix.py`
- `pytest -q tests/test_agent_facing_acceptance_harness_replay_matrix.py`
- `python3 -m json.tool agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json`
- `npm pack --dry-run --json`
