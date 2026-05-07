# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/async_hooks/asyncWrapProviders/HTTPCLIENTREQUEST`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-httpclientrequest --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-httpclientrequest --field method_signature --field required_params --field return_shape to verify that the proof receipt contains the extracted facts.

Review gate: Pass if the proof receipt confirms that the exact method signature, required parameters, and expected return shape were extracted from the source document.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
