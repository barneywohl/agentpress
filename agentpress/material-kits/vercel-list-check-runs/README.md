# Vercel: list check runs for a deployment

GLM-backed AgentPress material kit for `Vercel`.

Painpoint: Agents cannot programmatically list deployment check runs, causing silent deployment failures and inability to surface CI/CD status to users

Target source: https://vercel.com/docs/rest-api/sdk/checks-v2/list-check-runs-for-a-deployment

Validation:
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-list-check-runs --json
```

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
