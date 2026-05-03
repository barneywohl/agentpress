# AgentPress Registry + Proof Ingest + Exponential Improvement Spec — 2026-05-03

## Why

The next compounding bottleneck after schemas/host harness/TTF-green is turning external adoption signals into an automatic improvement loop without unsafe publishing or fake proof. Agents need registry dry-runs, proof ingestion review, receipt-to-backlog automation, and an exponential improvement radar.

## Commands

```bash
python3 scripts/agentpress.py registry-dry-run --json
python3 scripts/agentpress.py proof-ingest --json --allow-rejected
python3 scripts/agentpress.py proof-ingest-review --json
python3 scripts/agentpress.py receipt-to-backlog --json
python3 scripts/agentpress.py exponential-improvement-radar --json
```

## Outputs

- `agentpress/distribution/registry-dry-run.json`
- `agentpress/external-proofs/external-proof-index.json`
- `agentpress/external-proofs/proof-ingest-review.json`
- `agentpress/planning/receipt-to-backlog.json`
- `agentpress/planning/exponential-improvement-radar.json`

## Acceptance

- Registry dry-run states package-channel readiness without publishing or using credentials.
- Existing proof-ingest continues to index external proof submissions with privacy scoring.
- Proof-ingest-review converts receipts/blockers into scoped trust/backlog inputs.
- Receipt-to-backlog emits non-empty next build items even when the inbox is empty.
- Exponential improvement radar identifies compounding levers for the next cycle.
