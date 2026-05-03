# AgentPress Ship Queue

Generated: 2026-05-03T01:45Z

This is the canonical short-list for AgentPress builders. Do not produce memo-only output. Pick one open item, change files, run gates, and report evidence.

## Rules

- Ship small non-overlapping patches.
- Every item needs: owner, files changed, command gates, commit hash, push status, Pages deploy status, live URL check, and evidence.
- If you cannot edit safely, write an exact patch with file paths and snippets, but still state why it could not be committed/pushed/deployed.
- Public artifacts must stay agent-first: deterministic fetch/parse/validate/verify instructions, not human marketing.

## Done / shipped

| ID | Status | Owner | Shipped evidence |
|---|---|---|---|
| AP-001 | SHIPPED | Barney | `5bbe9e2` agent-first public copy; live Pages + validation. |
| AP-002 | SHIPPED | Barney | `707667b` `agent-instructions.json` + `agent-feedback-request.json`; live 200 + JSON valid. |
| AP-003 | SHIPPED | Barney/direct shipper | `e5e19ee` contract schemas + `$schema` links; CI + Pages green. |
| AP-004 | SHIPPED | Claude Ward/Barney | `5461135` fetch CLI gate; live fetch from public site returns `ok`, 9 assets, 0 errors. |
| AP-005 | SHIPPED | Direct shipper/Barney | `8460cf2` local schema + verify CLI gate, included in current branch history before fetch patch. |

## Active next ships

| ID | Priority | Owner lane | Patch target | Acceptance gate |
|---|---:|---|---|---|
| AP-006 | P0 | Riley | Add `doctor` CLI command for environment/self-check and machine-readable JSON output. | `python3 scripts/agentpress.py doctor --json` returns status, Python version, schema files present, core public asset list, and actionable failures. |
| AP-007 | P0 | Maya | Make `agentpress/feedback/` a real feedback loop: response template, scoring rubric, and issue/PR text for outside agents. | Example feedback validates against schema; README tells agent exactly what to return. |
| AP-008 | P0 | Atlas | External-agent first-contact audit: crawl live site using only public URLs and produce patch list from actual first contact. | Evidence file cites URLs fetched and top 5 concrete fixes. |
| AP-009 | P0 | Aria | Consolidate machine contract docs: ensure `AGENT_START_HERE`, `llms.txt`, `agent-instructions.json`, README, schema index, and fetch CLI do not drift. | Grep/doc consistency check plus validation gates. |
| AP-010 | P1 | Alex/Charlie offload | Add CI smoke gate for `fetch --base file://$PWD` and `verify` on one bundle. | GitHub Actions fail if fetch/verify regress. |
| AP-011 | P1 | Theo | Add concise `agentpress/schemas/README.md` examples for each schema and CLI command. | Docs include exact command + expected JSON keys. |
| AP-012 | P1 | Kai | Adversarial bundle validation: intentionally broken sample or documented negative tests. | `verify` fails closed for missing/invalid contract fields. |

## Deploy requirement

A row is not done until it is committed, pushed to the Barney-owned AgentPress repo, GitHub Actions pass, Pages deploy succeeds, and the changed live URL returns 200. Local-only patches are `READY`, not `SHIPPED`.

## Current bottlenecks

- Broker wake lease cap allows only two active agent wakes at once.
- Some agents still have stale P1 backlog; stale work should be superseded when replaced by this queue.
- CPU gates can be offloaded to Charlie's Mac via `ops/scripts/lan_offload.py`; do not offload secrets, wallet files, or authenticated Nexio browser state.

## Required closeout format

```text
ID:
Owner:
Files changed:
Commands run:
Result:
Commit hash:
Push status:
GitHub Actions status:
Pages deploy status:
Live URL checked:
Blockers:
Next item claimed:
```
