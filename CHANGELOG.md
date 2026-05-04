# Changelog

## 0.2.0-rc.1 — 2026-05-04

Release-candidate packaging/distribution pass for AgentPress.

### Added
- Stronger npm discovery positioning for AI agents, `llms.txt`, MCP, Claude, GPT, LangChain, CrewAI, schema validation, and agent contracts.
- README badges, clearer 60-second quickstart framing, and a `Why agents find it` section.
- MIT `LICENSE` file.
- npm `files` whitelist to keep package contents intentional.
- npm `publishConfig` for public scoped package publishing with provenance.
- Negative fixture regression coverage for fail-closed verification.

### Changed
- Package description and keywords optimized for registry/search surfaces.
- Node engine raised to `>=18.0.0`.
- Python wrapper version aligned to `0.2.0rc1`.

### Validation
- `python3 scripts/agentpress.py doctor --json` — OK.
- `python3 scripts/agentpress.py lint . --allow-warnings --json` — OK, 0 findings.
- `python3 scripts/agentpress.py schema-validate-all --json` — OK, 524 checked / 0 failed.
- `python3 -m pytest -q tests` — 114 passed.
- `npm pack --dry-run` — OK, no `__pycache__`/`.pyc` entries.

### Release gate
- Do not run `npm publish` / PyPI publish until release account, 2FA, provenance, and package-name strategy are confirmed.
