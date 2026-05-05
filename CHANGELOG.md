# Changelog

## 0.2.0-rc.3 — 2026-05-05

Post-rc2 hardening and first-user evaluation release candidate.

### Added
- Supply-chain risk controls doc and CI gate for zero runtime npm dependencies, tarball budget, forbidden file checks, manifest integrity, and script-disabled smoke install.
- Safe Karpathy-style first-user eval harness with synthetic repo scenarios and temp-dir cleanup guardrails.
- First-user eval tests and package inclusion for the harness.

### Validation
- `python3 -m pytest tests/test_eval_first_user_harness.py -q`
- `npm run validate`
- `python3 -m py_compile scripts/eval_first_user_harness.py`
- `python3 scripts/eval_first_user_harness.py --json`
- GitHub Actions: CI, Validate, Supply Chain Gate, Pages deploy.

## 0.2.0-rc.2 — 2026-05-05

Safe pre-publish cleanup for the next AgentPress release candidate. No npm or PyPI publish performed in this commit.

### Added
- `SECURITY.md` with supported versions, private disclosure path, no-secrets guidance, scope, and SLA.
- Compatibility matrix rows with status, proof command, limits, and explicit MCP static-vs-live boundary.

### Changed
- npm tarball whitelist tightened for a smaller install surface while keeping CLI, schemas, MCP static catalog, compatibility docs, and core docs.
- README and npm shim now state that the npm package requires Python >=3.10.
- MCP copy now says static discovery/catalog only; live `agentpress mcp-serve` remains roadmap.
- Local Python metadata aligned to `0.2.0rc2`; PyPI publish remains separate and unperformed.

### Validation target
- `python3 -m json.tool package.json`
- `python3 scripts/check_agentpress_positioning.py`
- `python3 scripts/validate_agentpress_assets.py`
- `npm pack --dry-run`


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
