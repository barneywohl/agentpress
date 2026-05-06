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
python3 scripts/agentpress.py marketplace --capability gorilla-utility-pack --json
```

## Gorilla utility install/run/proof flow

The marketplace exposes the gorilla execution queue plus each utility pack as user-facing entries. Every entry carries exact commands:

1. Install/generate locally: `python3 scripts/agentpress.py gorilla-utility-pack --json`
2. Run the selected pack command from `install_run_proof_commands.run`
3. Run `python3 scripts/agentpress.py first-contact audit --no-network --json`
4. Finalize and validate the receipt using the entry's `proof_finalize` and `proof_validate` commands

## Safety

The marketplace is discovery only. It does not execute external writes, sign payments, call paid endpoints, create wallets, or request secrets. Gorilla utility entries are `ready_not_sent`: no mass posting, scraped DMs, fake adoption, or external comments/sends are automated; any external post/send/comment requires explicit human approval.
