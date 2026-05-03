# AgentPress Broken Bundle Fixtures

These fixtures are intentionally invalid. They are platform tests, not example publications.

Run:

```bash
python3 scripts/agentpress.py negative-fixtures --json
```

The command must return `status: ok` only when every fixture fails verification for the expected reason. This proves AgentPress fails closed on malformed or unsafe bundles.
