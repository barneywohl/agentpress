# Security Policy

## Supported versions

| Package | Supported line | Notes |
|---|---:|---|
| `@agent_press/agentpress` | `0.2.0-rc.3` local metadata; `0.1.0` live registry default until next approved publish | Node shim with no-Python first-run fast path plus Python full CLI. |
| `agentpress-static` | `0.2.0rc3` local metadata; `0.1.0` live registry default until next approved publish | PyPI publishing is intentionally separate from this repo commit. |

Older release candidates are best-effort only. Please reproduce issues against the current GitHub `main` branch when possible.

## Reporting a vulnerability

Open a private GitHub security advisory when available, or email `security@agentpress.dev` with:

- affected version / commit SHA;
- exact command, input file, or manifest that triggers the issue;
- whether secrets, credentials, private repo data, external writes, or package publishing could be affected;
- a minimal reproduction that uses synthetic data only.

If email bounces, open a GitHub issue with **no exploit details or secrets** and ask for a private disclosure channel.

## No-secrets guidance

Do not include API keys, `.env` files, private repository contents, auth tokens, cookies, wallet material, npm/PyPI tokens, or production logs in reports. Use redacted fixtures or throwaway test credentials. AgentPress should fail closed around sensitive paths; a bypass is security-relevant.

## Scope

In scope:

- secret/path exfiltration through `doctor`, `lint`, `fetch`, `verify`, schema validation, or generated proof bundles;
- unsafe external writes, registry publishes, or network side effects without explicit human approval;
- MCP/connector metadata that misrepresents permissions, credentials, or side effects;
- package contents that accidentally include secrets, build caches, or local evidence dumps.

Out of scope unless chained to AgentPress behavior: generic dependency CVEs without exploitability, spam/social engineering, denial-of-service against public hosting, and reports requiring access to private systems.

## Response SLA

- Acknowledge: 3 business days.
- Triage target: 7 business days.
- Fix/mitigation target: 30 days for confirmed high-impact issues; sooner for secret exposure or unauthorized writes.

AgentPress is static-first and local-first. Any live publish, external outreach, production deploy, or credentialed action remains outside the package default path and requires separate human approval.
