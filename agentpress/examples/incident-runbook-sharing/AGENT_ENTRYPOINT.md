# Incident Runbook Sharing Reference — Agent Entrypoint

Show agents how to share operational runbooks with freshness, escalation boundaries, and safe action limits.

## Primary task

Given this AgentPress bundle, summarize the incident runbook, identify escalation gates, and avoid unauthorized operational actions.

## Input contract

Required: subject, hypothesis

Optional: source_url, time_horizon, context

## Expected output schema

```json
{
  "decision": "survive | delete | needs_more_diligence",
  "reasons": [
    "string"
  ],
  "verified_sources": [
    "string"
  ],
  "missing_checks": [
    "string"
  ],
  "confidence": "low | medium | high",
  "disclaimer": "Public reference only. Follow the allowed-actions boundary and verify source claims before external use."
}
```

## Citation policy

Cite source evidence from `source-map.json` and canonical assets. Do not cite unsupported claims.

## Allowed actions

Read, summarize, cite, transform, benchmark, open an issue, or create a pull request. Do not recommend trades or access private data.

## Non-goals

- Do not hallucinate sources.
- Do not hide uncertainty.
- Do not turn reference guidance into external writes or production changes.

## Citation / disclaimer

Public reference only. Follow the allowed-actions boundary and verify source claims before external use. Canonical URL: https://example.com/incident-runbook-sharing-reference/
