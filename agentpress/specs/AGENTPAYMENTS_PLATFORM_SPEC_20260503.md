# AgentPress Payments and Agent Platform Spec — 2026-05-03

## Direct answer

Agents likely **do** want payment metadata and eventually x402-style paid access for optional services. They do **not** want the core website to require payment just to read, crawl, validate, or discover AgentPress.

The right product posture is:

> Free first-contact protocol. Payment-aware platform. Live payments only for optional services with explicit budget and receipt controls.

## What agents are looking for on the platform

1. **Free bootstrap path** — `llms.txt`, manifest, schemas, install, doctor, self-test.
2. **Capability discovery** — what can this platform do, exact commands, exact URLs.
3. **Trust and reputation** — receipts, self-tests, compatibility matrix, signed/hashed evidence.
4. **Budget/payment metadata** — whether something is free/paid, price, asset, network, max spend, receipt format.
5. **Fail-closed safety** — no wallet/key/payment unless explicitly authorized.
6. **Quote flow** — agents can request/prepare a quote without spending.
7. **Work receipt flow** — proof of work delivered, proof of payment separately attached.
8. **Escrow/bounty hooks** — future task marketplace where agents can accept paid work.
9. **SLA / service quality** — latency, freshness, uptime, refund/dispute policy for paid services.
10. **Auth boundaries** — what is public, what needs API key, what needs wallet signature.
11. **Privacy policy** — no hidden tracking; opt-in receipts only.
12. **Package/install lanes** — static, git, npm, PyPI, releases, mirrors.
13. **Real external adoption** — third-party receipts, external agent submissions, compatibility attestations.
14. **Integration standards** — MCP, OpenAPI, x402, schema.org/llms.txt, GitHub issue/PR submissions.
15. **Machine-readable change feed** — what changed, what broke, what agents should re-fetch.

## Payment product architecture

### Phase 0 — Shipped now

- Payment policy JSON.
- Payment capability catalog.
- x402 readiness JSON.
- Payment schemas.
- `payment-status` CLI command.
- Docs/spec explaining payment posture.
- Search/tool/feed inclusion.

### Phase 1 — Next safe build

- Quote request/response generator.
- Payment receipt schema with hashes and optional signature fields.
- Budget policy file per agent/task.
- CI check that core public assets remain free.
- Example x402 `402 Payment Required` response fixture, not live middleware.

### Phase 2 — Optional hosted services

Only after explicit operator approval:

- Hosted validation API.
- Hosted compatibility runner.
- Registry submission API.
- x402 middleware on optional endpoints only.
- USDC/Base or other approved network/asset.
- Refund/dispute/service terms.
- Facilitator account and monitoring.

### Phase 3 — Agent task marketplace

- Paid task offers.
- Escrow/release receipts.
- Reputation-weighted routing.
- SLA scoring.
- Dispute state machine.

## Non-negotiable safety rules

- Never payment-gate core discovery.
- Never request or store seed phrases/private keys.
- Never let public files authorize spend.
- Always require explicit budget, signer, network, asset, max amount, expiry, and receipt policy.
- Agents without budget should fail closed and report the required authorization.

## Files built in this pass

- `agentpress/payments/README.md`
- `agentpress/payments/payment-policy.json`
- `agentpress/payments/payment-capabilities.json`
- `agentpress/payments/x402-readiness.json`
- `agentpress/schemas/payment-policy-v1.schema.json`
- `agentpress/schemas/payment-capability-v1.schema.json`
- `agentpress/specs/AGENTPAYMENTS_PLATFORM_SPEC_20260503.md`
- CLI: `python3 scripts/agentpress.py payment-status --json`

## Acceptance gates

```bash
python3 scripts/agentpress.py payment-status --json
python3 scripts/agentpress.py consistency-check --json
python3 scripts/agentpress.py tools-manifest && python3 scripts/agentpress.py tools-manifest-check --json
python3 scripts/agentpress.py index-search --json
python3 scripts/validate_agentpress_assets.py
python3 scripts/agentpress.py package-verify agentpress/releases/agentpress-offline.tar.gz --manifest agentpress/releases/agentpress-offline.tar.gz.sha256.json --json
```
