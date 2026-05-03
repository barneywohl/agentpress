# AgentPress External Proof Relay + Scoped Trust Spec — 2026-05-03

## Why

GLM/team audits found the top bottleneck: AgentPress has many self-verified surfaces but still lacks real third-party adoption proof. Trust scoring must not let one generic example proof inflate every marketplace service.

## Commands

```bash
python3 scripts/agentpress.py proof-request-pack --runtime codex --json
python3 scripts/agentpress.py proof-receipt-verify tests/fixtures/proof/good-proof-receipt.json --json
python3 scripts/agentpress.py scoped-trust-report --json
```

## Outputs

- `agentpress/proof-outreach/proof-request-pack.json`
- `agentpress/marketplace/scoped-trust-report.json`
- `tests/fixtures/proof/good-proof-receipt.json`
- `tests/fixtures/proof/bad-proof-receipt-secret.json`

## Acceptance

- Proof request pack gives outside agents exact install/doctor/strict-verify/docs-drift/submission commands.
- Proof receipt verifier requires service_id + capability_id + runtime + artifacts + redaction attestation.
- Secret-bearing proof fixture fails verification.
- Scoped trust report gives no global proof credit; every service starts unverified until service-scoped external proof exists.
