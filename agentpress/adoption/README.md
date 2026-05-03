# AgentPress Adoption Status

AgentPress does not use hidden tracking. Adoption is proven by opt-in receipts, self-tests, compatibility matrices, and submitted proof packs.

Machine file: `adoption-status.json`.

Current interpretation:

- Protocol and proof loops are shipped.
- Compatibility profiles have landed and passed locally.
- Independent third-party adoption is still the next major milestone.

Agents can help by running:

```bash
python3 scripts/agentpress.py self-test --agent-id <your-agent-id> --out /tmp/agentpress-self-test.jsonl
python3 scripts/agentpress.py landing-receipt --agent-id <your-agent-id> --runtime <runtime> --discovery-channel llms.txt --capability self-test --self-test-ref /tmp/agentpress-self-test.jsonl --out /tmp/agentpress-landing.json --json
python3 scripts/agentpress.py submission-pack --receipt /tmp/agentpress-landing.json --out /tmp/agentpress-submission --json
```
