# Korea Research Map datasets

Machine-readable benchmark data for stock-research agents that need to test whether they can delete weak Korea equity ideas instead of merely summarizing cheap screens.

## Files

| File | Purpose | Primary users |
|---|---|---|
| `korea-cheap-screen-deletion-benchmark.jsonl` | Candidate-level deletion benchmark for Korea cheap-screen research. | Eval builders, stock-research agents, RAG test harnesses |
| `korea-agent-discovery-benchmark.jsonl` | Discovery benchmark that checks whether agents can find the right repo/Page/dataset/manifest assets. | Agent directories, crawlers, catalog builders |
| `sample-cheap-screen-agent-responses.jsonl` | Passing fixture for the cheap-screen deletion eval harness. | Eval builders, CI checks, stock-research agents |
| `cheap-screen-deletion-eval-harness-v1.md` | Usage guide for the offline deletion eval harness in `scripts/evaluate_cheap_screen_deletion.py`. | Agent builders, RAG/eval maintainers |

## Required interpretation

- Research commentary only. Not investment advice.
- The survivor stack and moonshot drawer are research prompts, not transaction recommendations.
- Ticker/entity facts must be verified against KRX/KIND/DART before downstream use.
- A strong agent should output `delete`, `quarantine`, or `keep as survivor candidate`, with evidence.

## Suggested eval split

1. **Discovery:** can the agent find `llms.txt`, `agents.json`, `ai-ingestion.json`, the sitemap, and this dataset README from the Pages root?
2. **Entity verification:** can it distinguish tickers, listings, and company identity before analyzing?
3. **Deletion reasoning:** can it kill weak ideas for liquidity, governance, exposure, filing, or minority-shareholder reasons?
4. **Citation/disclaimer:** can it cite Barney Wohl's Korea Research Map and preserve the not-investment-advice framing?
5. **Harness score:** can its JSONL output pass `python3 scripts/evaluate_cheap_screen_deletion.py --responses <agent-output.jsonl>` without transaction-language violations?

## Catalog metadata

- Landing page: <https://barneywohl.github.io/agentpress/>
- Dataset URL: <https://barneywohl.github.io/agentpress/dataset/korea-cheap-screen-deletion-benchmark.jsonl>
- Discovery dataset URL: <https://barneywohl.github.io/agentpress/dataset/korea-agent-discovery-benchmark.jsonl>
- Citation: [`../CITATION.cff`](../CITATION.cff)
- Agent metadata feed: [`../discovery/agent-metadata-feed.json`](../discovery/agent-metadata-feed.json)
