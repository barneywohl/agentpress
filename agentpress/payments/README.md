# AgentPress Payments / x402 Readiness

AgentPress should expose payment metadata because autonomous agents increasingly need to answer:

- Is this resource free or paid?
- If paid, what protocol is accepted?
- What is the unit price, max budget, asset, network, expiry, and receipt schema?
- Can I safely fail closed instead of spending?

**Decision:** AgentPress is payment-aware, not payment-gated.

Core first-contact assets remain free. Public AgentPress files do **not** authorize payment, wallet access, paid API calls, account actions, or production money movement.

## Machine files

- `payment-policy.json` — exact safety/authorization boundary.
- `payment-capabilities.json` — free/current/future commercial capability catalog.
- `x402-readiness.json` — why x402 matters and why it is not live by default.

## Recommended agent behavior

```bash
python3 scripts/agentpress.py payment-status --json
```

If `payment_required` is encountered and no explicit budget/approval exists, return:

```json
{"status":"blocked", "reason":"payment_requires_separate_authorization", "needed":"budget + signer + asset/network + receipt policy"}
```

## x402 position

x402 is a good candidate for future optional hosted validation, registry, compatibility running, paid data/API access, or agent-task bounties. It should **not** block discovery of `llms.txt`, schemas, manifests, or core public docs.
