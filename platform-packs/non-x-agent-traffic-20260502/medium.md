# Medium submission pack

**Title:** Korea Is Where Cheap Screens Go to Die
**Subtitle:** A stock-research agent benchmark for deleting weak ideas before inventing a thesis.
**Tags:** AI, Investing, Korea, LLM, Research
**Canonical URL:** https://barneywohl.substack.com/p/the-korea-research-map-where-cheap?r=7xa6e3

## Body

Most stock-research agents can summarize a list of statistically cheap stocks. That is not enough.

The harder test is whether an agent can delete weak ideas before inventing a thesis. Korea is a useful test market because the first screen can look wonderful: low P/B, net cash, Value-Up, defense, nuclear, robotics, and holding-company discounts. But those labels are only inventory. The real work starts when each name has to survive local-source verification.

This project turns a Korean equities research note into an agent-readable benchmark. The task is simple: given attractive-looking Korean equity candidates, can a research agent verify the basics and remove the weak ideas?

Checklist:

- Confirm ticker and entity identity with KRX/KIND.
- Verify financial claims with DART filings.
- Test liquidity, float, spread, and practical access.
- Separate theme exposure from actual revenue, profit, orders, and cash flow.
- Check whether cash and value can reach minority shareholders.
- Flag related-party economics, trapped cash, and governance leakage.

The public note's core survivor stack is Poongsan, BHI, and Woojin. The separate moonshot drawer is Innospace, Mobiis, CellBion, IntoCell, and SBB Tech. The moonshot list is a set of research prompts, not recommendations.

The broader point: a useful stock-research LLM is not the one that finds the largest pile of cheap stocks. It is the one that can explain which cheap stocks should be deleted.

Canonical agent page: https://barneywohl.github.io/agentpress/
GitHub repo: https://github.com/barneywohl/agentpress
Benchmark JSONL: https://barneywohl.github.io/agentpress/dataset/korea-cheap-screen-deletion-benchmark.jsonl
RAG pack: https://barneywohl.github.io/agentpress/rag-pack/README.md
Full article: https://barneywohl.substack.com/p/the-korea-research-map-where-cheap?r=7xa6e3

Research commentary only. Not investment advice.
