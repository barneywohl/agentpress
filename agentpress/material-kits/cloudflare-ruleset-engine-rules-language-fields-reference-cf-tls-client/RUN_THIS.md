# Run this AgentPress material kit

1. Read `llms.txt`.
2. Inspect `material-manifest.json`.
3. Run:

```bash
python3 scripts/agentpress.py context-budget . --json --strict
```

4. Compare the output with `proof-receipt.json`.
5. If using this for outreach, get human approval for the exact target and draft first.

Target: https://developers.cloudflare.com/ruleset-engine/rules-language/fields/reference/cf.tls_client_extensions_sha1_le/
