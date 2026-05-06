# Run this AgentPress material kit

1. Read `llms.txt`.
2. Inspect `material-manifest.json`.
3. Run:

```bash
python3 scripts/agentpress.py provider-adapter-repro-pack --provider anthropic --host claude --json
```

4. Compare the output with `proof-receipt.json`.
5. If using this for outreach, get human approval for the exact target and draft first.

Target: https://platform.claude.com/docs/de/agents-and-tools/tool-use/computer-use-tool
