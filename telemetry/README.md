# Agent Traffic Telemetry Convention

GitHub clone counts prove the repo is being pulled, but they do not identify whether the cloner is a human, crawler, CI job, or AI agent. This folder defines a clean, non-invasive convention for future distribution.

## Use source-tagged links

When posting or submitting the repo to agent directories, forums, dataset catalogs, or RAG indexes, use URLs with explicit campaign parameters:

```text
https://barneywohl.github.io/agentpress/AGENT_ENTRYPOINT.md?src=agent-directory&utm_medium=agent&utm_campaign=korea-agent-benchmark
```

Prefer one stable `src` per channel. Do not use deceptive beacons, hidden pixels, or fingerprinting.

## High-signal agent paths

- `/AGENT_ENTRYPOINT.md` — human-readable agent task brief.
- `/agent-task-card.json` — machine-readable task card.
- `/agents.json` — root agent metadata.
- `/dataset/korea-cheap-screen-deletion-benchmark.jsonl` — eval rows.
- `/rag-pack/ingestion-manifest.json` — RAG ingestion.

## What counts as signal

Strong signal:

- repo clones from new unique cloners after agent-directory submissions
- inbound links/referrers from AI/dev/dataset platforms
- issues/PRs/citations from agent/RAG builders
- forks that preserve the benchmark assets

Weak signal:

- raw page views without referrer
- aggregate clone counts without channel correlation
- social impressions
