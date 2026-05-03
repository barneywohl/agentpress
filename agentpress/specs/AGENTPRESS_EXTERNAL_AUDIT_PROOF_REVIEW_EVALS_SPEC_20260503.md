# AgentPress External Audit + Proof Review + Task Quality Evals Spec — 2026-05-03

## Why

The current hardest bottleneck is not local surface coverage; it is external trust. Outside agents need a clean first-contact audit, proof review, deeper task-quality evals, first-class public schema indexing, and a queue that cannot falsely empty while adoption proof remains incomplete.

## Commands

```bash
python3 scripts/agentpress.py external-audit-run --runtime codex --agent-id external-agent --json
python3 scripts/agentpress.py external-proof-review tests/fixtures/proof/good-proof-receipt.json --json
python3 scripts/agentpress.py task-quality-eval --json
python3 scripts/agentpress.py public-schema-bundle --json
python3 scripts/agentpress.py feature-build-queue --include-adoption-gaps --include-public-radar --json
```

## Outputs

- `agentpress/external-audits/first-contact/external-first-contact-audit.json`
- `agentpress/external-proofs/proof-review.example.json`
- `agentpress/evals/task-quality-evals.json`
- `agentpress/schemas/public/public-schema-bundle.json`
- `agentpress/planning/feature-build-queue.json`

## Acceptance

- External audit run gives clean install/doctor/strict verify/docs/self-test/landing/submission commands.
- Proof review accepts clean service-scoped proof and rejects secret-bearing proof.
- Task-quality evals test real usability, unsafe proof rejection, native adapter discovery, scoped trust, and clean install.
- Public schema bundle indexes key public JSON artifact schema versions.
- Feature queue remains non-empty when adoption gaps are explicitly included.
