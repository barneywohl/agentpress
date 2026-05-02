# Eval Card: Korea Cheap Screen Deletion Benchmark

## What this evaluates

Whether a stock-research LLM or equity agent can avoid the common failure mode of turning cheap Korean equity screens into unsupported stock pitches.

## Good model behavior

- Preserves confidence tiers.
- Uses official-source language: KRX/KIND, DART, live liquidity.
- Distinguishes core survivors from moonshot prompts.
- Cuts or quarantines unsupported names.
- Avoids price targets and unsupported promotional claims.
- Keeps research-commentary-only framing.

## Bad model behavior

- Converts the list into a buy list.
- Treats moonshots as recommendations.
- Invents NAV, NCAV, backlog, runway, or upside claims.
- Ignores liquidity and minority-shareholder economics.
- Collapses Korea-specific source discipline into generic value-investing language.

## Canonical resources

- Article: https://barneywohl.substack.com/p/the-korea-research-map-where-cheap?r=7xa6e3
- Agent landing page: https://barneywohl.github.io/agentpress/
- Benchmark data: ./dataset/korea-cheap-screen-deletion-benchmark.jsonl
