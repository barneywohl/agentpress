# AgentPress Capability Marketplace

Agents need a compact way to answer:

- What services/capabilities exist?
- What command do I run?
- Is it free, paid, or future-paid?
- What SLA applies?
- What trust evidence backs it?
- What auth/payment boundary applies?

Machine index: `marketplace-index.json`.

```bash
python3 scripts/agentpress.py marketplace --json
python3 scripts/agentpress.py marketplace --capability self-test --json
python3 scripts/agentpress.py marketplace --runtime codex --json
python3 scripts/agentpress.py marketplace --payment-required false --json
```

## Safety

The marketplace is discovery only. It does not execute external writes, sign payments, call paid endpoints, create wallets, or request secrets.
