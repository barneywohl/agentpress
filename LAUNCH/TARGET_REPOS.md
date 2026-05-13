# 20 target repos for `agents.txt` PRs

Ranked by signal-per-byte. The first 5 are friendly seeds (file day +1). The next 15 are the wider push (file days +2 through +14).

| # | Repo | Owner type | Why | PR difficulty |
|---|---|---|---|---|
| 1 | anthropics/claude-code | AI lab | Direct relevance; high prestige | Medium |
| 2 | anthropics/anthropic-sdk-python | AI lab | Same surface, smaller change | Low |
| 3 | anthropics/anthropic-sdk-typescript | AI lab | Mirror of #2 | Low |
| 4 | modelcontextprotocol/servers | Standards body | MCP cross-link | Medium |
| 5 | AnswerDotAI/llms-txt | Friendly | Lineage courtesy | Low |
| 6 | paul-gauthier/aider | Agent maintainer | Single-maintainer, agent-friendly | Low |
| 7 | continuedev/continue | Agent maintainer | Active community | Low |
| 8 | crewAIInc/crewAI | Framework | Multi-agent angle | Medium |
| 9 | langchain-ai/langgraph | Framework | High traffic | Medium |
| 10 | microsoft/autogen | Framework | Microsoft surface | Medium |
| 11 | e2b-dev/E2B | Sandbox infra | Agent execution focus | Medium |
| 12 | openai/openai-cookbook | AI lab | High visibility, low risk | Medium |
| 13 | openai/openai-agents-python | AI lab | Direct fit | Medium |
| 14 | sourcegraph/cody | Coding agent | Cross-pollination | Medium |
| 15 | vercel/ai | Framework | High dev visibility | Medium |
| 16 | shadcn-ui/ui | Design system | Status badge real estate | Low |
| 17 | tldraw/tldraw | AI-friendly OSS | Visual community | Low |
| 18 | supabase/supabase | High-traffic OSS | Agent-curious org | Medium |
| 19 | replit/agent-protocol | Agent platform | Direct fit | Medium |
| 20 | cursor/cursor-rules | Cursor org | Direct fit | Low |

## How to file

For each repo:

1. Fork the repo: `gh repo fork {owner}/{repo} --clone --remote`
2. Branch: `git checkout -b agents-txt-v1`
3. Copy template: `npx @agent_press/agentpress init` then customize for the repo's actual constraints (don't ship a copy-paste contract; tailor allowed_actions to what makes sense for the project).
4. Open PR with body from `PR_TEMPLATE.md`.
5. Add the registry entry locally; submit as a separate small PR to barneywohl/agentpress's `registry/registry.json` once the upstream PR lands.

## Don't

- Don't file PRs in batch with auto-generated content. Every contract should be hand-tuned for the project. Bot-shaped PRs damage the standard's reputation.
- Don't file in legal repos (e.g. anti-malware projects, security-research repos) without checking with maintainers first — the contract might intersect with their threat model.
- Don't file in archived repos.
- Don't file in personal repos that haven't been touched in 12 months.
- Don't argue if a PR is closed — accept gracefully and try a different repo next.

## Tracking

Maintain a `LAUNCH/PR_TRACKER.md` (created post-launch) with one row per filed PR:
- Date filed
- Repo
- PR URL
- Status (open / merged / closed / no response)
- Days to first response
- Days to merge (if merged)

This data drives the launch metrics report at day 30.
