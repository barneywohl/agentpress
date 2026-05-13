# Show HN submission

## Title (80 char max — HN guideline; this fits)

```
Show HN: Agents.txt – like robots.txt, but for telling AI agents what they can do
```

**Why this title:** Lineage analogy is the entire pitch. "Show HN" gets vouched faster than "Show HN: AgentPress." Spec name in title — people pattern-match into "real standard, not a startup."

## URL (HN submission URL field)

```
https://agentpress.dev
```

(If `agentpress.dev` not bought yet by launch: `https://agentpress.pages.dev`)

## First comment (post immediately after submission)

Submit the post WITHOUT a comment, then post this within 60 seconds. HN guidelines specifically endorse this pattern.

```
Hi HN — I built this because every coding agent in 2026 has to guess what's safe to do on a repo. Devin opens a PR. Claude Code edits a file. Cursor refactors something. None of them know whether the maintainer is OK with that, what's allowed without approval, what's flat-out prohibited. The repo's CONTRIBUTING.md is for humans. The LICENSE is about copyright. There's no machine-readable answer.

agents.txt is the answer. One file at the repo root. INI-style sections (familiar from .gitconfig and .editorconfig). Three required lists: allowed_actions, prohibited_actions, requires_human_approval. Plus entry points, MCP server URL, rate limits, scope caps, disclosure rules.

The whole spec fits on one page: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md

What I shipped today:
- The spec (MIT, free to fork)
- A CLI: `npx @agent_press/agentpress init` — 5 questions, drops everything in your repo in 60 seconds
- @agent_press/core — zero-dep TypeScript parser (and a Python mirror for the data side)
- A GitHub Action — fails CI when the contract is malformed
- README badge generator — every adopter advertises the spec for free
- VS Code extension — syntax highlighting + on-save validation
- Browser extension (Chrome + Firefox) — URL-bar badge whenever you visit a repo or site with an agents.txt
- An MCP server — Claude Code, Cursor, Devin, Aider can natively query the contract before acting
- A curated registry of early adopters

The whole thing is MIT. The package is 313 KB on npm (compressed) — about 65× smaller than the v0.x preview. No vendor lock-in. The spec is the product.

Lineage: robots.txt (1994) → sitemap.xml (2005) → llms.txt (2024) → agents.txt (2026).

Happy to answer questions about the schema choices, why I picked INI over YAML, where MCP fits, or anything else. Also genuinely curious about what's missing — the spec is at v1.0 but small enough that v1.1 can address real pain quickly.
```

## Tags (HN doesn't use them, but if asked elsewhere)

`open-source`, `ai-agents`, `developer-tools`, `standard`, `mcp`, `claude-code`, `cursor`, `devin`

## Vouch / amplify

After submission, ask 3-5 people you know with HN accounts to view the post (NOT to upvote — HN penalizes vote rings). Just visiting helps the algorithm.

## Post-submission tasks

- [ ] Pin the HN URL in the X thread when it goes up.
- [ ] Reply to every top-level comment within 30 minutes during waking hours.
- [ ] Don't argue. Acknowledge legitimate concerns. Ship a v1.0.1 patch fast for any real bug surfaced.
- [ ] If it hits front page (top 30), post a separate "wow this got traction, here's what's next" tweet.
