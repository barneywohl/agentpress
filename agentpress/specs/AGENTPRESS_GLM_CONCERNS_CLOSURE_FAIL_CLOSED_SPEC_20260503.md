# AgentPress GLM Concerns Closure + Fail-Closed Gates Spec — 2026-05-03

## Why

GLM marked the previous cycle `DONE_WITH_CONCERNS`: several gates could still return green on empty/adversarial inputs. This batch makes the trust, schema, native adapter, CI, approval/reviewer, proof relay, and action-ledger wiring fail-closed.

## Commands

```bash
python3 scripts/agentpress.py native-adapter-check --json
python3 scripts/agentpress.py schema-validate-all --json
python3 scripts/agentpress.py trust-tier-evaluate --json
python3 scripts/agentpress.py approval-gate-eval tests/fixtures/gates/approval-good.json --json
python3 scripts/agentpress.py reviewer-gate-eval tests/fixtures/gates/reviewer-good.json --json
python3 scripts/agentpress.py action-ledger-adapter-wiring --json
python3 scripts/agentpress.py external-proof-relay-status --json
python3 scripts/agentpress.py glm-concerns-closure --json
```

## Acceptance

- Bad trust fixtures fail: global proof credit and T0 without receipt refs.
- Native adapter gate checks all 7 targets and fails on zero/missing configs.
- Schema validate all crawls public AgentPress JSON/JSONL surfaces, not a small allowlist.
- CI runs native adapter, public schema crawler, fail-closed trust, and executable approval/reviewer gates.
- Approval/reviewer gates have pass and fail fixtures.
- Proof relay/status and action-ledger adapter wiring are machine-readable public surfaces.
