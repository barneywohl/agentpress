# Smoke test transcript — v1.0.0-rc.2

**Date:** 2026-05-13
**Goal phase:** H (smoke suite vs published artifacts)
**Result:** ✅ **30/30 tests pass** on macOS arm64 against the **public** registries.

The full Mac/Linux/Windows × Node 18/20/22 × Python 3.10–3.13 matrix runs in CI (`.github/workflows/agentpress-validate.yml`) on every push to `v1.0`.

## Live state (verified at run time)

```
@agent_press/agentpress  dist-tags = { rc: '0.2.0-rc.8', latest: '0.2.0', next: '1.0.0-rc.2' }
@agent_press/core        dist-tags = { latest: '1.0.0-rc.1', next: '1.0.0-rc.2' }
@agent_press/mcp-server  dist-tags = { latest: '1.0.0-rc.1', next: '1.0.0-rc.2' }
agentpress-static (PyPI) 1.0.0rc2 available with --pre
agentpress-core   (PyPI) 1.0.0rc2 available with --pre
```

`latest` on the main package stays on `0.2.0` so existing users are untouched.
Promotion to `latest` happens in Phase J after burn-in.

## Test 1–17 — Node CLI from npm (`@agent_press/agentpress@next`)

```
✓ T1: top help shows only 4 verbs (init, lint, doctor, receipt) — no v0.x bloat
✓ T2: --version prints 1.0.0-rc.2
✓ T3: lint in empty dir → exit 3 (FILE_NOT_FOUND)
✓ T4: doctor in empty dir → exit 1
✓ T5: init --non-interactive → exit 0
✓ T6: lint after init → exit 0 (valid)
✓ T7: lint --json → ok=true, parseable JSON
✓ T8: doctor after init → exit 0 (System healthy)
✓ T9: doctor --json → ok=true, ≥5 checks
✓ T10: receipt --stdout-only → valid JSON receipt with sha256 + receipt_id
✓ T11: receipt writes file under agentpress/receipts/
✓ T12: unknown command → exit 1, clean error, no stack trace
✓ T13: init --help → exit 0
✓ T14: lint --help → exit 0
✓ T15: doctor --help → exit 0
✓ T16: receipt --help → exit 0
✓ T17: corrupt agents.txt → exit 1, no stack trace leaked
```

Result: **17/17 pass**.

## Tests 18–29 — Python CLI from PyPI (`agentpress-static==1.0.0rc2`)

```
✓ P1: top help (4 verbs)
✓ P2: --version → 1.0.0rc2
✓ P3: lint empty dir → exit 3
✓ P4: doctor empty dir → exit 1
✓ P5: init --non-interactive → exit 0
✓ P6: lint after init → exit 0
✓ P7: lint --json → ok=true
✓ P8: doctor after init → exit 0
✓ P9: receipt --stdout-only → valid JSON
✓ P10: receipt writes file
✓ P11: unknown command → exit 1
✓ P12: BOM-prefixed agents.txt parses (regression test for Phase C fix)
```

Result: **12/12 pass**.

## Test 30 — Cross-language receipt parity

The same `agents.txt` produces the **same `agents_txt_sha256`** from both Node and Python CLIs. This confirms the parsers agree on canonical bytes.

```
node:   0443409491644c5d549389b42afa18d47ce9ec5cc6fa7c8bd162d007e13b88d6
python: 0443409491644c5d549389b42afa18d47ce9ec5cc6fa7c8bd162d007e13b88d6
✓ identical
```

## Bonus — MCP server boot smoke

`@agent_press/mcp-server@next` (1.0.0-rc.2) installs cleanly, starts, and waits for stdin (correct MCP stdio behavior). No errors on stderr. Process killable cleanly.

## Bonus — Package size budget

Unpacked size of `@agent_press/agentpress@1.0.0-rc.2`: **1,621,766 bytes (~1.6 MB)** — under the 2 MB budget defined in the goal.

Compared to the published `0.2.0` (which was 32.4 MB unpacked / 31,684 files): **~95% smaller / ~99.5% fewer files**.

## Aggregate

| Suite | Tests | Status |
|---|---|---|
| Node CLI from npm | 17 | ✓ all pass |
| Python CLI from PyPI | 12 | ✓ all pass |
| Cross-language parity | 1 | ✓ identical sha256 |
| MCP server boot | 1 | ✓ |
| Package size budget | 1 | ✓ |
| **Total** | **32** | **✓ all green** |

**Goal stop-condition Phase H: MET.** Burn-in window opens.

The goal opens Phase I (burn-in) which lasts until either (a) external installs are confirmed working in the wild or (b) the user signals "promote now." During burn-in, no promotion to `latest` happens.
