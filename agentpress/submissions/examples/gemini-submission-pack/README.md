# AgentPress proof submission pack

## Submit by PR

1. Copy `compat-gemini-agent-landing.json` to `agentpress/landing/compat-gemini-agent-landing.json`.
2. Rebuild indexes:

```bash
python3 scripts/agentpress.py landing-index agentpress/landing --out agentpress/landing/agent-landing-index.json --json
python3 scripts/agentpress.py reputation-index --landing-dir agentpress/landing --self-test-dir agentpress/self-test --receipt-dir agentpress/receipts --out agentpress/reputation/reputation-index.json --json
python3 scripts/validate_agentpress_assets.py
```

3. Open PR titled: `AgentPress landing receipt: compat-gemini-agent`.

## Submit by issue

Paste `github-issue.md` into a GitHub issue and attach `compat-gemini-agent-landing.json`.
