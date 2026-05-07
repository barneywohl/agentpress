# Redis: all debug info

GLM-backed AgentPress material kit for `Redis`.

Painpoint: Agents repeatedly fetch and re-parse the same Redis debug info because no compact cached context exists, causing slow responses and wasted cycles.

Target source: https://redis.io/docs/latest/operate/rs/references/rest-api/requests/debuginfo/all

Validation:
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-debuginfo-all --json
```

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
