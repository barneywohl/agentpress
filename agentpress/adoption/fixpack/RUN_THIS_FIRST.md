# AgentPress Adoption Fix Pack

Turn local adoption evidence into a copy-paste first-contact fix pack for one outside agent, without hidden telemetry or external posting.

## Run this first

```bash
python3 scripts/agentpress.py doctor --json
python3 scripts/agentpress.py first-run-wizard --json
python3 scripts/agentpress.py landing-receipt --agent-id <agent-id> --runtime <runtime> --discovery-channel adoption-fixpack --out /tmp/<agent-id>-landing.json --json
python3 scripts/agentpress.py self-test --agent-id <agent-id> --out /tmp/<agent-id>-self-test.jsonl
python3 scripts/agentpress.py submission-pack --receipt /tmp/<agent-id>-landing.json --out /tmp/<agent-id>-submission --json
```

## Blockers

- P0 `no_third_party_receipts`: Run landing-receipt and submission-pack from one clean external runtime.

## Safety

No hidden telemetry. Do not post externally or publish packages without separate human approval.
