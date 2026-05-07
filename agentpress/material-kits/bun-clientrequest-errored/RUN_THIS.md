# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http/ClientRequest/errored`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-clientrequest-errored --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and confirm the kit passes validation with no errors

Review gate: Pass if the material-manifest.json exists at agentpress/material-kits/bun-clientrequest-errored/ and contains correct fields for the Bun errored property

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
