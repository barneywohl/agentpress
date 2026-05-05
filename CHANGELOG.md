# Changelog

## 0.2.0-rc.3 — 2026-05-05

Post-rc2 hardening and first-user evaluation release candidate.

### Added
- Supply-chain risk controls doc and CI gate for zero runtime npm dependencies, tarball budget, forbidden file checks, manifest integrity, and script-disabled smoke install.
- Safe Karpathy-style first-user eval harness with synthetic repo scenarios and temp-dir cleanup guardrails.
- First-user eval tests and package inclusion for the harness.
- Node-native first-run fast path for `doctor --json` when Python is unavailable, plus `llms-init` generation for arbitrary repo roots.
- CI coverage for manifest integrity, npm pack smoke, Node fast-path behavior, shell metachar argv safety, and sensitive-root refusal.

### Changed
- Registry proof defaults remain on live `0.1.0` packages until a separate approved npm/PyPI publish, while local package metadata stays at rc3.

### Validation
- `python3 -m pytest tests/test_eval_first_user_harness.py -q`
- `python3 -m pytest tests/test_first_user_p0_paths.py tests/test_llms_init_node_fast_path.py tests/test_node_shim_shell_metachar.py tests/test_lint_doctor_secret_guard.py -q`
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
