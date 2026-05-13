# Product Hunt launch

## Page setup

| Field | Content |
|---|---|
| Name | `AgentPress` |
| Tagline | `agents.txt for any repo — the open standard for AI agent governance` |
| Description | (see below) |
| First link | `https://agentpress.dev` |
| Topics | Developer Tools, Open Source, Artificial Intelligence, GitHub, Productivity |
| Pricing | Free |
| Maker comment | (see below) |
| Gallery | Screenshots: 1) hero of agentpress.dev, 2) example agents.txt, 3) GH Action passing, 4) VS Code with syntax highlighting, 5) browser ext popup |

## Description

```
robots.txt told crawlers what to crawl.
llms.txt told LLMs what to read.
agents.txt tells autonomous AI agents what they're allowed to do on your repo.

In 2026, coding agents (Devin, Claude Code, Cursor, Aider, Replit Agent) are landing PRs in production codebases. None of them have a machine-readable answer to "what's safe?" CONTRIBUTING.md is for humans; LICENSE is about copyright. agents.txt is the missing piece.

One file at the repo root. Three lists: allowed_actions, prohibited_actions, requires_human_approval. Plus entry points, rate limits, MCP server URL, disclosure rules.

✦ Open standard, MIT licensed
✦ One CLI command to adopt: `npx @agent_press/agentpress init`
✦ GitHub Action fails CI on misconfig
✦ VS Code + browser extensions
✦ Native MCP server for Claude Code, Cursor, Devin
✦ Curated registry of early adopters
✦ Reference parsers in TypeScript + Python (zero deps)

Spec, code, extensions — all in one open repo: github.com/barneywohl/agentpress
```

## Maker comment (post immediately after launch goes live)

```
Hi PH 👋

Built this because every coding agent I use (Claude Code, Cursor, occasionally Devin) constantly has to guess at what's OK to do on a repo. They guess wrong sometimes — usually safely cautious, but sometimes destructively bold.

agents.txt is the simplest possible answer: a one-page contract at the repo root. The whole spec is here: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md

The bet is that if 50 high-signal repos adopt the file in 30 days, the agent platforms start respecting it natively. That's the moat — not the tool, the standard.

Everything ships today: CLI, parser libraries (TS + Python), GitHub Action, VS Code extension, browser extension, MCP server. All MIT.

Adoption is `npx @agent_press/agentpress init`. Five questions. Done.

Happy to answer questions on the schema choices, the MCP integration, or what's coming in v1.1 (cryptographic signing). Especially want to hear from anyone running agents in production today — what's missing?
```

## Promotion checklist

- [ ] Schedule PH launch for 12:01 AM PT (PT timezone matters; PH resets daily at midnight PT)
- [ ] DM 5-10 hunters / founders with the link the day-before; ask for honest first impressions, not upvotes
- [ ] Post in the PH Slack / Discord communities if a member
- [ ] Reply to every comment within 30 minutes — PH rewards engagement velocity in the daily ranking
- [ ] Post the PH URL in the X thread + on Bluesky once live
- [ ] Don't fake votes; PH penalizes vote rings hard
