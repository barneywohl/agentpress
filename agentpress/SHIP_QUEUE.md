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
| AP-006 | SHIPPED | Riley/Barney | `doctor --json` exists and passes; docs include doctor gate. |

## Active next ships

| ID | Priority | Owner lane | Patch target | Acceptance gate |
|---|---:|---|---|---|
| AP-007 | P0 | Maya | Make `agentpress/feedback/` a real feedback loop: response template, scoring rubric, and issue/PR text for outside agents. | Example feedback validates against schema; README tells agent exactly what to return. |
| AP-008 | P0 | Atlas | External-agent first-contact audit: crawl live site using only public URLs and produce patch list from actual first contact. | Evidence file cites URLs fetched and top 5 concrete fixes. |
| AP-009 | P0 | Aria | Consolidate machine contract docs: ensure `AGENT_START_HERE`, `llms.txt`, `agent-instructions.json`, README, schema index, and fetch CLI do not drift. | Grep/doc consistency check plus validation gates. |
| AP-010 | SHIPPED | Barney/Charlie offload | Add CI smoke gate for `doctor`, `schema`, `verify`, and `fetch --base file://$PWD`; live deploy required after commit. | GitHub Actions fail if machine bootstrap/verify regress. |
| AP-011 | P1 | Theo | Add concise `agentpress/schemas/README.md` examples for each schema and CLI command. | Docs include exact command + expected JSON keys. |
| AP-012 | P1 | Kai | Adversarial bundle validation: intentionally broken sample or documented negative tests. | `verify` fails closed for missing/invalid contract fields. |

## Deploy requirement

A row is not done until it is committed, pushed to the Barney-owned AgentPress repo, GitHub Actions pass, Pages deploy succeeds, and the changed live URL returns 200. Local-only patches are `READY`, not `SHIPPED`.

## Global attention needs shipped from GLM review

| ID | Status | Feature | Evidence |
|---|---|---|---|
| GA-001 | SHIPPED | Localized llms routing files + locale index | `locales/llms.*.txt`, `locales/locale-index.json` |
| GA-002 | SHIPPED | Concrete feedback loop templates/rubric/submission docs | `agentpress/feedback/feedback-response-template.json`, `scoring-rubric.json`, templates |
| GA-003 | SHIPPED | Discovery manifest malformed key cleanup | `.well-known/agentpress.json` profile/schema URLs normalized |

## Real platform utility built locally

| AP-027 | SHIPPED | Agent landing receipts | `landing-receipt`, `landing-index`; privacy-safe opt-in proof that agents discovered/used AgentPress, enabling honest adoption measurement without hidden tracking. |

| AP-026 | SHIPPED | Static inbox compiler | `inbox-compile`; turns static agent comms state into `index.html`, `inbox-index.json`, and `inbox-messages.jsonl` for agent/human queue inspection without backend. |

| AP-025 | SHIPPED | Bundle diff and upgrade-check | `bundle-diff`, `upgrade-check`; agents can detect file/contract/freshness/action-boundary drift before trusting new bundle versions. |

| AP-024 | READY | Agent CLI adapter quickstarts | `adapter-quickstart` + `adapter-quickstart-check`; generates Codex/Claude/Gemini/GLM/browser entrypoints, configs, tool manifests, and self-test scripts. Local only pending directive keyword for deploy. |

| AP-023 | SHIPPED | Handoff and receipt proof for agent delegation | `handoff-create/validate`, `receipt-create/validate`; traceable context transfer and completion evidence for agent-to-agent work. |

| AP-022 | SHIPPED | Static inbox/outbox communication lifecycle | `message inbox-init/register/send/broadcast/inbox-check/claim/complete/agents`; agents can coordinate offline through static JSON directories. |

| AP-021 | READY | Static tool discovery manifest for agent attention | `tools-manifest` + `tools-manifest-check`; exposes AgentPress executable CLI primitives as tool-like static JSON so agents can discover/call them. Local only pending directive keyword for deploy. |

| AP-020 | READY | Offline package verification and package index | `package`, `package-verify`, `package-index`; agents can fetch one tarball, verify SHA256 manifest, and work offline. Local only pending directive keyword for deploy. |

| AP-019 | READY | Privacy-safe team capability packs | `agentpress.py team-pack` + `team-pack-validate`; public-source/explicit-consent only, redaction by default, capability/handoff context for agents. Local only pending directive keyword for deploy. |

| AP-018 | READY | Agent self-test runner and reputation proof JSONL | `agentpress.py self-test --agent-id ID --out results.jsonl`; standard suite proves verify/search/message/bundle/fail-closed capability; CI gate added. Local only pending directive keyword for deploy. |

| AP-017 | SHIPPED | AgentPress searchable asset/capability index | `agentpress.py index-search`, `agentpress.py search QUERY`; publishes `agentpress/search/search-index.json`; CI gated for message/bundle/fail-closed queries. |

| AP-016 | SHIPPED | Docs/API folder to valid AgentPress bundle generator | `agentpress.py bundle SOURCE --out OUT`; copies source docs and generates entrypoint/task-card/source-map/freshness/allowed-actions/llms/sitemap/ingestion/eval; CI gated. |

| ID | Status | Feature | Evidence |
|---|---|---|---|

| AP-015 | READY | Executable agent communication CLI | `agentpress.py message create-request/route/create-response/thread-*`; validates static request/response/thread JSON for local-first agent coordination. Built/tested locally; deploy blocked until directive keyword. |

## Missing feature backlog

| ID | Priority | Feature | Why it matters |
|---|---:|---|---|
| AP-013 | P1 | Offline package publishing and documented SHA256 manifest | Restricted-network agents need a single artifact they can fetch once and verify locally. CLI exists; publish/link package artifact next. |
| AP-014 | SHIPPED | Negative/adversarial validation fixtures | `agentpress/fixtures/broken-bundles/` + `agentpress.py negative-fixtures --json`; CI fails if broken bundles do not fail closed. |
| AP-015 | P2 | Public release/changelog feed | Agents need to detect what changed between AgentPress contract versions. |
| AP-016 | P2 | Language/runtime-specific quickstarts | Gemini/Claude/Codex/browser/RAG agents should each have one exact minimal run path. |

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
