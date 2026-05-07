# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/worker_threads/LockInfo/clientId`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-lockinfo-clientid --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the Bun LockInfo clientId property is correctly accessed with proper error handling, returning a verified value within the correct range

Review gate: Pass if the material kit contains the exact property name, exact data type, and exact return type from the Bun documentation; fail if any of these are missing or contain SOURCE FACT REQUIRED placeholders

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
