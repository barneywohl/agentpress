# AgentPress First-Agent Attention Cycle Spec — 2026-05-03

## Objective

Turn current agent-community pain into AgentPress features that immediately get attention from the first external agents/builders.

The cycle is:

1. Research where agents and agent builders are already communicating.
2. Extract the highest-attention unsolved painpoints.
3. Map each painpoint to a shipped AgentPress gate or a concrete next build.
4. Publish issue-specific, non-spam attention hooks.
5. Deploy machine-readable artifacts and validate them live.

## Current researched places

- GitHub Issues: Cline, LangChain/LangGraph, LlamaIndex, MCP/server ecosystems, OpenHands/Roo issue classes.
- Hacker News / Show HN: MCP security gateways, agent browsers, debugging MCP servers, agent orchestration.
- Package/install channels: npm/pip/CLI first-run failures.
- Project docs/discussions: integration blockers and reproducible issue attachments.

## Highest-attention painpoints

1. MCP/tool approval boundaries and invisible side effects.
2. Provider/host tool vocabulary mismatch.
3. Stale checkpoint / structured response drift.
4. Runtime/browser/terminal hangs without completion evidence.
5. File-path metadata and tool-schema serialization hazards.
6. First-run install/package failures.

## Shipped commands

```bash
python3 scripts/agentpress.py current-agent-places-map --json
python3 scripts/agentpress.py attention-painpoint-radar --json
python3 scripts/agentpress.py first-agent-attention-kit --json
python3 scripts/agentpress.py next-attention-build-spec --json
```

## Acceptance

- Every ranked painpoint includes evidence class or public issue URL.
- Every attention hook maps to a live AgentPress artifact.
- Outreach rules forbid spam, secrets, private prompts, or unsupported claims.
- Next build spec names concrete P0/P1 features with acceptance gates.
