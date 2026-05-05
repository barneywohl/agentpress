# AgentPress agent needs / painpoint build list — 2026-05-05

Scope: AgentPress only. Inputs: npm/PyPI live registry verification, Maya/Jordan team audits for mission `mission-20260505-155310-6cf4fa`, public agent-builder painpoint work, rc4 proof receipts, and current repo gates.

## Is npm being done correctly?
Yes for the rc lane.

Evidence:
- Package: `@agent_press/agentpress@0.2.0-rc.4`.
- `dist-tags`: `rc=0.2.0-rc.4`, `latest=0.1.0` intentionally unchanged.
- CLI bin: `agentpress -> bin/agentpress.js`.
- Pack contents: 93 files, ~292KB tarball, includes `bin/agentpress.js`, `scripts/agentpress.py`, and `agentpress/tools/agentpress-tools.json`.
- Clean npm smoke: `npx -y @agent_press/agentpress@rc doctor . --mode online --json` passed.
- Clean PyPI smoke: fresh venv + `agentpress-static==0.2.0rc4` + `agentpress doctor` passed.

## What agents have now
- Install lanes: npm rc, PyPI rc, GitHub source, static Pages.
- First-run lanes: `start`, `doctor`, `first-run-wizard`, `fetch`, `bundle`, `verify`, `self-test`.
- Safety gates: `safety-preflight`, secret guard in `doctor`, `broker-scope-guard`, `redaction-check`, permission/consent tools.
- Tool contract gates: `tool-contract-check`, `tool-output-sample-generate`, schema serialization/vocabulary checks.
- Proof/adoption: `external-proof-run`, landing receipts, submission packs, proof ingest/review, reputation/scoreboard.
- Runtime coverage: compatibility matrix for Codex, Claude, Gemini, GLM, browser, RAG.
- Community/painpoint surfaces: community issue radar, attention radar, current agent places map, unsolved backlog, connector/security scanners.

## Still needed / next build backlog

### P1 — Independent external proof receipts
Current proof is self-run/public smoke, not a true outside-agent adoption receipt.
Build: opt-in proof request + review loop for Cline/Roo/OpenHands/LangChain/LlamaIndex/MCP users without spam or secrets.
Acceptance: at least one independent proof/blocker receipt ingested and reviewed.

### P1 — Native integration packs where agents already work
Build dedicated quickstart/config packs for:
- Cline / Roo Code
- OpenHands
- Claude Code / Codex CLI / Gemini CLI / GLM
- LangGraph/LangChain tool schema users
- LlamaIndex/RAG document/tool users
- MCP servers/clients
Acceptance: each pack has install command, config snippet, safety policy, proof command, and common failure remediation.

### P1 — First-run no-Python fallback UX
npm shim still depends on Python being present. It is acceptable for rc, but agents need excellent failure output.
Build: missing/old Python JSON remediation path and/or JS-only bootstrap fetch path.
Acceptance: `npx @agent_press/agentpress@rc doctor --json` in missing-Python simulation emits exact install/fix steps.

### P1 — Context package init / handoff-root picker
Agents get lost when repo roots are huge.
Build: `context-package init` and/or `handoff-root pick` to generate `source-map.json`, `freshness.json`, and compact task-card roots.
Acceptance: strict `context-budget` passes on generated focused roots.

### P1 — Continuous broker/fanout scope guard
Repo CLI guard exists, but mission/fanout creation should call the guard automatically.
Build: integrate `broker-scope-guard` into Mission Engine/team fanout for AgentPress tasks.
Acceptance: fixture with Korea/value-hunter root is rejected or stripped before queueing.

### P2 — Tool output samples in CI
`tool-output-sample-generate` exists now. Next: wire sample generation/validation into CI and docs.
Acceptance: CI validates sample fixtures against `tool-contract-check`.

### P2 — Package channel promotion checklist
rc is correct; `latest` should only move after independent proof + RFLO review.
Build: `release-promote-checklist --from rc --to latest`.
Acceptance: machine checklist blocks if independent proof, smoke, CI, and package diff are missing.

## Painpoints we can solve next
1. “I don’t know which install lane to use” → native integration packs + smoke-install receipts.
2. “Tool schema/provider mismatch breaks runs” → tool contract + sample generation + provider packs.
3. “Huge repos blow context” → context package init / handoff root picker.
4. “I can’t trust proof/adoption claims” → independent proof ingestion/review.
5. “Agent task queues inherit stale roots” → broker-scope guard integrated into fanout/mission creation.
6. “npx fails if Python is missing” → no-Python remediation/JS bootstrap.

## Build shipped in this batch
- `tool-output-sample-generate`: creates structuredContent sample fixtures from tool output schemas.
- `smoke-install`: first-class npm/PyPI clean install smoke receipt command.
- `repo-sync-doctor`: catches stale/dirty local checkouts before agents judge release truth.
- Tool manifest now advertises those commands.
