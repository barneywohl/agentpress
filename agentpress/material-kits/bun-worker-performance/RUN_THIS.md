# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/worker_threads/WorkerPerformance`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-worker-performance --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the worker performance context is compact and citation-ready

Review gate: Pass if the worker performance context is compact, citation-ready, and prevents runtime failures from missing context

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
