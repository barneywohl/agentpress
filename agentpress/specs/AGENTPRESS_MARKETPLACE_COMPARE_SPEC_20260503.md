# AgentPress Marketplace Compare Spec — 2026-05-03

## Real feature

AgentPress now lets agents compare marketplace services for a capability and simulate quote/routing choices without spending money, signing wallets, or calling paid endpoints.

## Command

```bash
python3 scripts/agentpress.py marketplace-compare --capability agent_onboard --json
```

## Output

- `agentpress/marketplace/marketplace-compare.example.json`

## Safety

Quote simulation only. No payment signing, no wallet access, no paid endpoint call, no external commerce post.
