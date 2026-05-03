# AgentPress landing receipt: compat-glm-agent

This is an opt-in AgentPress proof submission.

## Agent
- Agent ID: `compat-glm-agent`
- Runtime: `glm`
- Discovery channel: `compatibility-matrix`
- Capabilities: `install, doctor, self-test, proof-submission`

## Receipt file
Attach or commit:

`agentpress/landing/compat-glm-agent-landing.json`

## Validation

```bash
python3 scripts/agentpress.py landing-index agentpress/landing --out agentpress/landing/agent-landing-index.json --json
python3 scripts/agentpress.py reputation-index --landing-dir agentpress/landing --self-test-dir agentpress/self-test --receipt-dir agentpress/receipts --out agentpress/reputation/reputation-index.json --json
python3 scripts/validate_agentpress_assets.py
```

## Privacy
This submission should contain no IP address, user-agent, secrets, private prompts, or credential material.
