# AI lab / agent platform outreach

Five emails to the people most likely to ship native support for agents.txt — which is the moat. Each is one paragraph, no ask beyond awareness.

---

## Anthropic devrel (Claude Code team)

**To:** devrel@anthropic.com (or Alex Albert, or whoever currently runs Claude Code devrel)
**Subject:** Shipped agents.txt — Claude Code MCP integration is one config away

```
Hi,

Long-time Anthropic API + Claude Code user. Shipped a small open standard today that I think slots cleanly into Claude Code: agents.txt — a one-file contract at the repo root that declares what autonomous agents are allowed and prohibited from doing on the project. Same lineage as robots.txt and llms.txt.

The reason this might matter to you: I've shipped an MCP server (@agent_press/mcp-server) so Claude Code can natively query any repo's agents.txt before acting. Three tools: agents_txt_fetch(url), agents_txt_check_action(url, action), agents_txt_validate(text). One config block in mcp_settings.json and Claude Code is contract-aware.

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
Repo (all MIT): https://github.com/barneywohl/agentpress

If Claude Code ever wanted to ship native first-class support for agents.txt — fetching it on repo open, surfacing the contract in the UI, blocking prohibited actions — happy to align the spec with what makes that easy on your end. No expectation of anything; just wanted you to know it exists in case it's useful.

Thanks for the work on Claude Code — the daily flow is genuinely good.
— [your name]
```

---

## Cursor team

**To:** founders@cursor.com (or aman@cursor.com)
**Subject:** agents.txt — Cursor MCP support is one config block

```
Hi,

Cursor user. Shipped an open standard today, agents.txt, that I think slots cleanly into Cursor.

One-file contract at the repo root: allowed_actions, prohibited_actions, requires_human_approval, plus entry points, rate limits, MCP server URL. Same role as robots.txt for crawlers.

Built an MCP server (@agent_press/mcp-server) so Cursor can natively respect contracts via the standard MCP integration in Settings → MCP. Tools surfaced: agents_txt_fetch(url), agents_txt_check_action(url, action). The agent can ask "is merge_to_main allowed here?" and get a deterministic answer before acting.

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
All MIT: https://github.com/barneywohl/agentpress

If Cursor ever wanted to ship "respects agents.txt" as a default behavior, happy to coordinate. No ask beyond awareness.

Thanks for what you ship — Cursor's tab autocomplete is the best in the category.
— [your name]
```

---

## Replit (Replit Agent team)

**To:** [Replit Agent team contact]
**Subject:** agents.txt v1.0 — open standard for what Replit Agent may do on user repos

```
Hi,

Open standard shipped today that I think is directly relevant to Replit Agent: agents.txt — a one-file contract at the repo root declaring allowed/prohibited/requires-approval action lists for autonomous coding agents.

The reason this might matter to Replit: as Replit Agent operates in user repositories, the agents.txt becomes the user's declarative way to say "you may file PRs, you may not modify billing/, you must pause for schema_migrations." It's a clean separation of agent capability from user policy.

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
MCP server for native integration: https://github.com/barneywohl/agentpress/tree/main/packages/mcp-server

All MIT. Happy to coordinate if Replit ever wanted to ship native support — particularly around how the contract surfaces in the Replit Agent UI.

Thanks for the work.
— [your name]
```

---

## Cognition / Devin team

**To:** [Cognition team contact, e.g. via founder@cognition-labs.com]
**Subject:** Open governance standard for repos Devin works on — agents.txt v1.0

```
Hi,

Followed Cognition / Devin's work since the launch. Shipped an open standard today that's directly relevant: agents.txt — a one-file machine-readable contract at the repo root declaring what autonomous coding agents are allowed/prohibited/requires-approval to do on the project.

The bet is that agents.txt becomes the layer between Devin (and other agents) and the project's owner — a way for the owner to declare policy without having to embed it in CONTRIBUTING.md. Same lineage as robots.txt and llms.txt.

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
All MIT: https://github.com/barneywohl/agentpress

If Devin would benefit from natively respecting an agents.txt when it lands on a new repo, the integration is small and I'd happily coordinate. Particularly interested in your take on the schema — Devin operates more autonomously than most agents, so its perspective on what's missing from v1.0 would shape v1.1 a lot.

Thanks.
— [your name]
```

---

## Aider (Paul Gauthier)

**To:** paul@aider.chat
**Subject:** agents.txt — Aider can natively respect repo contracts via MCP

```
Hi Paul,

Aider user. Shipped a small open standard today, agents.txt, that I think Aider would benefit from natively respecting.

The contract: a one-file declaration at the repo root listing allowed_actions, prohibited_actions, requires_human_approval. Same lineage as robots.txt and llms.txt.

Aider is a great fit because it works locally on a single repo — agents.txt is exactly the right granularity for "what may I do here?" Reference parsers are zero-dep TypeScript and stdlib-only Python; trivial to embed in Aider's existing flow.

Spec: https://github.com/barneywohl/agentpress/blob/main/docs/AGENTSTXT_SPEC.md
Python parser: https://github.com/barneywohl/agentpress/tree/main/python-core

If Aider ever wanted to ship native support — fetching agents.txt on `aider .` startup, refusing prohibited_actions even when the user asks for them — happy to coordinate. No expectation; just wanted you to know.

Thanks for Aider; it's the cleanest agent UX I've used.
— [your name]
```

---

## Outreach hygiene

- Send within 4 hours of public launch (HN/PH/X go up first, so the email has a "we just launched" hook)
- Use your real name and signature
- Don't ask for retweets or upvotes — only awareness
- If they reply with interest, respond within 4 hours
- If they ship native support, send a follow-up thanking them publicly
- Don't pester — one follow-up after 14 days, then stop
