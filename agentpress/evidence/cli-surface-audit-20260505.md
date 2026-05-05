# AgentPress CLI surface audit — 2026-05-05

Result: no parser/dispatch/docs/tool-manifest drift found after adding `cli-gap-audit`.

## Verified gates
- `docs-command-check`: ok.
- `tools-manifest-check`: ok.
- `tool-contract-check --strict`: ok, 214 tools, 0 fails, 0 warnings.
- Parser vs dispatcher audit: 277 parser commands, no parser without dispatch, no true dispatch without parser.
- `browser-smoke`: ok, 10 checked, 0 failed.
- `freshness-citation-report`: ok.
- Tests: 245 passed.
- `npm run validate`: ok.

## Built in this audit
- `cli-gap-audit`: machine-readable command surface drift audit covering parser, dispatcher, docs command check, tools manifest, and tool contract check.
- Added regression test `tests/test_cli_gap_audit.py`.

## Still intentionally not solved by CLI alone
- Independent third-party proof/adoption receipts require outside agents/operators; do not fabricate.
- `latest` promotion should remain blocked until independent proof + RFLO review + green CI/package smokes.
- Context-package init / handoff-root picker remains the top new CLI build candidate.
- Native integration packs for Cline/Roo/OpenHands/LangChain/LlamaIndex/MCP remain the top ecosystem build candidate.
