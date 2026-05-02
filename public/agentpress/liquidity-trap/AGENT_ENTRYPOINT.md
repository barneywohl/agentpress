# Korea Liquidity Trap Agent Benchmark — Agent Entrypoint

Benchmark for testing whether stock-research agents catch Korean small-cap float, spread, depth, and executable-size failures before presenting a thesis.

## Primary task

Given a Korean equity idea, verify liquidity/access constraints and decide whether the idea survives, should be deleted, or needs more live market diligence.

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

Research commentary only. Not investment advice. Canonical URL: https://barneywohl.github.io/agentpress/agentpress/examples/liquidity-trap/
