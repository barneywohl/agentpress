# Example safe AgentPress contribution

## Summary
Demonstrates local-only PR contribution artifact with owner checklist and validation commands.

## Safety
- No external write performed by AgentPress.
- Human must review before opening/merging PR.
- Do not include secrets, tokens, private prompts, IP addresses, or user-agent strings.

## Suggested branch
`agentpress/example-safe-agentpress-contribution`

## Validation commands
- `python3 scripts/agentpress.py tools-manifest-check --json`
- `python3 scripts/agentpress.py consistency-check --json`
- `python3 scripts/agentpress.py negative-fixtures --json`
- `python3 scripts/validate_agentpress_assets.py`

## Changed files
- `agentpress/tools/agentpress-tools.json`
- `scripts/agentpress.py`
