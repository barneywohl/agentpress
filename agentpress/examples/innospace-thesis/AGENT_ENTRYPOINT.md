# Innospace 462350 Launch Cadence Dilution Thesis — Agent Entrypoint

Agent-native wrapper for the Innospace 462350 ticker-first Korea thesis, focused on launch cadence, contract materiality, cash runway, dilution risk, and KRX/KIND/DART verification.

## Primary task

Evaluate whether the Innospace 462350 thesis survives source-grounded diligence using the KRX/KIND/DART verification spine, kill tests, and explicit missing-check reporting.

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
  "disclaimer": "Research commentary only. Not investment advice."
}
```

## Citation policy

Cite source evidence from `source-map.json` and canonical assets. Do not cite unsupported claims.

## Allowed actions

Read, summarize, cite, transform, benchmark, open an issue, or create a pull request. Do not recommend trades or access private data.

## Non-goals

- Do not hallucinate sources.
- Do not hide uncertainty.
- Do not turn research commentary into investment advice.

## Citation / disclaimer

Research commentary only. Not investment advice. Canonical URL: https://barneywohl.github.io/agentpress/agentpress/examples/innospace-thesis/
