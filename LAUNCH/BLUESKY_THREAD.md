# Bluesky launch thread

Bluesky audience leans more open-source, more standards-curious, less hype-y than X. Adjust accordingly: less marketing voice, more spec-doc voice.

Single post (Bluesky favors longer single posts over threads):

```
agents.txt — an open standard for telling autonomous AI agents what they're allowed to do on your repo or site.

Same lineage as robots.txt (1994), sitemap.xml (2005), llms.txt (2024).

One file at the repo root. Three lists: allowed_actions, prohibited_actions, requires_human_approval. Plus entry points, rate limits, MCP server, disclosure rules.

Spec, reference parsers (TS + Python), GitHub Action, VS Code extension, browser extension, MCP server for Claude Code/Cursor/Devin — all MIT licensed, all in one repo.

If you maintain a public repo, `npx @agent_press/agentpress init` will draft a sensible agents.txt for you in 60 seconds.

agentpress.dev
github.com/barneywohl/agentpress

Feedback especially welcome on the schema — v1.0 is small enough that v1.1 can address real friction quickly.
```

Then a follow-up post with a screenshot of the spec page or a sample agents.txt rendered.

## Tags / labels

#opensource #ai #standards #devtools #agents

## Cross-post

Pin to your profile for the launch window. Quote-post the HN URL when that goes up.
