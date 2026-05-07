# Bun: onmessageerror

GLM-backed AgentPress material kit for `Bun`.

Painpoint: Agents crash or silently swallow errors when worker threads fail, because they lack the exact onmessageerror handler signature and error object shape, causing unhandled rejections that terminate the process.

Target source: https://bun.com/reference/node/worker_threads/MessagePort/onmessageerror

Validation:
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-onmessageerror --json
```

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
