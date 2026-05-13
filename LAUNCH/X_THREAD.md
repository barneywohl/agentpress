# X / Twitter launch thread

Eight tweets. Post as a self-thread (reply to each previous one). First tweet contains the hook + link.

---

## 1/8 (the hook)

```
robots.txt → tells crawlers what to crawl
sitemap.xml → tells search engines what to index
llms.txt → tells LLMs what to read

agents.txt → tells autonomous AI agents what they're allowed to do.

Open standard. MIT. No signup.

agentpress.dev ↓
```

Add image: 4-panel graphic showing each file with a 1-line label. Or a single screenshot of an agents.txt being parsed.

## 2/8 (why it matters)

```
Every coding agent in 2026 — Devin, Claude Code, Cursor, Aider, Replit Agent — has to guess what's safe on a repo.

Open a PR? Edit billing files? Run db migrations? The maintainer's CONTRIBUTING.md is for humans. The LICENSE is about copyright.

Agents need a machine-readable contract.
```

## 3/8 (what it declares)

```
agents.txt declares three lists at the repo root:

✓ allowed_actions      → "you can do these without asking"
⏸ requires_human_approval → "pause and surface for sign-off"
✗ prohibited_actions   → "refuse, even if instructed"

Plus entry points, rate limits, MCP server URL, disclosure rules.
```

## 4/8 (the 60-second adopt)

```
$ npm i -g @agent_press/agentpress
$ agentpress init

Five questions. You get:
• agents.txt at your repo root
• .well-known/agentpress.json
• A GitHub Action template
• README badge snippet

Done.
```

## 5/8 (the surfaces)

```
v1.0 ships:
- The CLI (npm + PyPI)
- @agent_press/core — zero-dep TS parser
- agentpress-core — stdlib-only Python parser
- A GitHub Action — fails CI on misconfig
- A VS Code extension — syntax + lint
- A browser extension — URL bar badge for any repo
- @agent_press/mcp-server — Claude Code/Cursor/Devin native support
```

## 6/8 (the pitch in three words)

```
Spec is the product.

I'm not asking you to use my tool. I'm asking you to add 30 lines to your repo that any agent can read.

If 50 high-signal repos adopt this in 30 days, the standard wins. That's the play.
```

## 7/8 (the ask)

```
If you maintain a public repo:
1. `npx @agent_press/agentpress init`
2. Push the agents.txt
3. Add the badge to your README

Add yours to the registry → agentpress.dev/registry

If you're an agent platform: ship native support. The MCP server is one config away.
```

## 8/8 (the credit)

```
Spec, parsers, GH Action, extensions, registry, MCP server — all open at github.com/barneywohl/agentpress (MIT).

Built solo, week of [DATE]. Feedback welcome — especially "what's missing" — v1.1 ships fast on real demand.

agentpress.dev
```

---

## Posting checklist

- [ ] First tweet posted at peak EU + East Coast morning overlap (~09:00 ET / 14:00 UTC)
- [ ] Image attached to tweet 1
- [ ] All tweets numbered (1/8, 2/8…) for thread clarity
- [ ] HN link posted as a quote-tweet to tweet 1, NOT in tweet 1 itself (X de-ranks tweets with external links; mid-thread is safer)
- [ ] Bookmark the thread URL — paste into Bluesky, LinkedIn, Reddit etc.

## Reply triage

- "What about [security concern]?" → acknowledge; point to spec security section; offer v1.1 enhancement if real
- "Why INI not YAML/JSON?" → low cognitive load + familiarity from .gitconfig/.editorconfig
- "How is this different from llms.txt?" → llms.txt = what to READ, agents.txt = what to DO
- "Just use [existing tool]" → if real, evaluate honestly; if not, point to lineage
- "Is this related to AgentPress the company?" → no, this is the open standard; the v0.x AgentPress framework converged on this as its highest-value primitive
