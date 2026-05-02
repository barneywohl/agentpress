# KB-FINRATE Korean Bank NIM Compression Thesis — Agent Entrypoint

Ticker/thesis-led AgentPress article for Korean bank net-interest-margin compression under a BOK rate-cut transmission scenario. Research commentary only; not investment advice.

## Primary task

Verify whether KB/Shinhan/Hana funding mix, BOK rate path, and NIM disclosures support or kill the Korean bank NIM compression thesis.

## Ticker / thesis frame

- Ticker proxy: `KB-FINRATE`
- Companies to compare: KB Financial, Shinhan Financial Group, Hana Financial Group
- Thesis: BOK easing creates Korean bank NIM compression if deposit repricing runs ahead of loan yield recovery.

## What must be true

1. BOK cuts the policy/base rate by at least `25 bps` within 6 months.
2. Time-deposit / rate-sensitive funding is large enough to transmit repricing.
3. Loan-yield repricing lags deposit-cost repricing for two or more quarters.
4. Fee income and credit-cost changes do not offset the margin pressure.

## Kill tests

- BOK holds/raises for two quarters.
- NIM is flat/up in quarterly filings after rate-cut transmission.
- Funding mix/deposit beta evidence contradicts the thesis.
- Offset income/credit-cost improvements dominate NIM pressure.

## Input contract

Required: ticker, thesis, source_urls

Optional: source_url, time_horizon, context

## Expected output schema

```json
{
  "decision": "survive | delete | needs_more_diligence",
  "reasons": ["string"],
  "verified_sources": ["string"],
  "missing_checks": ["string"],
  "kill_tests_triggered": ["string"],
  "confidence": "low | medium | high",
  "disclaimer": "Research commentary only. Not investment advice."
}
```

## Citation policy

Cite source evidence from `source-map.json` and primary company/regulator disclosures. Do not cite unsupported claims.

## Allowed actions

Read, summarize, cite, transform, benchmark, open an issue, or create a pull request. Do not recommend trades or access private data.

## Non-goals

- Do not issue a buy/sell/hold recommendation.
- Do not hallucinate BOK/FSS/company filings.
- Do not hide missing checks.
- Do not treat the thesis as investment advice.

## Citation / disclaimer

Research commentary only. Not investment advice. Canonical URL: https://barneywohl.github.io/agentpress/agentpress/examples/kb-finrate/
