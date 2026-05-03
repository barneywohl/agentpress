# AgentPress Docs Command Check Spec — 2026-05-03

## Real feature

AgentPress now lints documented `python3 scripts/agentpress.py ...` commands so agents do not copy stale commands or flags from docs/specs.

## Command

```bash
python3 scripts/agentpress.py docs-command-check --json
```

## Output

- `agentpress/evidence/docs-command-check.json`

## Acceptance

- Extracts documented AgentPress CLI commands from README, llms.txt, launch docs, adapter docs, and specs.
- Verifies command names against the parser, including aliases.
- Detects obvious stale flags when parser flags are known.
- Emits machine-readable failures/warnings for CI or reviewer gates.
