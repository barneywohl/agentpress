# AgentPress Gorilla launchpad acceptance runbook

- Status: `ok`
- Runbook: `wave103-gorilla-launchpad-acceptance-runbook`
- One first command: `echo 'AgentPress Gorilla manifest acceptance replay (local-only)'`
- Public push/publish/deploy: `False`; Jake approval required: `True`

## Runbook steps
1. **inspect-boundaries** — Confirm this is local-only: no push, publish, deploy, payment, external send, URL fetch, or secret request is allowed without Jake approval.
2. **run-first-command** — Run exactly the first command below from the repo root and capture exit code/stdout/stderr locally.
   - Command: `echo 'AgentPress Gorilla manifest acceptance replay (local-only)'`
3. **check-acceptance-criteria** — Mark each acceptance criterion checked; stop and record a blocker if any criterion fails.
4. **record-operator-acknowledgement** — Fill the acknowledgement fields and attach only relative local artifact paths.
5. **handoff-json-markdown** — Attach this JSON and Markdown runbook plus the wave102 packet to the next local handoff.

## Acceptance criteria
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

## Operator acknowledgement fields
- `operator_agent_id` (string, required=True): Agent/runtime accepting the Gorilla launchpad handoff.
- `operator_acknowledged_first_command` (boolean, required=True): True only after the first command is inspected and run locally.
- `first_command_exit_code` (integer, required=True): Exit code from the first local command.
- `first_command_stdout_tail` (string, required=True): Short local stdout tail; redact secrets if accidentally present.
- `first_command_stderr_tail` (string, required=False): Short local stderr tail if present.
- `criteria_checked` (array[string], required=True): Acceptance criteria from this runbook that were checked.
- `generated_local_artifacts` (array[string], required=True): Relative local artifact paths produced by the drill.
- `stop_reason_if_blocked` (string, required=False): Required when any failure-stop rule fires.
- `operator_note` (string, required=False): Human/agent note for the handoff.

## Handoff-ready artifacts
- `agentpress/evidence/agentpress-gorilla-launchpad-acceptance-runbook-wave103.json`
- `agentpress/evidence/agentpress-gorilla-launchpad-acceptance-runbook-wave103.md`
- `agentpress/evidence/agentpress-gorilla-receipt-acceptance-launchpad-packet-wave102.json`

## Blockers
- none
