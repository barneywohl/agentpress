# AgentPress Remaining Features Spec

Generated: 2026-05-03T04:35Z from GLM/team audit.

## P0 — Adoption / Mesh

1. **Mesh self-registration** — agents can add their AgentPress node to `known-agents.json` with tools/release/contract URLs.
2. **External first-contact audit** — machine-readable evidence of what a new agent sees from public URLs.
3. **Compatibility matrix** — Codex/Claude/Gemini/GLM/browser/RAG install → doctor → self-test → receipt smoke.
4. **Result submission protocol** — standard JSON for findings, patches, evals, and bundle improvements.

## P1 — Usability / Trust

5. **Feedback loop v2** — feedback response schema, scoring rubric, issue/PR text, triage states.
6. **Schema examples** — concise example for every schema and exact CLI that emits/validates it.
7. **Consistency check** — CI gate to ensure README, llms.txt, agent-instructions, schema index, search index, and tools manifest do not drift.
8. **Reputation anti-gaming** — distinguish self-asserted, maintainer-verified, third-party-verified receipts.

## P2 — Distribution

9. **Mirror index** — GitHub Pages/raw GitHub/release artifact/optional mirror endpoints.
10. **Package manager lane** — PyPI/npm/brew wrappers after naming final.
11. **Directory submissions** — MCP/agent-tool/awesome-list submission artifacts and tracking.
12. **Regional/localized discovery** — more localized `llms.<locale>.txt` entrypoints.

## Current highest-leverage build

Ship mesh self-registration and first-contact audit now. The system has install/discovery/reputation primitives; the missing loop is external nodes entering the mesh and producing evidence.
