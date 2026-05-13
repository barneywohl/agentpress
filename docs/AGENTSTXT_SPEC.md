# `agents.txt` Specification

**Version:** 1.0
**Status:** Draft for adoption
**License:** MIT (this spec is free to implement, fork, and embed)

---

## Abstract

`agents.txt` is a text file at the root of a repository or web server (`/agents.txt`) that declares what autonomous AI agents are allowed and expected to do in that repo or on that site. It sits in the lineage of `robots.txt` (1994), `sitemap.xml` (2005), and `llms.txt` (2024) — small, copy-pasteable, machine-readable contracts that describe the social rules of a piece of internet real estate to non-human visitors.

`agents.txt` answers a question that every coding agent in 2026 currently has to guess at: **what is this repo's owner OK with me doing here?**

---

## Why a new file format

- `robots.txt` predates LLMs and addresses crawlers, not actors.
- `sitemap.xml` is a discovery aid, not a permissions contract.
- `llms.txt` describes what to **read**, not what to **do**.
- `LICENSE` describes copyright, not behavior.
- `CONTRIBUTING.md` is for humans and is not machine-parseable.

`agents.txt` fills the gap: a typed, machine-parseable, human-readable declaration of allowed/prohibited/requires-approval actions for autonomous agents.

---

## File location

- **Repo:** `/agents.txt` at the root, alongside `README.md` and `LICENSE`.
- **Site:** `https://example.com/agents.txt`, served as `text/plain; charset=utf-8`.

When both a site and a repo exist, both should host an `agents.txt`. The site version is authoritative for runtime decisions; the repo version is authoritative for code-level decisions.

---

## File format

INI-style sections (familiar from `.gitconfig`, `.editorconfig`). Chosen over YAML for low cognitive load and over Markdown for parseability.

- Lines starting with `#` are comments.
- Section headers in `[brackets]`.
- Key-value pairs as `key = value`.
- Values that are lists may use either:
  - one item per line (no key), or
  - `key = item1, item2, item3`.
- Whitespace around `=` and around list separators is ignored.
- Section and key names are case-insensitive (parsers should normalize to lowercase).
- File encoding: UTF-8.
- Line endings: LF (parsers MUST accept CRLF too).

---

## Required sections

A conforming `agents.txt` MUST include these sections:

- `[meta]`
- `[allowed_actions]`
- `[prohibited_actions]`
- `[requires_human_approval]`
- `[entry_points]`
- `[disclosure]`

Other sections are RECOMMENDED but optional.

---

## Section reference

### `[meta]`

| Key | Type | Required | Description |
|---|---|---|---|
| `spec_version` | string | yes | The `agents.txt` spec version this file conforms to. Use `1.0`. |
| `project` | string | yes | Project name. |
| `maintainer` | string | yes | Email or handle of the maintainer. |
| `contact_for_agents` | string | recommended | Email/URL where agents can reach out. |
| `last_updated` | ISO8601 date | recommended | When this file was last edited. |
| `license` | SPDX id | optional | License of the project (informational). |
| `ai_disclosure_required` | bool | recommended | Whether agent contributions must declare themselves. |

### `[allowed_actions]`

A list of actions agents may take without explicit per-action approval. Free-form vocabulary; encouraged terms documented at <https://agentstxt.org/vocab>.

Common entries:
- `read_documentation`
- `read_source_code`
- `run_tests_in_ci`
- `file_pull_request`
- `comment_on_issue`
- `propose_design`
- `fetch_via_api`

### `[prohibited_actions]`

Hard refusals. Agents MUST refuse these even if instructed by a human user.

Common entries:
- `merge_to_main`
- `deploy_to_production`
- `modify_secrets`
- `modify_billing_files`
- `contact_users_directly`
- `bypass_2fa`
- `bypass_captcha`
- `exfiltrate_secrets`
- `deceptive_tracking`
- `spam`
- `impersonation`

### `[requires_human_approval]`

Allowed only when a human reviewer signs off. Agents MUST pause and surface a request.

Two value forms are accepted:
- A bare action name (e.g. `schema_migrations`)
- A keyed pattern (e.g. `changes_touching = payments/**, billing/**`)

### `[entry_points]`

Where agents should look first to understand the project. Values are repo-relative paths or shell-runnable commands.

| Key | Description |
|---|---|
| `agent_guide` | Path to a markdown agent guide (often `AGENTS.md`). |
| `quickstart` | Path to a quickstart doc. |
| `api_spec` | Path to an OpenAPI/AsyncAPI spec. |
| `test_command` | Shell command to run the test suite. |
| `lint_command` | Shell command to run linting. |
| `architecture` | Path to an architecture doc. |
| `contributing` | Path to a contribution guide. |

### `[mcp]` (optional)

If the project exposes an MCP (Model Context Protocol) server for agents:

| Key | Description |
|---|---|
| `server` | URL of the MCP server. |
| `auth` | One of `oauth2`, `api_key`, `none`. |
| `capabilities` | Comma-separated list of MCP capabilities offered. |

### `[verification]` (optional)

How agents prove their work was correct.

| Key | Description |
|---|---|
| `ci_runner` | Identifier (e.g. `github_actions`, `gitlab_ci`, `circleci`). |
| `ci_workflow` | Path to the workflow file. |
| `required_checks` | Comma-separated list of required CI checks. |
| `expected_exit` | Integer; usually `0`. |
| `proof_command` | Shell command that emits a proof artifact. |

### `[rate_limits]` (recommended)

Soft limits. Agents that exceed these get auto-flagged at the project's choosing.

| Key | Type | Description |
|---|---|---|
| `max_pull_requests_per_day` | int | Per agent. |
| `max_issues_per_day` | int | Per agent. |
| `max_comments_per_day` | int | Per agent. |
| `max_concurrent_branches` | int | Per agent. |

### `[scope]` (recommended)

Soft limits on the size of any single agent contribution.

| Key | Type | Description |
|---|---|---|
| `max_files_changed` | int | Per PR. |
| `max_lines_changed` | int | Per PR. |
| `single_purpose_pr` | bool | Whether each PR must address exactly one concern. |

### `[disclosure]`

How agents identify themselves.

| Key | Description |
|---|---|
| `pr_label` | Label to apply to agent-authored PRs (e.g. `agent-authored`). |
| `commit_trailer` | Git trailer to use (e.g. `Authored-by-Agent: <agent-name> <agent-version>`). |
| `require_attribution_in_pr_body` | Bool; whether the PR body must declare the agent. |

### `[contact]` (recommended)

Where agents go when blocked.

| Key | Description |
|---|---|
| `escalation` | URL or email for escalation. |
| `escalation_email` | Optional; explicit email override. |

### `[fyi]` (optional)

Free-form, informational preferences. Not enforced.

Common keys:
- `preferred_branch_naming`
- `preferred_pr_size`
- `preferred_commit_style`
- `timezone`
- `preferred_response_window_hours`

---

## Conformance

A repo or site is **`agents.txt`-conformant** if:

1. It serves an `agents.txt` file at the canonical location.
2. The file parses against this v1.0 spec without errors.
3. The required sections (`[meta]`, `[allowed_actions]`, `[prohibited_actions]`, `[requires_human_approval]`, `[entry_points]`, `[disclosure]`) are present.
4. `[meta].spec_version` matches a published version.

An agent is **`agents.txt`-respecting** if:

1. It fetches and parses `agents.txt` before acting on a repo or site.
2. It refuses every entry in `[prohibited_actions]`.
3. It pauses on every entry in `[requires_human_approval]` and surfaces an approval request.
4. It respects `[rate_limits]` and `[scope]` budgets.
5. It identifies itself per `[disclosure]`.
6. It exposes its conformance state to operators (e.g., a `--strict-agents-txt` flag).

---

## Security considerations

- `agents.txt` is **not** an authentication layer. It declares social rules, not enforces them at the wire level. Agents that ignore the file face social and reputational consequences, not technical ones.
- For real enforcement, pair `agents.txt` with: branch protection, required reviews, CI lint of the file's contract against the diff, and per-agent identity tokens.
- A malicious actor can serve a permissive `agents.txt`. Tools should treat the file as the project's stated intent, not as ground truth.

---

## Backwards compatibility

- Future versions (1.1, 1.2, 2.0) MUST keep the meaning of `[meta].spec_version`. Parsers SHOULD warn when they encounter a newer version they don't fully understand and MUST fail safely (treat the file as opaque rather than partially apply unknown semantics).
- New optional sections may be added in minor versions.
- New required sections may only be added in major versions.

---

## Implementation status (v1.0 reference)

| Implementation | Repo | Status |
|---|---|---|
| `@agent_press/core` (TypeScript) | `barneywohl/agentpress` | Reference parser |
| `agentpress-core` (Python) | `barneywohl/agentpress` | Reference parser |
| `agentpress` CLI | `barneywohl/agentpress` | Init, lint, doctor, receipt |
| `agentpress/setup-action` | `barneywohl/agentpress` | GitHub Action for CI |
| VS Code extension `agents-txt` | `barneywohl/agentpress` | Editor support |
| Browser extension AgentPress Inspector | `barneywohl/agentpress` | URL bar badge |
| `@agent_press/mcp-server` | `barneywohl/agentpress` | MCP integration |

---

## Out of scope (v1.0)

These are deliberately deferred to later versions:

- **Cryptographic signing** of `agents.txt` (planned v1.1: `agents.txt.sig` companion file).
- **Per-agent ACLs** like `[allowed_actions:devin]` (planned v1.2).
- **Centralized registry** of all `agents.txt` files on the web (curated only; nobody runs it).
- **Authentication tokens** for agents (use existing protocols like OAuth2).
- **Replacement** for `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` — these are complementary.
- **Enforcement at HTTP layer** — `agents.txt` declares; CI/branch-protection enforce.

---

## License

This specification is released under the MIT License. Implementations are free to embed, fork, and extend. Attribution to the spec URL is appreciated but not required.

---

## Acknowledgments

- The lineage analogy (`robots.txt` → `sitemap.xml` → `llms.txt` → `agents.txt`) draws directly on prior work by the WebCrawler, Sitemap, and `llms.txt` (Jeremy Howard) communities.
- Safety contract framing (allowed / prohibited / requires-human-approval) was prototyped in the `@agent_press/agentpress` v0.x series.
