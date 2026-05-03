# AgentPress Fixtures

`broken-bundles/` contains intentionally invalid bundles used to prove AgentPress fails closed.

`broken/` is a compatibility alias for auditors and CI specs that expect the shorter path.

Run:

```bash
python3 scripts/agentpress.py verify agentpress/fixtures/broken/missing-required --json; test $? -ne 0
python3 scripts/agentpress.py negative-fixtures --json
```

The `negative-fixtures` command succeeds only when every listed broken bundle fails for the expected reason.
