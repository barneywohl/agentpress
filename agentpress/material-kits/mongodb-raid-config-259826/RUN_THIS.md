# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://www.mongodb.com/community/forums/t/what-type-of-raid-storage-configuration-is-recommended-for-achieving-optimal-performance-with-a-mongodb-deployment/259826`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/mongodb-raid-config-259826 --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify returned JSON has no errors and material-manifest.json exists at agentpress/material-kits/mongodb-raid-config-259826/material-manifest.json

Review gate: Material-manifest.json exists at correct path with valid JSON containing SOURCE FACT REQUIRED placeholders for RAID level, disk throughput, and replica config

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
