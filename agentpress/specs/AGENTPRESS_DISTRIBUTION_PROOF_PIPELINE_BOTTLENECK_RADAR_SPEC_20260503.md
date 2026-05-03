# AgentPress Distribution + Proof Pipeline + Bottleneck Radar Spec — 2026-05-03

## Why

Once the prior bottlenecks have shipped local solution layers, the next failure mode is losing track of the real-world blockers: registry publication, external proof collection, native host conformance, and the next bottlenecks after those are solved.

## Commands

```bash
python3 scripts/agentpress.py distribution-submission-pack --json
python3 scripts/agentpress.py external-proof-pipeline --json
python3 scripts/agentpress.py blocker-solution-matrix --json
python3 scripts/agentpress.py next-bottleneck-radar --json
```

## Outputs

- `agentpress/distribution/submission-pack/distribution-submission-pack.json`
- `agentpress/external-proofs/proof-pipeline.json`
- `agentpress/planning/blocker-solution-matrix.json`
- `agentpress/planning/next-bottleneck-radar.json`

## Acceptance

- Distribution pack enumerates live/ready/submission-ready/blocked package channels.
- Proof pipeline shows end-to-end stages from target discovery to scoped trust and lesson publishing.
- Blocker matrix maps every known bottleneck to a shipped solution layer and remaining blocker.
- Next radar identifies the next constraints after current bottlenecks are covered.
