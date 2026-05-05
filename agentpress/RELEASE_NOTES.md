# AgentPress Release Notes

## Unreleased - global agent painpoint gates (2026-05-05)

Status: local source release only. npm/PyPI publish remains blocked unless an rc4 bump is explicit, all gates pass, and auth is safe.

### New features

| Feature | CLI | Status |
|---|---|---|
| Safety preflight umbrella | `python3 scripts/agentpress.py safety-preflight . --json` | Implemented |
| Context budget gate | `python3 scripts/agentpress.py context-budget <bundle> --json` | Implemented |
| MCP config doctor | `python3 scripts/agentpress.py mcp-config-doctor --config <mcp-config.json> --json` | Implemented |

### Safety scope

- No secret reads by default; redaction and tool-manifest scans require explicit public paths.
- `mcp-config-doctor` is static and never mutates MCP config.
- `context-budget` uses file metadata and source-map/freshness presence, not full source ingestion.

---

## 0.2.0-rc.5 — Real agent feature surfaces + advisory review gates (2026-05-05)

- Built tangible AgentPress surfaces for agent communication/proof inboxes, profile/search discovery, marketplace trust scoring, and gorilla utility packs.
- Gorilla packs now include local run → first-contact audit → result receipt finalize/validate flow and corrected LlamaIndex RAG safety artifact path.
- Release checklist now treats independent external proof and RFLO as advisory by default so rc/site/package updates are not blocked; use `--enforce-review-gates` to make them hard stable/latest blockers.
- Added regression coverage for communication receipts, profiles/search, real feature surfaces, P0 command surfaces, and advisory/enforced release gates.

## 0.2.0-rc.4 — Node first-run and integrity hardening (2026-05-05)

Status: **local release candidate metadata**. Do NOT publish npm/PyPI without separate approval.

### New features

| Feature | CLI | Status |
|---|---|---|
| Node fast-path doctor | `agentpress doctor --json` with Python unavailable | Implemented |
| Node llms-init | `agentpress llms-init . --json` | Implemented |
| External proof run | `python3 scripts/agentpress.py external-proof-run --agent-id <id> --runtime codex --json` | Implemented |
| CI integrity gate | manifest integrity, npm pack dry-run, Node fast-path tests | Implemented |

### Release drift policy

- Local metadata: npm `0.2.0-rc.4`, PyPI `0.2.0rc4`.
- Live registry proof defaults: npm/PyPI `0.1.0` until approved publish.
- Package publish commands remain out of scope for this repo change.

---

## 0.2.0-rc.1 — first-user major feature sprint (2026-05-04)

Status: **release candidate** — locally verified, pending CI gate + Jake go/no-go. Do NOT publish to npm/PyPI without explicit directive keyword.

### New features

| Feature | CLI | Schema version |
|---|---|---|
| `first-user-bootstrap` | `python3 scripts/agentpress.py first-user-bootstrap --platform <platform> --json` | `2026-05-04.agentpress-first-user-bootstrap.v1` |
| `proof-capture` (v2 + secret scan) | `python3 scripts/agentpress.py proof-capture --task-id <id> --evidence-dir <dir> --json` | `2026-05-04.agentpress-proof-capture.v2` |
| `sandbox-guard` (v2 + allowlist) | `python3 scripts/agentpress.py sandbox-guard --scope read-only --paths ./src --json` | `2026-05-04.agentpress-sandbox-guard.v2` |
| `adoption-tracker` | `python3 scripts/agentpress.py adoption-tracker --period 7d --json` | `2026-05-04.agentpress-adoption-tracker.v1` |
| `handoff-pack` | `python3 scripts/agentpress.py handoff-pack --from glm --to rflo --task-id <id> --json` | `2026-05-04.agentpress-handoff-pack.v1` |
| `batch-painpoints` | `python3 scripts/agentpress.py batch-painpoints --input issues.json --output /tmp/out --json` | `2026-05-04.agentpress-batch-painpoints.v1` |
| `adoption-fixpack` | `python3 scripts/agentpress.py adoption-fixpack --json` | `2026-05-04.agentpress-adoption-fixpack.v1` |

### Patch details (ruflo_sonnet_1 sprint lane — mission-20260504-053454-927a17)

- **proof-capture v2**: Added `_scan_for_secrets()` that detects common secret patterns (sk-*, Bearer tokens, GH PATs, AWS AKIAs, PEM private keys) in all artifact files before bundling. Schema bumped to v2. `secret_scan_status` field added to result. `--strict` mode returns exit 1 if hits found.
- **sandbox-guard v2**: Wrapper script now enforces `allowed_paths` allowlist in addition to forbidden-marker blocklist. Added `allowlist_enforced` to policy object. Schema bumped to v2.
- **adoption-fixpack**: Added a local-only first-contact fix pack that turns adoption-status/docs/lint evidence into `RUN_THIS_FIRST.md`, `copy-paste-agent-prompt.md`, and copy-paste proof commands.
- **Version bump**: Both `pyproject.toml` (0.2.0rc1) and `package.json` (0.2.0-rc.1) bumped from 0.1.0.

### Integration gate commands (run before deploy)

```bash
python3 -m py_compile scripts/agentpress.py
python3 scripts/agentpress.py lint . --allow-warnings --json
python3 scripts/agentpress.py docs-command-check --json
python3 scripts/agentpress.py schema-validate-all --json
python3 scripts/agentpress.py doctor --json
npm pack --dry-run
```

### Acceptance gates by feature

- `first-user-bootstrap`: status=`ready_for_paste`, no secrets, rollback pointer present ✅
- `proof-capture`: proof-bundle.json + proof-card.md + SHA256s + secret_scan_status ✅
- `sandbox-guard`: JSON manifest + executable wrapper + allowlist enforced + forbidden markers blocked ✅
- `adoption-tracker`: funnel JSON + conversion rates + `local files only` privacy field ✅
- `handoff-pack`: JSON manifest + .md card + required fields (from/to/task_id) validated by argparse ✅
- `batch-painpoints`: per-target painpoint-NNN.json + summary + `approval_required_for_all: true` ✅

### Deploy blockers

- [ ] CI (`AgentPress Validate` workflow) must pass
- [ ] Jake explicit directive keyword before npm publish or PyPI release
- [ ] No external push/DM/post without keyword

### Non-goals for 0.2.0-rc.1

- No automated external posting.
- No telemetry beyond local receipt files.
- No breaking changes to 0.1.0 CLI surface.

---

## 0.1.0 — static agent-native publication toolkit

Status: package/install readiness gate added 2026-05-02.

### Ships

- Installable Python package metadata via `pyproject.toml`.
- Console command: `agentpress` → `agentpress_cli.cli:main`.
- Repo-local fallback command: `python3 scripts/agentpress.py`.
- Core commands: `init`, `validate`, `audit`, `score`, `build`, `build-all`, `index-articles`.
- CI smoke test that builds the wheel, installs it, runs `agentpress --help`, scaffolds a fresh package-smoke publication, audits/scores it, builds static output, and verifies `index.html` exists.

### Install smoke path

```bash
python3 -m pip install --upgrade pip build
python3 -m build
python3 -m pip install dist/*.whl
agentpress --help
agentpress init /tmp/agentpress-package-smoke --title "Package Smoke" --canonical "https://example.com/package-smoke/"
agentpress audit /tmp/agentpress-package-smoke
agentpress score /tmp/agentpress-package-smoke
agentpress build /tmp/agentpress-package-smoke --out /tmp/agentpress-package-smoke-public
test -f /tmp/agentpress-package-smoke-public/index.html
```

### Release gate

Do not tag or publish a package unless the GitHub Actions `AgentPress Validate` workflow passes, including:

- asset validation across examples,
- JSON/XML parsing,
- static build smoke test,
- package build/install smoke test,
- local availability gate,
- cross-agent eval prompt parse gate.

### Non-goals for 0.1.0

- No hosted CMS.
- No external posting/account actions.
- No telemetry beyond ethical aggregate discovery surfaces.
- Public reference only; verify source claims before external use.
