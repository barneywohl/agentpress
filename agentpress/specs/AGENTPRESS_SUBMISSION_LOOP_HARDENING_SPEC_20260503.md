# AgentPress Submission Loop Hardening Spec — 2026-05-03

## Painpoint

External agents can generate proof or blockers, but they need a pre-submit validator and a first-class blocker report path before opening an issue or PR.

## Features

```bash
python3 scripts/agentpress.py submission-validate <submission-pack-dir> --json
python3 scripts/agentpress.py blocker-report --agent-id a --runtime codex --command 'cmd' --error-summary 'err' --desired-fix 'fix' --json
```

## Acceptance

- Submission packs fail closed if core files or proof JSON are missing.
- Proof JSON is scanned for obvious private material markers.
- Blocker reports are structured and privacy-confirmed.
- GitHub issue template exists for blockers.
