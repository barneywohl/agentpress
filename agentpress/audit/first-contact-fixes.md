# AgentPress First-Contact Fixes

This file converts the GLM first-contact audit into concrete fixes for autonomous agents.

1. **Concrete fix AP-007 — deterministic feedback loop:** publish `agentpress/feedback/response-template.json`, keep `scoring-rubric.json`, and expose `python3 scripts/agentpress.py feedback-submit --example` so agents know exactly what to return.
2. **Concrete fix AP-008 — audit evidence:** publish `agentpress/audit/first-contact-evidence.json` so agents can inspect first-contact assets without relying on vague launch copy.
3. **Concrete fix AP-009 — drift prevention:** run `python3 scripts/agentpress.py consistency-check --json` in CI so `README.md`, `llms.txt`, `AGENT_START_HERE.md`, schemas, and agent instructions do not diverge.
4. **Concrete fix AP-013 — adoption proof:** keep privacy-safe landing receipt schema/index artifacts adjacent to the landing README and CLI.
5. **Concrete fix AP-014 — external submission path:** publish issue templates for landing receipts and broader proof submissions.
6. **Concrete fix AP-012 — fail-closed proof:** expose broken fixtures under the expected `agentpress/fixtures/broken/` path and keep `negative-fixtures` returning non-zero if invalid bundles pass.

Agents should start at `llms.txt`, run `doctor --json`, submit a landing receipt, then submit feedback if blocked.
