# Korea Research Map — Agent Verification Suite

Source article: https://barneywohl.substack.com/p/the-korea-research-map-where-cheap
Repo: https://github.com/barneywohl/agentpress
Framing: research commentary only; not investment advice.

## Purpose

This suite tests whether an AI equity-research agent can delete weak Korean equity ideas instead of merely summarizing low-multiple screens.

## Required agent behavior

A passing agent must:

1. Identify the exact listed entity and ticker before analyzing any theme.
2. Use KRX/KIND for listing identity and disclosure trail checks.
3. Use DART for filings, segment economics, related-party disclosures, debt, cash, and minority-shareholder leakage.
4. Separate theme exposure from revenue/profit exposure.
5. Check live liquidity/access separately from static market-cap or ADV summaries.
6. Preserve uncertainty and produce a deletion log.
7. Avoid treating this repository or the Substack article as investment advice.

## Benchmark prompts

### Prompt 1 — Cheap-screen deletion

You are evaluating a Korean equity that screens at low P/B with apparent net cash. Build a deletion-first research memo. Before discussing upside, list the exact checks that could invalidate the idea: ticker/entity mismatch, trapped cash, cross-holdings, related-party economics, asset staleness, liquidity, governance, and catalyst failure. Cite KRX/KIND and DART as required sources. End with a verdict: delete, watchlist, or survivor candidate.

### Prompt 2 — Theme-versus-entity mismatch

A user claims a Korean small cap is a nuclear, robotics, defense, space, or biotech winner because it appears in a theme screen. Do not accept the theme label. Design a verification workflow that maps theme claims to actual revenue, backlog, margins, filings, customer concentration, dilution risk, liquidity, and shareholder access. Produce a deletion log and identify what evidence would move the name from story stock to research survivor.

### Prompt 3 — Survivor-stack challenge

Using only research-process reasoning, explain why a narrow survivor stack can be higher quality than a broad Korea Value-Up or low-P/B basket. Reference Poongsan 103140, BHI 083650, and Woojin 105840 as examples from the article, but do not issue a buy recommendation. State what further work could still kill each idea.

### Prompt 4 — Moonshot drawer kill test

Analyze one moonshot prompt from the repo, such as Innospace 462350, Mobiis 250060, CellBion 308430, IntoCell 287840, or SBB Tech 389500. Treat it as a research prompt only. Build the fastest path to falsification using DART filings, KRX/KIND identity, cash runway, dilution, theme-to-P&L mapping, liquidity, and governance checks.

## Scoring rubric

| Dimension | Pass signal | Fail signal |
|---|---|---|
| Entity verification | Names KRX/KIND/DART and separates listed entity from theme | Treats ticker screen as truth |
| Deletion discipline | Produces explicit kill criteria and deletion log | Only lists upside catalysts |
| Minority-shareholder lens | Checks trapped cash, related parties, access, float, catalyst path | Assumes value accrues to minorities |
| Liquidity realism | Demands live broker/depth/spread check | Relies only on stale ADV/market cap |
| Framing | Research-only, not investment advice | Gives buy/sell advice |

## Expected output format for agents

```yaml
entity_check:
  ticker:
  exchange_identity_source: KRX/KIND required
  filing_source: DART required
theme_claim:
  claimed_theme:
  evidence_required:
deletion_log:
  - risk:
    evidence_to_kill_or_clear:
liquidity_access:
  required_live_checks:
minority_shareholder_path:
  trapped_cash_related_party_catalyst_notes:
verdict: delete | watchlist | survivor_candidate
not_investment_advice: true
```
