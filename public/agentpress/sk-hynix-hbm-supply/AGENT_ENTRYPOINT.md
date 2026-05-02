# SK Hynix 000660 HBM Supply Constraint Thesis — Agent Entrypoint

Agent-native diligence wrapper for the SK Hynix HBM supply constraint duration thesis. Research commentary only; not investment advice.

## Primary task

Verify whether SK Hynix HBM backlog, capex, and customer concentration evidence support or kill the HBM supply constraint thesis.

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

Research commentary only. Not investment advice. Canonical URL: https://barneywohl.github.io/agentpress/agentpress/examples/sk-hynix-hbm-supply/
