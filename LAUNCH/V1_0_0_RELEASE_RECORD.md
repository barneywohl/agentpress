# AgentPress v1.0.0 release record

**Date:** 2026-05-13
**Tag:** [`v1.0.0`](https://github.com/barneywohl/agentpress/releases/tag/v1.0.0)
**Branch:** `v1.0` (ready for merge to `main`)
**Result:** ✅ shipped to npm + PyPI `latest`; existing 0.2.x users now upgrade to 1.0.0 by default.

## What's live

### npm (https://www.npmjs.com)

| Package | Version | dist-tags |
|---|---|---|
| `@agent_press/agentpress` | **1.0.0** | `latest: 1.0.0`, `next: 1.0.0-rc.2`, `rc: 0.2.0-rc.8` |
| `@agent_press/core` | **1.0.0** | `latest: 1.0.0`, `next: 1.0.0-rc.2` |
| `@agent_press/mcp-server` | **1.0.0** | `latest: 1.0.0`, `next: 1.0.0-rc.2` |

### PyPI (https://pypi.org)

| Package | Version |
|---|---|
| `agentpress-static` | **1.0.0** |
| `agentpress-core` | **1.0.0** |

### One-line install

```bash
# Node
npm install -g @agent_press/agentpress
agentpress init

# Python
pip install agentpress-static
agentpress init
```

### GitHub

- Repo: https://github.com/barneywohl/agentpress
- Release tag: https://github.com/barneywohl/agentpress/releases/tag/v1.0.0
- Source branch: `v1.0` (merge to `main` next)

## Headline numbers vs the original 0.2.0

| Metric | 0.2.0 | 1.0.0 | Δ |
|---|---|---|---|
| npm tarball compressed | 2.18 MB | 313.8 KB | **86% smaller** |
| npm tarball unpacked | 32.4 MB | 1.6 MB | **95% smaller** |
| Files in npm package | 31,684 | 183 | **99.4% fewer** |
| CLI verbs (real, working) | 0 (legacy v0.x only) | 4 v1.0 + legacy fallback | net +4 |
| Reference parser libs published | 0 | 2 (TS + Python) | +2 |
| MCP server | 0 | 1 | +1 |
| Extensions (VS Code + browser) | 0 | 2 | +2 |
| GitHub Action | 0 | 1 | +1 |
| End-to-end tests | 0 | 110+ | +110+ |
| Lines deleted from v0.x repo | — | **3,399,404** | — |

## Verification at ship time

The final smoke run against the **published 1.0.0** artifacts (no `@next`, no `--pre`) passed:

- `npm install -g @agent_press/agentpress` → 1.0.0
- `agentpress --version` → `1.0.0`
- Top help shows only 4 verbs (init, lint, doctor, receipt) + legacy fallback; no v0.x bloat
- `agentpress init --non-interactive` → writes valid `agents.txt`, exit 0
- `agentpress lint` → 0 errors, 0 warnings, exit 0
- `agentpress doctor` → System healthy
- Cross-language sha256 parity (Node + Python) on a freshly generated `agents.txt`:
  - `e01b199ed66259cf9e149b9eb21a1ae3f1718a6a1d24e3f7f658b59683edb278`
  - byte-identical from both CLIs

## Phase log

| Phase | Outcome |
|---|---|
| A — Node CLI v1.0 verbs | ✅ 16 e2e tests pass; `bin/agentpress.js` + 10 lib modules |
| B — Python CLI parity | ✅ 15 e2e tests pass; `agentpress_cli/cli.py` + 10 lib modules; cross-lang sha256 identical |
| C — Parser edge cases | ✅ 30 tests pass; one BOM bug fixed in Python parser |
| D — Install hygiene | ✅ 5 tests pass; no install-time side effects in any package |
| E — CI matrix | ✅ Mac/Linux/Windows × Node 18/20/22 × Python 3.10/3.11/3.12/3.13 wired in `.github/workflows/agentpress-validate.yml` |
| F — Documentation alignment | ✅ README/QUICKSTART/FULL_REFERENCE/CHANGELOG verified by running every command |
| G — Publish rc.2 to next/PyPI | ✅ all 5 packages live on `next` / PyPI prerelease |
| H — Smoke vs published rc.2 | ✅ 30/30 pass (LAUNCH/SMOKE_TEST_TRANSCRIPT_2026-05-13.md) |
| I — Burn-in | ✅ closed by maintainer ("as long as u tested it … then do it") |
| J — Promote to latest + 1.0.0 final | ✅ all 5 packages republished at 1.0.0; `latest` moved on all three npm packages; PyPI versions available without `--pre`; final smoke green |
| K — Release record snapshot | ✅ this document |

## What still needs your hands

1. **Revoke the npm token** that was pasted in chat history (security hygiene): https://www.npmjs.com/settings/barneywohl/tokens
2. **Publish a GitHub Release** for `v1.0.0` to surface the changelog publicly: https://github.com/barneywohl/agentpress/releases/new?tag=v1.0.0
   - Title: `v1.0.0 — agents.txt for any repo`
   - Body: copy from `CHANGELOG.md` `1.0.0-rc.2` entry
   - Check "Set as latest release"
   - **Also** check "Publish this Action to the GitHub Marketplace" so `barneywohl/agentpress/actions/setup-action@v1` resolves cleanly. Pick category "Utilities" → "Code review".
3. **Buy `agentpress.dev`** at your registrar of choice, point at the existing Cloudflare Pages project (`agentpress.pages.dev`).
4. **Submit VS Code extension** (`extensions/vscode/`) to the Marketplace via `vsce publish` (needs Azure DevOps publisher PAT).
5. **Submit browser extension** (`extensions/browser/`) to Chrome Web Store + Firefox AMO (needs developer accounts + real icon set).
6. **Public launch**: open `LAUNCH/LAUNCH_DAY_RUNBOOK.md` — every post / email / PR is pre-written in `LAUNCH/`.
7. **File the 20 PRs**: targets in `LAUNCH/TARGET_REPOS.md`, body in `LAUNCH/PR_TEMPLATE.md`. Track in `LAUNCH/PR_TRACKER.md`.

Each of these is documented with the exact command/click in `LAUNCH/HUMAN_ACTION_REQUIRED.md`.

## Merge plan

The `v1.0` branch has 25+ commits ahead of `main`. Once you've verified the public surfaces look right, merge:

```bash
git checkout main && git merge --ff-only v1.0 && git push origin main
```

Or open a PR for review: https://github.com/barneywohl/agentpress/compare/main...v1.0

## Rollback (if anything regresses post-launch)

The 4-level rollback ladder from `LAUNCH/V1_RC2_GOAL.md` stays in effect:

| Severity | Command |
|---|---|
| Cosmetic | Ship `1.0.1` |
| Functional regression in non-essential verb | `npm dist-tag add @agent_press/agentpress@1.0.0-rc.1 next` |
| Major regression | `npm dist-tag add @agent_press/agentpress@0.2.0 latest` (instant revert) |
| Security/data | `npm deprecate @agent_press/agentpress@1.0.0 "<reason>"` + force latest to 0.2.0 + advisory |

## Acknowledgments

This release shipped autonomously via Claude Code in `/goal` mode, gated at every phase by completion criteria from `LAUNCH/V1_RC2_GOAL.md`. Maintainer (barneywohl) approved the burn-in close with "as long as u tested it and ensure it is complete and works and ready to ship then do it" — the test gate (30/30 smoke pass + cross-language sha256 parity) was the operative quality bar.

Goal complete.
