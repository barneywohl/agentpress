# AgentPress External Proof + Host Batch + Connector Failure Cycle Spec — 2026-05-03

## Why

The next cycle after edge-case closure targets the new P0 backlog: acquire real external proof, batch ingest native host transcripts, and standardize connector failures into backlog items.

## Commands

```bash
python3 scripts/agentpress.py external-proof-campaign-runner --json
python3 scripts/agentpress.py host-transcript-batch-ingest tests/fixtures/conformance --json
python3 scripts/agentpress.py connector-failure-taxonomy --json
python3 scripts/agentpress.py cycle-gap-radar --json
```

## Acceptance

- External proof campaign runner defines opt-in targets and safe outreach template.
- Host transcript batch ingest reads a directory and emits conformance/blocker summary.
- Connector failure taxonomy maps failures to priorities/remediation.
- Cycle gap radar lists the next honest gaps after this cycle.
