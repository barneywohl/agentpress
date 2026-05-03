# AgentPress Agent Operating System Kits Spec — 2026-05-03

## Why

The next painpoint batch from public agent communities is operational: agents need plan workflows, approval gates, reviewer gates, provider compatibility guidance, runtime validation, shareable run artifacts, and a mission keeper cycle. These are the missing primitives that make AgentPress usable across Codex/Claude/Cline/Roo/OpenHands/MCP/LangChain/CrewAI-style environments.

## Commands

```bash
python3 scripts/agentpress.py plan-workflow-kit --json
python3 scripts/agentpress.py approval-gate-kit --json
python3 scripts/agentpress.py reviewer-gate-kit --json
python3 scripts/agentpress.py provider-compatibility-kit --json
python3 scripts/agentpress.py runtime-validation-harness --json
python3 scripts/agentpress.py run-artifact-pack --json
python3 scripts/agentpress.py mission-keeper-kit --json
```

## Outputs

- `agentpress/workflows/plan-workflow/plan-workflow.json`
- `agentpress/approvals/approval-gates.json`
- `agentpress/reviewers/reviewer-gates.json`
- `agentpress/providers/provider-compatibility.json`
- `agentpress/runtime-validation/runtime-validation-harness.json`
- `agentpress/run-artifacts/run-artifact-pack.json`
- `agentpress/mission-keeper/mission-keeper.json`

## Acceptance

- Every kit emits machine-readable JSON and appears in the tools manifest.
- Approval gates fail closed for external write/payment/credential/production actions.
- Reviewer gates include security/product/docs/runtime review templates.
- Runtime harness lists commands agents must pass before claiming support.
- Run artifact pack defines shareable evidence bundle structure.
- Mission keeper encodes the recursive research → backlog → build → verify → deploy → repeat loop.
