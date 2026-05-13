# AgentPress Full Reference

> v1.0 CLI surface. Legacy v0.x commands are still accessible via `agentpress legacy <cmd>` but are not documented here — they are deprecated for removal in v2.0.

## Top-level

```
agentpress [global options] <command> [command options]
```

### Global options

| Flag | Description |
|---|---|
| `-h`, `--help` | Show top-level help and exit 0 |
| `-v`, `--version` | Print version and exit 0 |

### Commands

| Verb | Purpose |
|---|---|
| `init` | Drop an `agents.txt` at your repo root |
| `lint` | Validate an `agents.txt` against the v1.0 spec |
| `doctor` | Run a health check on the v1.0 surface |
| `receipt` | Generate a content-addressed JSON proof receipt |
| `legacy` | Forward to the v0.x command surface (deprecation banner) |

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Errors found (validation, unknown command, user abort) |
| 2 | Strict-mode warnings escalated, or internal error |
| 3 | `agents.txt` not found where expected |

### Environment variables

| Variable | Effect |
|---|---|
| `AGENTPRESS_DEBUG=1` | Print stack traces on internal errors |
| `AGENTPRESS_LEGACY_QUIET=1` | Silence the legacy deprecation banner |
| `PYTHON` | Override the Python interpreter used for `agentpress legacy ...` (Node CLI only) |

---

## `agentpress init`

```
agentpress init [path] [options]
```

Interactive wizard that drops an `agents.txt` at your repo root with sensible defaults.

### Auto-detected facts (silent, before prompts)

- Repo type: `node` / `python` / `go` / `rust` / `ruby` / `php` / `monorepo:<list>` / `generic`
- CI provider: GitHub Actions / GitLab / CircleCI / Azure Pipelines
- GitHub origin (owner/repo from `.git/config`)
- Maintainer email (from `package.json` author → `pyproject.toml` authors → `git config user.email`)
- Project name (from `package.json` → `pyproject.toml` → repo name)

### Prompts

1. Maintainer email
2. AI disclosure required for agent-authored PRs? (default Y)
3. Allow agents to file PRs without per-PR approval? (default Y)
4. Require human approval for changes to billing/, payments/, auth/, security/? (default Y)
5. Add a GitHub Actions workflow that lints `agents.txt` on every PR? (default Y if GitHub Actions detected)

### Options

| Flag | Description |
|---|---|
| `-y`, `--non-interactive` | Use sensible defaults; no prompts |
| `-f`, `--force` | Overwrite an existing `agents.txt` |
| `-o`, `--out PATH` | Write into PATH instead of the current repo root |
| `-h`, `--help` | Show command help |

### Outputs

| File | When written |
|---|---|
| `agents.txt` | Always |
| `.github/workflows/agentstxt.yml` | If GitHub Actions detected and you say yes |
| `agentpress/receipts/init_<id>.json` | Always (init receipt) |
| README badge snippet on stderr | Always |

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | `agents.txt` already exists (use `--force`) or user aborted |
| 2 | Internal error (generated file failed inline validation — should never happen) |

---

## `agentpress lint`

```
agentpress lint [path] [options]
```

Validate an `agents.txt` against the v1.0 spec.

### Arguments

| Arg | Description |
|---|---|
| `path` | Path to the `agents.txt` (or to a directory containing one). Default: `./agents.txt` |

### Options

| Flag | Description |
|---|---|
| `--json` | Emit machine-readable JSON output |
| `--strict` | Treat warnings as errors (exit 2 on warnings) |
| `-h`, `--help` | Show command help |

### JSON output schema

```json
{
  "ok": true,
  "path": "/abs/path/to/agents.txt",
  "spec_version": "1.0",
  "project": "my-project",
  "errors": 0,
  "warnings": 0,
  "issues": []
}
```

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Valid |
| 1 | One or more errors |
| 2 | Strict-mode warnings escalated |
| 3 | `agents.txt` not found |

---

## `agentpress doctor`

```
agentpress doctor [path] [options]
```

Comprehensive health check.

### Checks

1. Runtime version — Node ≥ 18 (Node CLI), Python ≥ 3.10 (Python CLI)
2. Other-language runtime available (optional, for `agentpress legacy ...`)
3. Core parser library loadable (`@agent_press/core` / `agentpress-core`)
4. `agents.txt` exists
5. `agents.txt` parses
6. `agents.txt` validates
7. `.github/workflows/agentstxt.yml` present
8. README badge present
9. `agentpress` CLI on PATH

### Options

| Flag | Description |
|---|---|
| `--json` | Emit JSON output |
| `-h`, `--help` | Show command help |

### JSON output schema

```json
{
  "ok": true,
  "version": "1.0.0-rc.2",
  "root": "/abs/repo/path",
  "checks": [
    { "name": "Node.js >= 18", "status": "pass", "detail": "node 22.22.0" }
  ],
  "summary": { "pass": 7, "warn": 1, "fail": 0, "skip": 1 }
}
```

### Exit codes

| Code | Meaning |
|---|---|
| 0 | All checks pass (warnings allowed) |
| 1 | One or more errors |

---

## `agentpress receipt`

```
agentpress receipt [path] [options]
```

Generate a content-addressed JSON receipt proving an `agents.txt` was validated. v1.0 receipts are unsigned but content-addressed via sha256 — verify later by re-hashing the file. v1.1 will add ed25519 signing.

### Options

| Flag | Description |
|---|---|
| `--stdout-only` | Print receipt to stdout; do not write to disk |
| `-o`, `--out PATH` | Write receipt to PATH (default `agentpress/receipts/<id>.json`) |
| `--json` | Print the receipt to stdout in addition to writing (default when writing) |
| `-h`, `--help` | Show command help |

### Receipt schema

```json
{
  "schema_version": "agentpress-receipt.v1",
  "ts": "2026-05-13T16:42:14.764Z",
  "kind": "lint",
  "agents_txt_path": "agents.txt",
  "agents_txt_sha256": "ac066071ef634bb1aae88471237c2c4c624427eee85ada0f86fbccb9f03e0ae8",
  "spec_version": "1.0",
  "project": "AgentPress",
  "validation": { "ok": true, "errors": 0, "warnings": 0 },
  "agentpress_version": "1.0.0-rc.2",
  "receipt_id": "rcpt_a1b2c3d4e5f6"
}
```

### Cross-language parity

The Node CLI and Python CLI produce **identical receipts** (modulo `ts`) for the same `agents.txt` input. The `agents_txt_sha256` field will match exactly. CI verifies this on every push.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Receipt generated |
| 1 | `agents.txt` has errors (run `agentpress lint`) |
| 3 | `agents.txt` not found |

---

## `agentpress legacy <subcommand>`

```
agentpress legacy <subcommand> [args...]
```

Forward a command to the v0.x CLI surface (`scripts/agentpress.py`). Useful while functionality migrates into native v1.0 verbs.

A one-time deprecation banner is shown per invocation (silence with `AGENTPRESS_LEGACY_QUIET=1`).

This forwarding stays supported through v1.x and is removed in v2.0.

Run `agentpress legacy --help` for the full v0.x subcommand listing.

---

## Where to read next

- [agents.txt v1.0 specification](../docs/AGENTSTXT_SPEC.md)
- [README badge snippets](../docs/BADGE.md)
- [Registry of repos that adopted agents.txt](../registry/README.md)
- [GitHub Action: agentpress/setup-action](../actions/setup-action/)
- [VS Code extension](../extensions/vscode/)
- [Browser extension (Inspector)](../extensions/browser/)
- [MCP server (Claude Code / Cursor / Devin / Aider)](../packages/mcp-server/)
