# Reddit cross-posts

Each subreddit has different norms. Tailor the post; do NOT copy-paste the same text across subs (Reddit auto-flags).

---

## r/programming

**Title:** `agents.txt v1.0 — an open standard for telling AI coding agents what they're allowed to do on your repo`

**Body:**
```
Same lineage as robots.txt (1994), sitemap.xml (2005), llms.txt (2024). One file at the repo root. INI-style sections (.gitconfig style). Three required lists: allowed_actions, prohibited_actions, requires_human_approval.

Built because every coding agent in 2026 (Devin, Claude Code, Cursor, Aider) has to guess what the maintainer considers safe. CONTRIBUTING.md is for humans. LICENSE is about copyright. agents.txt is the missing machine-readable contract.

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md

Ships today, all MIT:
- CLI (npm + PyPI) — `npx @agent_press/agentpress init` → 5 questions, drops the file + GH Action template + README badge in 60 seconds
- @agentpress/core — zero-dep TypeScript parser (and Python mirror)
- GitHub Action — fails CI on misconfig
- VS Code + browser extensions
- MCP server — Claude Code, Cursor, Devin can query the contract natively

Site: https://agentpress.dev
Repo: https://github.com/barneywohl/agentpress

Honest feedback welcome on the schema. v1.0 is intentionally small so v1.1 can address real friction quickly.
```

---

## r/MachineLearning

**Flair:** `[D] Discussion` or `[N] News` — whichever the mods prefer.

**Title:** `[D] agents.txt v1.0 — open standard for declaring AI agent behavior boundaries on a repo`

**Body:**
```
Curious what folks here think of this approach.

The problem: autonomous coding agents (Devin, Claude Code, Cursor, Aider, Replit Agent) increasingly land changes in production repositories. They have no consistent way to know what the project's maintainers consider safe behavior. The result is either over-cautious refusals or unsafe edits.

The proposal: a one-file contract at the repo root, declaring allowed / prohibited / requires-human-approval action lists, plus entry points, rate limits, an optional MCP server URL, and disclosure rules. INI-style format (low cognitive load, no YAML indentation games).

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md

Notably out of scope for v1.0: cryptographic signing (planned v1.1), per-agent ACLs (v1.2), enforcement at the HTTP layer (intentionally — this declares social rules, CI/branch protection enforces).

Reference implementations (MIT):
- TypeScript parser, zero deps
- Python parser, stdlib only
- GitHub Action that lints in CI
- MCP server so Claude Code / Cursor / Devin can query natively

The bet is on the standard, not any individual tool. Curious what folks here would push back on, especially around: schema completeness, abuse vectors (e.g., malicious permissive contracts), and whether this should integrate with eval frameworks.
```

---

## r/OpenAI + r/Anthropic + r/ClaudeAI

(One post per sub, mostly the same content — focus on the model integration angle.)

**Title:** `agents.txt v1.0 — Claude / GPT / Cursor agents can now read a contract before acting on a repo`

**Body:**
```
Built an open standard so coding agents know what's allowed and prohibited on any repo they encounter. agents.txt at the repo root, INI format, three required lists.

The MCP server (`@agentpress/mcp-server`) plugs into Claude Code or any MCP-speaking agent. Three function calls become available:
- agents_txt_fetch(url) → fetch + parse
- agents_txt_check_action(url, action) → returns allow / deny / requires_approval / unknown
- agents_txt_validate(text) → check a draft

So your agent can, before opening a PR, ask: "is merge_to_main allowed here?" and get a deterministic answer.

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
Repo: https://github.com/barneywohl/agentpress

MIT, free to fork. Curious if Anthropic / Cursor want to ship native support — the MCP integration is one config away.
```

---

## r/LocalLLaMA

**Title:** `agents.txt v1.0 — let your local model know what it can and can't touch on a repo`

**Body:**
```
For folks running local models (Ollama, llama.cpp, vLLM) as coding agents — there's now a one-file standard for declaring repo-level boundaries that any model can parse with zero deps.

agents.txt at the repo root. INI format. Three lists: allowed_actions, prohibited_actions, requires_human_approval.

Reference parsers are tiny:
- TypeScript: ~250 LOC, zero deps
- Python: ~300 LOC, stdlib only

Easy to embed in your own agent loop without pulling in heavy deps.

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
Code: https://github.com/barneywohl/agentpress
```

---

## r/devops

**Title:** `agents.txt — declarative contract for AI agents touching your CI/CD repos`

**Body:**
```
Anyone else worried about coding agents landing PRs in production repos with no clear contract on what they're allowed to do? Built this to fix it.

agents.txt at the repo root + a GitHub Action that lints the contract on every PR. Required sections cover: allowed actions, prohibited actions (e.g. modify_secrets, deploy_to_production), requires-human-approval changes (schema migrations, billing, etc.), entry points (which test command to run, which OpenAPI to read), rate limits, scope caps, disclosure rules.

The GH Action posts a structured Step Summary to every workflow run.

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
Repo: https://github.com/barneywohl/agentpress

MIT. v1.0 today; v1.1 adds cryptographic signing for compliance use cases.
```

---

## Cross-posting hygiene

- Wait 1+ hour between subs to avoid auto-throttle
- Don't link from one Reddit comment to another (looks like brigading)
- Reply to every top-level comment within 60 minutes
- Don't argue. If a critique is valid, fix in v1.0.1 and say so
- If a sub mods auto-remove for "self-promotion," PM the mods politely with context
