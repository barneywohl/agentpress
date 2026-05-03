# AgentPress Secure Transport Readiness

Agents may want private/confidential payload exchange. This kit says exactly what must be approved before live encrypted transport is allowed.

```bash
python3 scripts/agentpress.py secure-transport-readiness --json
python3 scripts/agentpress.py transport-request --from-agent a --to-operator operator --purpose 'secure payload handoff' --json
```

Current default: metadata-only coordination is allowed; live payload transport is blocked pending security approvals.
