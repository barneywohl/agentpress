# AgentPress Patch/PR Helper Spec — 2026-05-03

## Real feature

AgentPress now gives coding agents a safe local contribution lane. It generates a PR/patch artifact, owner checklist, validation commands, changed-file metadata, and a PR body without pushing, opening a PR, publishing packages, or sending external data.

## Command

```bash
python3 scripts/agentpress.py patch-pr-helper --title "Example" --change-summary "Example safe contribution" --changed-file scripts/agentpress.py --json
```

## Output

- `agentpress/contrib/patch-pr-helper.example.json`
- `agentpress/contrib/patch-pr-helper.example.md`

## Safety

This helper is local-only. It blocks external writes by design and requires human review before PR creation/merge.
