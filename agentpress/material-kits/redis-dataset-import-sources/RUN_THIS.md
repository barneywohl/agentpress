# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/dataset_import_sources`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-dataset-import-sources --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit redis-dataset-import-sources --validation-strict and verify the receipt shows: (1) exact API endpoints extracted, (2) exact status codes extracted, (3) exact JSON schemas extracted, (4) no invented content

Review gate: Pass if the material kit contains the exact Redis dataset import source API endpoints, exact HTTP status codes, and exact JSON schemas from the source document, with no invented content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
