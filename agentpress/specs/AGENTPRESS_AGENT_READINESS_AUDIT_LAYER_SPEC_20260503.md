# AgentPress Agent Readiness Audit Layer Spec — 2026-05-03

## Why

Agents and operators do not just need a content protocol. They need a practical readiness layer that tells them if a repo/tool is installable, auditable, safe to connect, regression-testable, and evidence-producing.

## Commands

```bash
python3 scripts/agentpress.py readiness-audit --json
python3 scripts/agentpress.py readiness-score --json
python3 scripts/agentpress.py readiness-fix-plan --json
python3 scripts/agentpress.py runtime-install-doctor --json
python3 scripts/agentpress.py connector-security-scanner --json
python3 scripts/agentpress.py deterministic-agent-eval-packs --json
python3 scripts/agentpress.py verifiable-run-evidence-bundle --json
python3 scripts/agentpress.py browser-agent-compatibility-harness --json
```

## Acceptance

- Readiness audit gives pass/gap checks and score.
- Fix plan prioritizes runtime, browser, connector security, deterministic eval, evidence bundle work.
- Runtime doctor lists exact checks/remediations for Python/Node/npm/git/docker/browser/gh/CI.
- Connector scanner fails closed on secrets, missing auth, R4 without approval, unknown transports.
- Eval packs cover install/auth/API/browser/proof adoption paths.
- Evidence bundle defines claim-source map, tool logs, hashes, redaction, approvals, reviewers, CI refs.
- Browser harness defines URL/DOM/screenshot/network/console evidence outputs.
