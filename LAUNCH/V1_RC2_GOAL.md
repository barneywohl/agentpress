# GOAL: Ship `1.0.0-rc.2` so the CLI matches the README

**Date:** 2026-05-13
**Status:** Pre-launch blocker
**Stop condition:** `1.0.0-rc.2` is live on npm + PyPI under `next`, smoke-tests pass against the published artifacts, and we can confidently promote to `latest`.

---

## Why this exists

The audit of `1.0.0-rc.1` (already published to `next`) found that **the README promises 4 CLI verbs that don't actually work**:

| Verb | README says | Actually does |
|---|---|---|
| `agentpress init` | Interactive wizard, 5 questions, drops `agents.txt` | argparse error: requires `out` + `--title` |
| `agentpress lint .` | Validates `agents.txt` | Reports MISSING `llms.txt` |
| `agentpress doctor` | Health check on the v1.0 surface | Reports MISSING `llms.txt` |
| `agentpress receipt` | Cryptographic proof receipt | argparse error: invalid choice `'receipt'` |

The new packages (parser, MCP server, GitHub Action) work correctly. The legacy Python CLI was shipped as-is and doesn't speak the v1.0 surface. **Anyone who tries the README will fail in under 30 seconds.** That kills the launch.

This goal fixes the gap with a thin new Node CLI. ~4 hours of work; ships as `1.0.0-rc.2`. Then we promote to `latest` with confidence.

---

## What's NOT in scope

- Refactoring the 10,709-line `scripts/agentpress.py` monolith (deferred to v1.1; too risky for a same-week patch release)
- New features beyond the 4 verbs the README already promises
- Removing the legacy commands (they stay accessible via `agentpress legacy <cmd>` for v0.x users; deprecated in v1.1)
- Changing the spec, parsers, MCP server, or any other published surface

Tight scope = fast ship.

---

## The build

### 1. New file: `bin/agentpress.js` — replaces the existing thin shim

A single Node script (~250 LOC) that owns the v1.0 verbs natively:

```
agentpress                        # prints help
agentpress init [path]            # interactive wizard → writes agents.txt + .github workflow + README badge snippet
agentpress lint [path]            # validates agents.txt; --json for CI; exit 0/1
agentpress doctor [path]          # full health check; --json for CI
agentpress receipt [path]         # generates proof receipt with sha256 + spec_version + ts
agentpress legacy <subcmd> ...    # forwards to scripts/agentpress.py for v0.x commands
agentpress --version              # prints v1.0.0-rc.2
agentpress --help                 # prints clean help
```

**Implementation details:**
- Uses `@agent_press/core` for parsing (no duplication)
- Pure Node — no Python required for any v1 verb (Python only used for `legacy`)
- Snippet-based templates for `agents.txt` (sensible defaults pre-filled per repo type detection)
- Detects: GitHub repo (looks for `.git/config` origin), Node project (`package.json`), Python project (`pyproject.toml`/`setup.py`), Go (`go.mod`), Rust (`Cargo.toml`), monorepo (multiple of the above)
- Detects CI: GitHub Actions (`.github/workflows/`), GitLab (`.gitlab-ci.yml`), CircleCI (`.circleci/config.yml`)
- Interactive prompts via Node's built-in `readline` (no third-party prompt lib — keeps zero-dep promise)

### 2. `agentpress init` — the interactive wizard the README promises

Five prompts, defaults inferred from detection:

```
$ agentpress init
✓ Detected: GitHub repo at github.com/owner/repo
✓ Detected: Node project (package.json)
✓ Detected: GitHub Actions

? Maintainer email [from package.json author]: jane@example.com
? AI disclosure required for agent PRs? (Y/n): Y
? Allow agents to file PRs without approval? (Y/n): Y
? Require human approval for changes to billing/, payments/, auth/? (Y/n): Y
? Add GitHub Action for CI lint? (Y/n): Y

✓ Wrote agents.txt (38 lines)
✓ Wrote .github/workflows/agentstxt.yml
✓ Snippet for README badge:

[![agents.txt](https://img.shields.io/badge/agents.txt-v1.0-2563eb?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/barneywohl/agentpress)

Next: review the file, commit, push.
```

If `--non-interactive` flag passed, uses all defaults silently. Useful in CI / scripts.

### 3. `agentpress lint` — validates agents.txt against v1.0 spec

Uses `@agent_press/core.validate()`. Two output modes:

```
$ agentpress lint
AgentPress lint: ./agents.txt (spec v1.0)
  ✓ valid
  0 error(s), 0 warning(s)

$ agentpress lint --json
{ "ok": true, "issues": [], "spec_version": "1.0", "project": "my-project" }
```

Exit code 0 if valid (no errors), 1 if errors, 2 if errors + `--strict` flag.

### 4. `agentpress doctor` — comprehensive health check

```
$ agentpress doctor
AgentPress doctor (v1.0.0-rc.2)
  ✓ Node v22.22.0 (>= 18 required)
  ✓ Python 3.14.3 detected (optional, for legacy commands)
  ✓ agents.txt exists at ./agents.txt
  ✓ agents.txt parses (spec v1.0)
  ✓ agents.txt validates (0 errors, 0 warnings)
  ⚠ .github/workflows/agentstxt.yml not found (consider running `agentpress init`)
  ✓ README badge present
  
Summary: 5 OK, 1 warning, 0 errors. System healthy.
```

`--json` for structured output.

### 5. `agentpress receipt` — cryptographic proof of validation

Generates a JSON receipt provable later:

```
$ agentpress receipt --json
{
  "schema_version": "agentpress-receipt.v1",
  "ts": "2026-05-13T06:00:00Z",
  "agents_txt_path": "./agents.txt",
  "agents_txt_sha256": "a1b2c3...",
  "spec_version": "1.0",
  "project": "my-project",
  "validation": { "ok": true, "errors": 0, "warnings": 0 },
  "agentpress_version": "1.0.0-rc.2",
  "receipt_id": "rcpt_<uuid12>"
}
```

Saves to `agentpress/receipts/<receipt_id>.json` if not `--stdout-only`. v1.1 will add ed25519 signing; v1.0 receipts are unsigned but content-addressable via the sha256.

### 6. `agentpress legacy <cmd>` — escape hatch for v0.x users

```
$ agentpress legacy quickstart
[runs scripts/agentpress.py quickstart with all original args/behavior]
```

Prints a deprecation banner once per session: "Legacy commands forwarded to v0.x CLI; will be removed in v2.0."

### 7. Updates to existing files

- `package.json`:
  - Bump version to `1.0.0-rc.2`
  - Update `scripts` block to use the new verbs (`agentpress init`, `agentpress lint .`, `agentpress doctor`, `agentpress receipt`)
  - Add `@agent_press/core` to dependencies (was previously not declared since the CLI was Python-only)
- `pyproject.toml`: bump to `1.0.0rc2`
- `python-core/pyproject.toml`: bump to `1.0.0rc2`
- `packages/core/package.json`: bump to `1.0.0-rc.2` (republish so the CLI's depends-on resolves to a fresh version; alternatively pin to `^1.0.0-rc.1`)
- `packages/mcp-server/package.json`: bump to `1.0.0-rc.2`
- `CHANGELOG.md`: add `1.0.0-rc.2` entry summarizing this fix
- `README.md`: no changes needed — the README is the spec the new CLI must meet

---

## Smoke tests (must all pass before publishing rc.2)

Save as `LAUNCH/SMOKE_TESTS.md` (created when this goal completes). Run after `npm install -g @agent_press/agentpress@next` from a fresh `/tmp/agentpress-rc2-smoke/`:

| # | Command | Expected |
|---|---|---|
| 1 | `agentpress` | Prints clean help with 4 verbs (init, lint, doctor, receipt). No reference to gorilla, marketplace, china-*, etc. |
| 2 | `agentpress --version` | `1.0.0-rc.2` |
| 3 | `agentpress init --non-interactive` | Writes `agents.txt`, `.github/workflows/agentstxt.yml`. Exit 0. |
| 4 | `agentpress lint` | After step 3, reports valid. Exit 0. |
| 5 | `agentpress lint --json` | Returns `{"ok": true, ...}`. Exit 0. |
| 6 | `cat agents.txt` | Parses against [docs/AGENTSTXT_SPEC.md](../docs/AGENTSTXT_SPEC.md) by inspection. |
| 7 | `agentpress doctor` | All checks ✓. Exit 0. |
| 8 | `agentpress receipt --stdout-only` | Returns valid JSON receipt with sha256 matching `agents.txt`. |
| 9 | (in invalid repo) `agentpress lint` | Errors clearly: "agents.txt not found at ./agents.txt. Run `agentpress init` to create one." Exit 1. |
| 10 | `agentpress legacy doctor` | Forwards to legacy Python CLI; deprecation warning shown. |
| 11 | `agentpress nonexistent` | Clean error: "Unknown command 'nonexistent'. See `agentpress --help`." Exit 1. |

If all 11 pass on a fresh install, rc.2 is ready to promote to `latest`.

---

## Build sequence

1. **Write `bin/agentpress.js`** — the new Node CLI (~250 LOC).
2. **Write `bin/lib/init.js`** — repo + CI detection, template generation, interactive prompts.
3. **Write `bin/lib/lint.js`** — wraps `@agent_press/core.validate()`, formats output.
4. **Write `bin/lib/doctor.js`** — full health check with structured output.
5. **Write `bin/lib/receipt.js`** — generates content-addressed receipt.
6. **Write `bin/lib/legacy.js`** — spawns `python3 scripts/agentpress.py` with passthrough args.
7. **Update `package.json`** — version bump + scripts + dep on `@agent_press/core`.
8. **Update `pyproject.toml` + `python-core/pyproject.toml`** — version bumps.
9. **Update `CHANGELOG.md`** — `1.0.0-rc.2` entry.
10. **Run smoke tests locally** — all 11 must pass against a `npm pack` install.
11. **Commit + push to `v1.0` branch.**
12. **Publish to npm:**
    - `cd packages/core && npm version 1.0.0-rc.2 && npm publish --access public --tag next` (republish for version alignment)
    - `cd packages/mcp-server && npm version 1.0.0-rc.2 && npm publish --access public --tag next`
    - `cd /Volumes/X10/clawd/agentpress-v1-source && npm publish --tag next`
13. **Publish to PyPI** (only Python CLI changed; parser unchanged so optional):
    - `cd /Volumes/X10/clawd/agentpress-v1-source && python3 -m build && twine upload dist/agentpress_static-1.0.0rc2*`
    - (skip `agentpress-core` since the parser didn't change)
14. **Re-run smoke tests** against the *published* artifacts (not local).
15. **If all green: promote `next` to `latest` for all 3 npm packages:**
    - `npm dist-tag add @agent_press/core@1.0.0-rc.2 latest`  (already latest since it's the newest)
    - `npm dist-tag add @agent_press/mcp-server@1.0.0-rc.2 latest`
    - `npm dist-tag add @agent_press/agentpress@1.0.0-rc.2 latest`  ← **the load-bearing one** (replaces 0.2.0)
16. **Verify final state**: `npm view @agent_press/agentpress dist-tags` shows `latest: 1.0.0-rc.2`.

---

## Rollback plan

If anything goes wrong post-promote:
- `npm dist-tag add @agent_press/agentpress@0.2.0 latest` — instantly reverts `latest` to the old stable
- v1.0.0-rc.2 stays available under `next` for users who explicitly opt in
- Open a GitHub issue with the failure mode, ship rc.3 with the fix

---

## What this goal does NOT touch

- The agents.txt v1.0 spec (locked)
- The parser libraries (working correctly)
- The MCP server (working correctly)
- The GitHub Action (working correctly)
- The browser + VS Code extensions (working correctly; pending publish)
- The landing page (working)
- The 10,709-line legacy Python CLI (left intact behind `agentpress legacy`)

This goal is surgical: make the 4 promised CLI verbs real, then promote.

---

## Estimated time

~4 hours of focused work, including the smoke-test pass. Then promotion to `latest` is one minute.

---

## Acceptance

The goal is met when:
1. All 11 smoke tests pass against `npm install -g @agent_press/agentpress@next` from a fresh dir.
2. `1.0.0-rc.2` is live on npm + PyPI under `next`.
3. `latest` dist-tag has been promoted to `1.0.0-rc.2` for `@agent_press/agentpress` (and the other two new packages already have it as their only version).
4. `npm install -g @agent_press/agentpress` (no `@next`) installs `1.0.0-rc.2` and the README's commands all work.
5. Existing `0.2.0` users are unaffected (npm caches; they only upgrade if they explicitly run `npm update`).

After all five conditions hold, the launch surfaces in `LAUNCH/` (HN, X, Bluesky, etc.) can be triggered with confidence — every command in every post will work for someone copying it.
