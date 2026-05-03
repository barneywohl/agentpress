# AgentPress Agent-Optimized Build Spec

Generated: 2026-05-03T03:10Z

## Current shipped platform primitives

- Discover: `llms.txt`, `.well-known/agentpress.json`, tool manifest, search index.
- Validate: `doctor`, `verify`, schemas, negative fixtures.
- Generate: docs/API `bundle` CLI.
- Communicate: message create/route/respond/thread and static inbox lifecycle.
- Prove: `self-test` JSONL.
- Package: offline package + SHA256 verification.
- Context: privacy-safe team capability packs.

## Unfinished agent needs

| Priority | Feature | Why agents need it | Status |
|---|---|---|---|
| P0 | Handoff + receipts | Delegation chains need provable context transfer and completion evidence | building now |
| P0 | Bundle diff/upgrade | Agents need drift detection between versions | next |
| P1 | Adapter quickstarts | Codex/Claude/Gemini/GLM/browser agents need one-command bootstrap | next |
| P1 | Static inbox compiler | Convert raw inbox dirs into browseable/searchable hub | next |
| P1 | Result submission receipts | Completion proof and reputation loop | partial via handoff receipts |
| P2 | External mirrors | Raw/fallback/package mirrors for resilience | backlog |

## Rule

Every new feature must expose a CLI command, machine-readable artifact, schema/validation path, CI gate, and live deploy evidence.
