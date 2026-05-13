# Newsletter outreach

Five short, personalized emails. Each is one paragraph + the link. Newsletter editors hate boilerplate; do NOT mass-mail.

---

## TLDR (TLDR Newsletter)

**To:** dan@tldrnewsletter.com (or whoever currently runs TLDR Founders / TLDR AI)
**Subject:** Open standard for AI agent governance — agents.txt v1.0

```
Hi Dan,

Long-time reader. I shipped a small open standard today that I think TLDR readers might actually use: agents.txt — a one-file contract at the repo root that tells autonomous AI agents (Claude Code, Cursor, Devin, Aider) what they're allowed to do on a project. Same lineage as robots.txt and llms.txt.

Spec is one page, MIT, all reference impls open: https://agentpress.dev

The pitch is the analogy: "robots.txt for crawlers, llms.txt for LLMs, agents.txt for autonomous agents." Adoption is `npx @agent_press/agentpress init`.

If TLDR Dev / TLDR AI ever covers it, would love to know — happy to answer any follow-up questions or get on a quick call. No expectation either way.

Thanks for the newsletter.
— [your name]
```

---

## Pragmatic Engineer (Gergely Orosz)

**To:** gergely@pragmaticengineer.com
**Subject:** Open standard for what AI agents may do on a repo

```
Hi Gergely,

Pragmatic Engineer reader. Shipped an open standard today that's directly in your wheelhouse — agents.txt, a single-file machine-readable contract for what autonomous coding agents may and may not do on a repo. Lineage: robots.txt → sitemap.xml → llms.txt → agents.txt.

Built because every coding agent I use (Claude Code, Cursor) currently guesses at what's safe. The contract is INI format, fits on one page, and a CLI / GitHub Action / MCP server make adoption a 60-second move.

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
Site: https://agentpress.dev (MIT)

Would value your honest take, especially on whether the schema captures the right things. No ask beyond that.

Thanks for the work you do — your "AI engineer" coverage shaped a lot of how I think about this.
— [your name]
```

---

## AI Tidbits (Sahar Mor)

**To:** [Sahar's contact via aitidbits.ai]
**Subject:** agents.txt — open standard for AI agent governance on repos

```
Hi Sahar,

Reader of AI Tidbits. Shipped an open standard that might be a fit for a future issue.

agents.txt v1.0 — one-file contract at the repo root that declares what autonomous AI agents (Devin, Claude Code, Cursor, Aider) may/may-not do on a project. Includes a GitHub Action, VS Code + browser extensions, and an MCP server so Claude Code/Cursor can natively respect the contract.

Lineage analogy: robots.txt → llms.txt → agents.txt.

All MIT, ships today: https://agentpress.dev
Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md

If it's a fit for AI Tidbits, would love to know. Either way, thanks for the work.
— [your name]
```

---

## Latent Space (Swyx & Alessio)

**To:** swyx@latent.space
**Subject:** Open standard for AI agent governance — wondered if it's pod-worthy

```
Hi swyx,

Latent Space listener. Shipped an open standard today and wondered if it's pod-worthy or just a brief mention.

agents.txt — one-file contract that tells autonomous coding agents what they're allowed to do on a repo. Lineage: robots.txt → llms.txt → agents.txt. Spec is one page; reference parsers in TS + Python; MCP server so Claude Code / Cursor / Devin natively respect the contract; VS Code extension, browser extension, GitHub Action all ship today.

The bet is on the standard, not the tool. Want adoption in 50+ high-signal repos within 30 days; if that lands, the agent platforms ship native support.

Site: https://agentpress.dev
Repo: https://github.com/barneywohl/agentpress (MIT)

Would love to chat about the design choices (INI over YAML, MCP integration, what v1.1 should add) if there's interest. No pressure.

Thanks for everything you ship.
— [your name]
```

---

## Rest of World

(More of a stretch — Rest of World does global tech reporting but covers AI infrastructure occasionally. Pitch as "infrastructure for the agent economy globally.")

**To:** [editorial inbox]
**Subject:** Open standard for AI agent governance — global infrastructure angle

```
Hi,

Rest of World reader. Shipped an open standard today that has a global tech infrastructure angle worth a brief look.

agents.txt v1.0 — open, MIT-licensed contract for telling autonomous AI agents what they're allowed to do on a repo or website. Same role as robots.txt for crawlers, but for the agent economy that's exploding globally in 2026.

Why it might be of interest: agent platforms (Devin, Manus, Cursor, Replit Agent, Anthropic's Claude Code) are landing real changes on real codebases with no agreed-upon governance layer. agents.txt is the smallest possible answer — adoption is one CLI command. The bet is on the standard becoming default, similar to how robots.txt did in the 1990s.

All MIT, ships today: https://agentpress.dev
Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md

Happy to answer any questions. No expectation of coverage; just on the off chance it's useful.
— [your name]
```

---

## Outreach hygiene

- Send personally, NOT via Mailchimp / SendGrid
- Use your real name + a real signature with website + GitHub handle
- Don't follow up more than once (one polite nudge after 7 days, then stop)
- If they cover it, share + tag them publicly within 24 hours
- If they don't, that's fine — try again with v1.1 or a major adoption milestone
