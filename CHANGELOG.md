# Changelog

## 1.0.0-rc.2 — 2026-05-13

The "make the README real" release candidate. v1.0.0-rc.1 published the
spec, parsers, GitHub Action, extensions, MCP server, registry, and a
clean npm package — but shipped the legacy 10,709-line Python CLI
unchanged, so the four README-promised verbs (init/lint/doctor/receipt)
either didn't exist or did the wrong thing. rc.2 fixes that.

### Added — Node CLI
- `bin/agentpress.js` real entry point with clean top help (no v0.x bloat)
- `bin/lib/init.js` interactive wizard (5 prompts + auto-detect; --non-interactive flag)
- `bin/lib/lint.js` validates agents.txt via `@agent_press/core`; --json, --strict
- `bin/lib/doctor.js` 9-point repo health check; --json
- `bin/lib/receipt.js` content-addressed receipt (sha256 of agents.txt bytes)
- `bin/lib/legacy.js` forwards to scripts/agentpress.py with one-time banner
- `bin/lib/{exit_codes,paths,detect,prompts,template}.js` shared modules
- `tests/cli.test.mjs` 16 e2e tests using node:test

### Added — Python CLI
- `agentpress_cli/cli.py` real entry point (replacing the 8-line shim)
- `agentpress_cli/_{exit_codes,paths,detect,prompts,template,init,lint,doctor,receipt,legacy,version}.py`
  mirror the Node modules exactly
- Uses `agentpress-core` (Python parser) — declared as runtime dep in pyproject.toml
- `tests/test_cli_python.py` 15 e2e tests using pytest
- Cross-language verified: Node + Python produce identical sha256 for same input

### Added — parser edge cases
- `packages/core/test/edge-cases.test.mjs` (15 tests)
- `python-core/tests/test_edge_cases.py` (15 tests)
- Covers: UTF-8 BOM, CRLF, trailing whitespace, mixed tabs/spaces around =,
  empty file, only [meta], unknown sections, unknown spec_version,
  section header case, comment-only lines, inline #, large lists,
  comma-list whitespace, SPEC_VERSION constant

### Fixed — parser
- `agentpress-core` Python: strip UTF-8 BOM (U+FEFF) at file start
  (Python `str.strip()` doesn't remove it; JS `.trim()` does). One-line fix.

### Added — CI
- Full matrix: Mac/Linux/Windows × Node 18/20/22 × Python 3.10–3.13
- Cross-language receipt-parity job (Node and Python sha256 must match)
- npm tarball size budget hard fail at > 500 KB
- MCP server boot smoke test
- Install hygiene tests (no postinstall side effects)

### Changed — docs
- README.md verified: every command works on a fresh install
- agentpress/QUICKSTART.md rewritten for v1.0 (was full of v0.x `llms-init` references)
- agentpress/FULL_REFERENCE.md rewritten as a v1.0 reference (was 650 lines of v0.x)

### Versions bumped
- @agent_press/agentpress  1.0.0-rc.1 → 1.0.0-rc.2
- @agent_press/core        1.0.0-rc.1 → 1.0.0-rc.2 (parser BOM fix)
- @agent_press/mcp-server  1.0.0-rc.1 → 1.0.0-rc.2 (dep on core)
- agentpress-static        1.0.0rc1   → 1.0.0rc2
- agentpress-core          1.0.0rc1   → 1.0.0rc2

### Test counts
- 16 Node CLI + 15 Python CLI + 37 TS parser + 37 Python parser + 5 install hygiene = **110 tests**, all green.

### Release gate
- rc.2 publishes to `next` dist-tag; existing 0.2.0 users on `latest` unaffected.
- Promotion to `latest` (and bump to 1.0.0 final) follows after Phase H/I in V1_RC2_GOAL.md:
  full smoke suite vs published artifacts + burn-in.

## 1.0.0-rc.1 — 2026-05-13

The "real launch" release candidate. Strip + sharpen + ship.

### Added
- **`agents.txt` v1.0** as the headline file format. Drop-in standard for telling autonomous AI agents what they're allowed to do on your repo. Lineage: `robots.txt` → `sitemap.xml` → `llms.txt` → `agents.txt`.
- Eat-our-own-food: `agents.txt` at the root of this repo declaring AgentPress's own contract.
- Package size cut **from 32.4 MB unpacked (31,684 files) to under 2 MB (≈170 files)** — a ~16× size reduction and ~95% file-count reduction.

### Removed
- `agentpress/material-kits/` — 7,136 generated documentation kits / 31,404 files. Agents fetch docs on demand; static doc bundles are bloat.
- `agentpress/evidence/` — internal wave-receipt artifacts that should never have shipped to npm consumers.
- 33 internal "wave" / "fanout" / "gorilla" / "marketplace" scripts from `scripts/` that were dev choreography, not user-facing CLI.
- ~120 mostly-empty scaffolding subdirectories under `agentpress/` (gorilla, mesh, payments, queue, runtime, providers, etc.) — all aspirational, none used.
- 18 internal LARP planning docs (`AGENT_*_SPEC.md`, `GLOBAL_*.md`, `NEXT_100X_*.md`, `OUTSIDE_*.md`, `REMAINING_*.md`, `SHIP_QUEUE.md`, etc.).
- `disclaimer.md` (internal).

### Changed
- `package.json` `scripts` block trimmed from 36 entries (mostly `rc:wave-*`) to 6 user-facing verbs: `doctor`, `init`, `lint`, `validate`, `receipt`, `test`.
- `package.json` `files` whitelist rewritten to ship only the agent-facing surface; everything else excluded.
- README rewritten as a sharp 70-line landing doc: pitch → install → CLI → safety contract → links. The lineage analogy (`robots.txt → llms.txt → agents.txt`) is the new headline.
- Description updated to: "agents.txt for any repo. Tell autonomous AI agents what they're allowed to do, in 60 seconds."
- Keywords tuned for 2026 agent ecosystem (claude-code, cursor, devin, mcp).
- `pyproject.toml` version aligned to `1.0.0rc1`; removed `material-kits` from package-data.

### Backwards compatibility
- v0.2.x CLI verbs (`doctor`, `lint`, `validate`, `quickstart`) all still work — no breaking changes for existing users.
- npm dist-tags: v1.0.0-rc.1 published as `next`; `latest` stays on 0.2.0 until v1.0.0 final ships.
- `agentpress migrate` (coming v1.0.0) will offer a one-command upgrade path for repos generated by v0.2.x.

### Validation
- `npm pack` — confirms <2 MB tarball, ~170 files
- `python3 scripts/agentpress.py doctor --json` — OK
- Existing test suite still passes against the trimmed surface

### Release gate
- v1.0.0-rc.1 does NOT publish. Surfaced to maintainer for human approval (npm 2FA + PyPI token).
- Next: ship `@agent_press/core` parser library, `agentpress/setup-action@v1` GitHub Action, README badge, curated registry, VS Code extension, browser extension, and `@agent_press/mcp-server` — then v1.0.0 final + public launch (HN, PH, X, Bluesky, Reddit).

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
