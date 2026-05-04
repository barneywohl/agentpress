# AgentPress Deep Complaints Build Cycle — 2026-05-04

## Research result
Public scan sample: 48 accessible issue/story signals. Top complaint categories: market_discussion, tool_call_schema_mismatch, approval_consent_security, provider_model_compat, file_path_data_safety, state_checkpoint_memory.

## What agents are missing
- Issue-to-repro packs for tool/provider/schema failures.
- MCP config mutation guard with backup/diff/restore proof.
- Approval evidence for risky tools.
- Checkpoint replay attachments for stale state.
- Runtime hang timelines.
- First-run package/install fallback.

## Built locally in this cycle
- `agentpress/community/deep-agent-complaint-frequency.json`
- `agentpress/community/live-community-recheck-runner.json`
- `agentpress/community/live-missing-capabilities-radar.json`
- `agentpress/repro/issue-to-repro-pack.json`
- `agentpress/security/mcp-config-mutation-guard.json`
- `agentpress/outreach/manual-outreach-approval-queue.json`
- `agentpress/proof/reply-receipt-ingest-examples.json`
- `agentpress/specs/deep-complaints-build-cycle-spec.json`

## Deploy gate
External deploy/push requires Jake directive keyword from Telegram.
