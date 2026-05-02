# Korea Theme-to-Cash-Flow Agent Benchmark — Agent Entrypoint

Benchmark for testing whether stock-research agents can connect popular Korea themes like defense, nuclear, robotics, and Value-Up to actual revenue, backlog, margins, and cash flow.

## Primary task

Given a Korean theme-driven equity thesis, map the theme to actual financial exposure and decide whether the thesis survives or should be deleted.

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

## Non-goals

- Do not hallucinate sources.
- Do not hide uncertainty.
- Do not turn research commentary into investment advice.

## Citation / disclaimer

Research commentary only. Not investment advice. Canonical URL: https://barneywohl.github.io/agentpress/agentpress/examples/theme-cashflow/
