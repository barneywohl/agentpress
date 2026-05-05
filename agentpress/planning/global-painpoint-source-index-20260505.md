# AgentPress Global Painpoint Source Index - 2026-05-05

Mission: `mission-20260505-133622-52df70`
Repo: `/tmp/agentpress-publish-commit`
Baseline pushed head: `ae72206 feat: target AgentPress agent pain points`

## Sources Read

- `/Volumes/X10/clawd/ops/state/agent_messages.jsonl`
  - Active global build loop assigned P0 review/build tasks for `mission-20260505-133622-52df70`.
  - The next-loop tasks explicitly call for remaining P0/P1 features after `ae72206+`.
- `/Volumes/X10/clawd/ops/state/task_queue.json`
  - Confirms the global painpoint loop, review focus areas, required evidence path, and no-secrets/no-Nexio-prod scope.
- `/Volumes/X10/clawd/shared/status/mission-20260505-133622-52df70_ruflo_opus_1.txt`
  - Read-only RFLO synthesis maps current P0/P1 gaps to concrete commands.
  - Remaining P1 build list: `safety-preflight`, `context-budget`, `mcp-config-doctor`, provider error/handoff improvements, live compatibility proof.
- `/Volumes/X10/clawd/shared/status/agentpress_painpoints_feature_ship_20260505.md`
  - Prior local sprint shipped `painpoint-map`, first-action guidance, channel clarity, handoff evidence hashing, and sensitive evidence refusal.
- `/Volumes/X10/clawd/shared/status/agentpress_feature_build_ship_20260505_codex.md`
  - Earlier first-run fast path evidence, including the safety and proof loop that informed the current backlog.
- Current repo status
  - `agentpress-site` HEAD is `ae72206`.
  - GitHub remote `agentpress` points to `https://github.com/barneywohl/agentpress.git`.
  - Existing CLI has building blocks for secret preflight, redaction, tool-file access scanning, sandbox guard, provider error explanation, and handoff contracts.

## P0/P1 Build Backlog

1. `safety-preflight` - umbrella command over secret-permission preflight, redaction guidance, tool file-access risk scanner, sandbox/sensitive-path status. Must not read secrets.
2. `context-budget` - static context bloat gate with file counts, bytes, source-map requirement, freshness hints, max file/char budgets, and exact remediation.
3. `mcp-config-doctor` - static MCP config checker for JSON shape, server count, duplicate names, dangerous env value markers, and backup/restore guidance. Must not mutate config.
4. `provider-error-explainer` - quick polish only if low-risk: point context and permission failures at the new umbrella gates.

## Acceptance Gates

- Unit tests for every new command.
- Tool registry/docs surfaces updated.
- Required local gates: `python3 -m pytest -q`, `npm test`, `npm run validate`, docs command check, schema validate all, npm pack dry-run, `git diff --check`.
- Push the resulting commit to `barneywohl/agentpress` branches `main` and `agentpress-site`.
- Do not publish npm/PyPI unless an rc4 bump and safe auth are completed; otherwise record publish as blocked/pending.
