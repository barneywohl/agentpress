# AgentPress Gorilla operator acknowledgement verifier

- Status: `ok`
- Verifier: `wave104-gorilla-operator-acknowledgement-verifier`
- Public push/publish/deploy: `False`; Jake approval required: `True`

## Verifier steps
1. **load-runbook** — Load the wave103 runbook and preserve its local-only safety boundary.
2. **validate-required-fields** — Reject acknowledgements missing required operator fields.
3. **validate-first-command** — Require operator_acknowledged_first_command=true and first_command_exit_code=0.
4. **validate-criteria-coverage** — Require every runbook acceptance criterion in criteria_checked.
5. **validate-local-artifacts** — Require generated artifacts to be relative local paths with no URL, secret marker, or parent traversal.

## Required acknowledgement fields
- `operator_agent_id` (string, required=True)
- `operator_acknowledged_first_command` (boolean, required=True)
- `first_command_exit_code` (integer, required=True)
- `first_command_stdout_tail` (string, required=True)
- `first_command_stderr_tail` (string, required=False)
- `criteria_checked` (array[string], required=True)
- `generated_local_artifacts` (array[string], required=True)
- `stop_reason_if_blocked` (string, required=False)
- `operator_note` (string, required=False)

## Failure-stop rules
- Stop if any required acknowledgement field is missing.
- Stop if the first command was not acknowledged with exit code 0.
- Stop if any acceptance criterion is unchecked.
- Stop if any generated artifact path is absolute, remote, parent-traversing, or secret-labeled.
- Stop before any public push, publish, deploy, payment, external send, URL fetch, or secret request without Jake approval.

## Handoff-ready artifacts
- `agentpress/evidence/agentpress-gorilla-operator-acknowledgement-verifier-wave104.json`
- `agentpress/evidence/agentpress-gorilla-operator-acknowledgement-verifier-wave104.md`
- `agentpress/evidence/agentpress-gorilla-launchpad-acceptance-runbook-wave103.json`

## Blockers
- none
