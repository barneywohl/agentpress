# GOAL: Ship `1.0.0-rc.2` so AgentPress is production-ready

**Date:** 2026-05-13
**Status:** Pre-launch blocker; gates promotion of v1.0 to `latest`
**Mode:** Run continuously, phase-gated by completion of each previous phase

---

## Why this exists

Audit of the live `1.0.0-rc.1` packages on npm + PyPI found that the **new infrastructure (parsers, MCP server, GitHub Action) all work correctly, but the shipped CLI — the legacy 10,709-line Python monolith — does not implement the v1.0 README promises.** Any user who installs and follows the README will fail in under 30 seconds. That kills the launch.

This goal makes the CLI surface match the README, brings the Python CLI to feature parity with the Node CLI, adds production-grade error handling and cross-platform support, and gates promotion to `latest` behind a full smoke-test pass against the *published* artifacts.

---

## Stop condition (production-ready)

The goal is met when **ALL** of the following are true:

1. `npm install -g @agent_press/agentpress` (no `@next`) installs `1.0.0-rc.2` and **every command in `README.md` works on first try** with no further setup
2. `pip install agentpress-static` (no `--pre`) installs `1.0.0rc2` and the same commands work
3. The 30 smoke tests in §6 all pass against the **published** artifacts (not local), on a clean machine, in a fresh directory
4. `agentpress --help` shows only the four v1.0 verbs (no legacy bloat exposed by default)
5. `agentpress` with no args shows the same clean help (no cryptic JSON)
6. `agentpress legacy <cmd>` still works for existing v0.x users with a one-time deprecation banner
7. `agents.txt` produced by `agentpress init` validates cleanly against the v1.0 spec
8. CI in the `agentpress` repo runs the smoke suite on every push and stays green
9. `latest` dist-tag points to `1.0.0-rc.2` on all three npm packages and PyPI has `1.0.0rc2` available without `--pre` flag (when bumped to `1.0.0` final after burn-in)
10. Rollback to `0.2.0` is one command away if anything regresses post-promote

When all 10 hold, AgentPress is production-ready and the launch surfaces in `LAUNCH/` can be triggered.

---

## What's IN scope

- Replace the thin Node shim `bin/agentpress.js` with a real CLI that owns the v1.0 verbs natively
- Add equivalent Python CLI entry point in `agentpress_cli/` that owns the same verbs natively using `agentpress-core`
- Both CLIs share the same surface, same outputs, same exit codes
- Hide legacy commands from default `--help`; expose via `agentpress legacy --help`
- Generate sensible `agents.txt` templates per repo type (Node, Python, Go, Rust, mono, generic)
- Comprehensive error handling: clean messages, useful exit codes, no stack traces leaked to users
- Cross-platform: Mac (arm + intel), Linux, Windows (PowerShell + CMD)
- Tests cover happy paths, error paths, edge cases, all four verbs, both CLIs
- CI matrix runs the smoke suite on Node 18/20/22 × Python 3.10/3.11/3.12/3.13 × Mac/Linux/Windows
- Rollback plan documented and one-command executable

## What's OUT of scope (explicit non-goals)

- Refactoring the 10,709-line `scripts/agentpress.py` monolith (deferred to v1.1)
- Removing legacy commands (they stay behind `agentpress legacy` until v2.0)
- New verbs beyond the four the README promises (init, lint, doctor, receipt)
- Cryptographic signing of receipts (v1.1 work — current receipts are content-addressed via sha256 only)
- Per-agent ACLs in agents.txt (v1.2)
- Hosted SaaS / dashboard / paid tier
- Changes to the agents.txt v1.0 spec
- Changes to `@agent_press/core`, `@agent_press/mcp-server`, or the GitHub Action (they already work)

---

## The fixes (every audit finding mapped to a deliverable)

### Critical 1 — `agentpress receipt` does not exist
**Fix:** Implement in both CLIs.
- Node: `bin/agentpress.js` → `receipt` subcommand
- Python: `agentpress_cli/cli.py` → `receipt` subcommand
- Output schema: `{ "schema_version": "agentpress-receipt.v1", "ts": <iso>, "agents_txt_path": <abs>, "agents_txt_sha256": <hex>, "spec_version": <str>, "project": <str>, "validation": {"ok": bool, "errors": int, "warnings": int}, "agentpress_version": <semver>, "receipt_id": "rcpt_<uuid12>" }`
- Default: writes to `./agentpress/receipts/<receipt_id>.json`
- Flags: `--stdout-only` to skip file write; `--out PATH` to override location; `--json` for JSON output to stdout (default if `--stdout-only`)
- Exit 0 on valid agents.txt, 1 if agents.txt invalid/missing, 2 on internal error

### Critical 2 — `agentpress init` not interactive
**Fix:** Real interactive wizard in both CLIs.
- Detection (silent, before prompts):
  - Git repo (look for `.git/`)
  - GitHub origin (parse `.git/config`)
  - Node project (`package.json`)
  - Python project (`pyproject.toml`, `setup.py`)
  - Go project (`go.mod`)
  - Rust project (`Cargo.toml`)
  - Monorepo (multiple of the above)
  - CI: GitHub Actions (`.github/workflows/`), GitLab (`.gitlab-ci.yml`), CircleCI (`.circleci/config.yml`)
  - Existing `LICENSE`, parse SPDX id if standard
  - Maintainer email: `package.json author`, `pyproject.toml authors`, then `git config user.email`
- Five prompts:
  1. Maintainer email (default from detection)
  2. AI disclosure required for agent-authored PRs? (default Y)
  3. Allow agents to file PRs without per-PR approval? (default Y)
  4. Require human approval for changes to billing/, payments/, auth/, security/ paths? (default Y)
  5. Generate GitHub Action template for CI lint? (default Y if `.github/workflows/` detected)
- Writes:
  - `agents.txt` at repo root (must validate cleanly against the v1.0 spec — verified inline before write)
  - `.github/workflows/agentstxt.yml` (only if GitHub Actions detected and user said yes)
  - `agentpress/receipts/init_<rcptid>.json` proof of the init run
- Prints README badge snippet to stdout after success
- Flags: `--non-interactive` (uses all defaults silently — for CI use), `--out PATH` (override repo root), `--force` (overwrite existing agents.txt with prompt)
- If `agents.txt` already exists and `--force` not set: refuse with clear error pointing at `agentpress doctor`
- Exit 0 on success, 1 on user abort (Ctrl-C), 2 on detection or write failure

### Critical 3 — `agentpress lint` checks wrong files
**Fix:** Lint `agents.txt` only. Both CLIs use the published `@agent_press/core` (Node) and `agentpress-core` (Python) parsers.
- Default path: `./agents.txt`
- Argument: `agentpress lint [path]` where `path` is either a file or a directory containing `agents.txt`
- Output (default human-readable):
  ```
  AgentPress lint: ./agents.txt (spec v1.0)
    ✓ valid
    0 error(s), 0 warning(s)
  ```
- Output (`--json`): full ValidationResult JSON from parser
- Output (`--strict`): warnings escalate to errors
- Exit 0 on valid, 1 on errors, 2 on errors with `--strict`, 3 on file-not-found
- File-not-found error message: `agents.txt not found at <path>. Run \`agentpress init\` to create one.`

### Critical 4 — `agentpress doctor` checks wrong files
**Fix:** Real health check for the v1.0 surface in both CLIs.
- Checks (each passes or fails individually):
  1. Runtime: Node version >= 18 (Node CLI), Python version >= 3.10 (Python CLI)
  2. `@agent_press/core` (Node) or `agentpress-core` (Python) parser is importable
  3. `agents.txt` exists at default location
  4. `agents.txt` parses (no parser errors)
  5. `agents.txt` validates (no validation errors)
  6. `.github/workflows/agentstxt.yml` present (warning if absent and `.github/workflows/` exists)
  7. README contains agents.txt badge (warning if absent)
  8. `agentpress` CLI is on PATH (resolves correctly)
  9. Optional: `python3` available (only for `agentpress legacy` users; not a hard fail)
- Output (default): human-readable checklist with ✓/✗/⚠ and summary line
- Output (`--json`): `{ "checks": [...], "summary": {"passed": n, "warnings": n, "errors": n}, "ok": bool }`
- Exit 0 if no errors, 1 if any errors

### Cosmetic 5 — `agentpress --help` exposes 250+ legacy commands
**Fix:** Clean default help showing only the four v1.0 verbs.
- `agentpress --help` shows: version, four verbs with one-line descriptions, link to docs
- `agentpress legacy --help` shows: legacy subcommand listing (forwarded from Python monolith)
- `agentpress <verb> --help` shows: per-verb help with all flags

### Cosmetic 6 — `agentpress` no args prints cryptic JSON
**Fix:** Show the same clean help as `--help`. Exit 0.

### Production gap A — Python CLI has same broken behavior
**Fix:** New `agentpress_cli/cli.py` implements the same four verbs natively using `agentpress-core` Python parser. Both CLIs:
- Same surface (verb names, flag names, exit codes)
- Same output formats (human and `--json`)
- Same receipt schema
- Same templates for `agents.txt`
- Pass the same smoke test suite

### Production gap B — Cross-platform path handling
**Fix:**
- Node CLI: use `path.join`, `path.resolve`, `path.sep` consistently. No hardcoded `/`. Test on Windows in CI.
- Python CLI: use `pathlib.Path`. No hardcoded `os.sep`. Test on Windows in CI.
- File writes use atomic temp + rename (cross-platform).
- All file paths in receipts are absolute and use forward slashes for consistency (interoperable JSON).

### Production gap C — Edge cases in the parser layer
**Fix:** Add fixtures and tests for:
- UTF-8 BOM at start of file
- CRLF line endings (Windows)
- Trailing whitespace on every line
- Mixed tabs and spaces around `=`
- Empty file
- File with only `[meta]` (missing required sections — should error clearly)
- File with unknown sections (should preserve in `unknown_sections` and warn, not error)
- File with unknown spec_version (should warn, not error)
- Section header case insensitivity (`[Meta]`, `[META]`, `[meta]` all parse to `meta`)
- Comment-only lines (start with `#`)
- Inline comments (text after `#` on a non-section line — currently undefined; spec to v1.0: treat as part of value)

If the parser surface needs changes to handle any of these, those changes ship as `@agent_press/core@1.0.0-rc.2` and `agentpress-core==1.0.0rc2` with the CLI.

### Production gap D — Install-time UX
**Fix:**
- `npm install @agent_press/agentpress` shows a single post-install line: "AgentPress installed. Run `agentpress init` to get started."
- No noisy postinstall scripts that publish, deploy, or contact services (keeps the security claim in the README real)
- Python `pip install agentpress-static` produces an importable CLI that's on PATH after install

### Production gap E — Cross-language test parity
**Fix:** Both Node and Python smoke test suites parse the same canonical fixture (`tests/fixtures/canonical-agents.txt`) and produce byte-identical receipts (modulo timestamp) for the same input. CI gates on this.

### Production gap F — Documentation matches behavior
**Fix:** Update once at the end of the build:
- `README.md` — verify every command shown actually runs and produces the documented output
- `agentpress/QUICKSTART.md` — same
- `agentpress/FULL_REFERENCE.md` — same
- The published spec doc — unchanged (already correct)

---

## Smoke test suite (every test must pass against published artifacts)

These run as `agentpress/tests/test_smoke_v1.py` (Python) and `tests/smoke.test.mjs` (Node). Both are wired into the v1.0 CI workflow and gate promotion to `latest`.

| # | Command | Expected |
|---|---|---|
| 1 | `agentpress` | Exits 0; prints help with exactly the four v1.0 verbs; no legacy command names appear |
| 2 | `agentpress --help` | Same as #1 |
| 3 | `agentpress --version` | Prints `1.0.0-rc.2` (or current rc) |
| 4 | (fresh dir) `agentpress lint` | Exits 3; error message references `agents.txt not found` and suggests `agentpress init` |
| 5 | (fresh dir) `agentpress doctor` | Exits 1; lists missing agents.txt as an error |
| 6 | `agentpress init --non-interactive` | Exits 0; writes `agents.txt`, `.github/workflows/agentstxt.yml` (if applicable), and an init receipt |
| 7 | `cat agents.txt` after #6 | Includes all required sections per the v1.0 spec |
| 8 | `agentpress lint` after #6 | Exits 0; reports 0 errors, 0 warnings |
| 9 | `agentpress lint --json` after #6 | Returns `{"ok": true, ...}` parseable JSON |
| 10 | `agentpress doctor` after #6 | All checks ✓ except possibly README badge (warning) |
| 11 | `agentpress doctor --json` after #6 | Returns valid JSON with `"ok": true` |
| 12 | `agentpress receipt --stdout-only` after #6 | Prints JSON receipt with non-empty `agents_txt_sha256` |
| 13 | (corrupt agents.txt) `agentpress lint` | Exits 1; reports specific errors with line numbers; no stack trace |
| 14 | `agentpress nonexistent` | Exits 1; clean error "Unknown command 'nonexistent'. See `agentpress --help`." |
| 15 | `agentpress legacy --help` | Exits 0; shows legacy command listing (forwarded from Python monolith) |
| 16 | `agentpress legacy doctor` | Exits 0; runs the legacy Python doctor; prints one-time deprecation banner |
| 17 | `npx -y @agent_press/agentpress@next --version` | Exits 0; prints version |
| 18 | (Python CLI) `pip install --pre agentpress-static && agentpress --version` | Exits 0; prints version |
| 19 | Python CLI smoke tests #1–14 | All pass with identical output to Node CLI (modulo platform-specific paths) |
| 20 | (Mac) Run #1–18 | All pass |
| 21 | (Linux) Run #1–18 in Docker | All pass |
| 22 | (Windows) Run #1–18 in CI Windows runner | All pass |
| 23 | (Node 18) Run all | All pass |
| 24 | (Node 20) Run all | All pass |
| 25 | (Node 22) Run all | All pass |
| 26 | (Python 3.10) Run all Python tests | All pass |
| 27 | (Python 3.12) Run all Python tests | All pass |
| 28 | Cross-language: run `agentpress init` with Node CLI, then `agentpress lint` with Python CLI on the same file | Both pass; receipts have same sha256 |
| 29 | `npm pack` for the main CLI | Tarball < 500 KB |
| 30 | `MCP server smoke`: spawn `@agent_press/mcp-server`, send `initialize` request, expect `result` with `tools` listing the four agents_txt_* tools | Passes |

CI runs the full matrix on every push to the `v1.0` branch. The matrix is the gate for promotion.

---

## Build sequence (phases — completion-gated, no times)

Each phase ends with a status report to the user and commits to the `v1.0` branch.

### Phase A — Node CLI v1.0 verbs implemented
- Create `bin/agentpress.js` as a real entry point (replacing the thin shim)
- Create `bin/lib/{init,lint,doctor,receipt,legacy,detect,prompts,template,paths,exit_codes}.js` modules
- Use `@agent_press/core` for parsing (declare as dep in `package.json`)
- Use Node's built-in `readline` for prompts (no third-party prompt deps)
- All four verbs functional locally
- Local invocation: every smoke test #1–#14 passes against `npm pack`-installed artifact
- **Status report:** what's implemented, current pass rate against the suite, anything that didn't fit

### Phase B — Python CLI v1.0 verbs implemented  
- Update `agentpress_cli/cli.py` to own the four verbs natively
- Use `agentpress-core` (the Python parser library) for parsing
- Mirror the Node CLI's surface, outputs, exit codes exactly
- All four verbs functional locally
- Smoke tests #18–#19 (cross-language parity) pass
- **Status report:** parity confirmed; differences (if any) documented

### Phase C — Parser edge cases handled
- Add fixtures under `packages/core/test/fixtures/` and `python-core/tests/fixtures/`
- Add tests for every edge case enumerated in "Production gap C"
- If parser changes needed, ship them as `1.0.0-rc.2` for both core packages
- **Status report:** fixtures added; parser version of each language; whether parsers needed changes

### Phase D — Help, error UX, install hygiene
- Clean `--help` output (no legacy bloat)
- Clean error messages for every exit code (no stack traces)
- Verify `npm install` produces no postinstall side effects (no publish, no deploy, no network calls)
- Verify `pip install` produces no `setup.py` side effects
- **Status report:** UX cleaned; install hygiene verified

### Phase E — CI matrix
- Update `.github/workflows/agentpress-validate.yml` to run the full smoke suite on Mac/Linux/Windows × Node 18/20/22 × Python 3.10/3.11/3.12/3.13
- All cells green
- **Status report:** CI matrix passing; link to CI run

### Phase F — Documentation alignment
- `README.md` — every command verified by running it
- `agentpress/QUICKSTART.md` — same
- `agentpress/FULL_REFERENCE.md` — same
- `CHANGELOG.md` — add `1.0.0-rc.2` entry summarizing the fixes
- Version bumps to `1.0.0-rc.2` (npm) / `1.0.0rc2` (PyPI) in all five package manifests
- **Status report:** docs verified; versions aligned

### Phase G — Publish to registries
- Surface to user: this phase requires npm credentials (use existing valid token in `~/.npmrc`) and PyPI credentials (use `/Volumes/X10/clawd_secrets/pypi_agentpress_token.txt` — confirmed account-wide). If credentials need rotation, surface the exact command for the user.
- Publish in order, each verified before next:
  1. `@agent_press/core@1.0.0-rc.2` to `next` (republish if parser changed; no-op if unchanged but version bumped)
  2. `@agent_press/mcp-server@1.0.0-rc.2` to `next`
  3. `agentpress-core==1.0.0rc2` to PyPI (if changed)
  4. `agentpress-static==1.0.0rc2` to PyPI
  5. `@agent_press/agentpress@1.0.0-rc.2` to `next`
- Verify after each: install in a fresh dir succeeds, package metadata correct
- **Status report:** all five live with URLs; install verifications pass

### Phase H — Smoke tests against published artifacts
- Run the full 30-test smoke suite in a fresh `/tmp/agentpress-rc2-smoke/` directory installing from the public registries (NOT local pack)
- Every test must pass before proceeding
- If anything fails: file the failure, fix, bump to `1.0.0-rc.3` (or patch), republish, re-run
- **Status report:** 30/30 pass; full transcript saved to `LAUNCH/SMOKE_TEST_TRANSCRIPT_<date>.md`

### Phase I — Burn-in period
- Leave `1.0.0-rc.2` on `next` dist-tag for a burn-in window so any external tester can hit issues before we promote to `latest`
- During burn-in: monitor GitHub issues, npm download counts (especially per-version), any community feedback
- Burn-in ends when either: (a) external installs confirmed working, or (b) user explicitly says "promote now"
- No promotion to `latest` happens during burn-in
- **Status report:** burn-in state; download counts; any issues

### Phase J — Promote to `latest` and bump to final `1.0.0`
- Bump versions: `1.0.0-rc.2` → `1.0.0` in all five manifests
- Republish all five at `1.0.0` to `latest` (this is when `@agent_press/agentpress` moves from `0.2.0 latest` to `1.0.0 latest`)
- Run the full smoke suite one more time against the final `1.0.0` artifacts
- Tag the GitHub release as `v1.0.0`
- Publish the GitHub Marketplace listing for the Action (user task — surface command)
- **Status report:** v1.0 live as `latest`; everything green; ready for launch surfaces in `LAUNCH/`

### Phase K — Documentation snapshot
- Snapshot the smoke test transcript, CI matrix results, and final versions into `LAUNCH/V1_0_0_RELEASE_RECORD.md` for posterity and for the public launch transparency thread
- Update `LAUNCH/POST_LAUNCH_PLAYBOOK.md` to note `1.0.0` is now `latest` and adjust the day-1 outreach copy accordingly
- **Status report:** Release record saved; ready for launch.

---

## Rollback plan (one-command for each level)

Each level is independent. Pick whichever level the failure mode requires.

| Severity | Symptom | Rollback command |
|---|---|---|
| Cosmetic | Bad help output, typo, wrong example | Patch in `1.0.0-rc.3` or `1.0.1`; no rollback needed |
| Functional regression in a non-essential verb | `agentpress receipt` crashes on some input | `npm dist-tag add @agent_press/agentpress@1.0.0-rc.1 next` (move users back to rc.1 on next channel) |
| Major regression in core verb | `agentpress init` writes broken `agents.txt` | `npm dist-tag add @agent_press/agentpress@0.2.0 latest` (instant revert to last stable; rc.2 stays on `next` for users who opt in) |
| Catastrophic | Security issue / data loss | `npm deprecate @agent_press/agentpress@1.0.0-rc.2 "<reason>"` + force `latest` to `0.2.0` + GitHub security advisory + public post |

All rollback commands are documented in `LAUNCH/ROLLBACK.md` (created in Phase F).

---

## Acceptance — the goal is "done" when

The 10-point stop condition at the top of this document is met. To restate explicitly:

1. ✅ `npm install -g @agent_press/agentpress` (no `@next`) gets `1.0.0` (or rc.2 during burn-in) and every README command works
2. ✅ `pip install agentpress-static` mirror
3. ✅ All 30 smoke tests pass against the *published* artifacts
4. ✅ `agentpress --help` shows only four verbs
5. ✅ `agentpress` with no args shows the same clean help
6. ✅ `agentpress legacy <cmd>` still works
7. ✅ Generated `agents.txt` validates cleanly
8. ✅ CI matrix green on every push to v1.0
9. ✅ `latest` dist-tag at v1.0 (or rc.2 during burn-in)
10. ✅ Rollback documented and one-command-ready

When all 10 hold, the launch surfaces in `LAUNCH/` are safe to fire.

---

## What this goal does NOT touch

- The `agents.txt` v1.0 specification (locked, working)
- The parser libraries' public API (working; only internal edge-case handling may improve)
- The MCP server's stdio protocol (working)
- The GitHub Action's `validator.js` (working)
- The browser + VS Code extensions (working; pending separate marketplace submissions)
- The landing page (working)
- The 10,709-line legacy Python CLI (left intact behind `agentpress legacy`)
- Domain purchase / Cloudflare DNS / agentpress.dev (user task)
- Public launch posting (HN/PH/X/Bluesky/Reddit) — that's launch day; this goal is the prerequisite
- The 20-repo PR push — same, post-launch

---

## Goal handoff

When `/goal` is invoked with this file as the directive, the agent executes phases A through K in order, runs continuously, posts status reports between phases, and stops only when the 10-point acceptance criteria all hold. Any phase that requires user authentication (npm publish, PyPI upload) surfaces the exact action needed and waits for confirmation before proceeding. The agent does not promote `1.0.0-rc.1` to `latest` and does not skip the smoke-test gate under any circumstance.
