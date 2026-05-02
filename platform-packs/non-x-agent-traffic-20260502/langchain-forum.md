# LangChain forum submission pack

**Category:** Show and tell / LangGraph agents / RAG evaluation
**Title:** Korea cheap-screen deletion benchmark for stock-research agents

## Body

I built a small public benchmark for testing stock-research agents on deletion quality rather than thesis generation.

Failure mode: agents can summarize cheap-looking public equities, but they often fail to delete weak candidates before inventing a thesis. Korea is a useful non-US test because it requires KRX/KIND identity checks, DART filing verification, liquidity/access checks, minority-shareholder economics, and theme-to-P&L validation.

The benchmark task: given attractive-looking Korean equity candidates, can the agent remove names that fail local-source verification and explain why they were removed?

Useful integration points for LangChain/LangGraph builders:

- Retriever checks for KRX/KIND/DART source coverage.
- Tool-call traces that prove the agent verified entity identity before analysis.
- A deletion rubric that rewards abstention and penalizes unsupported thesis generation.
- RAG pack and JSONL eval rows for regression testing.

Canonical agent page: https://barneywohl.github.io/agentpress/
GitHub repo: https://github.com/barneywohl/agentpress
Benchmark JSONL: https://barneywohl.github.io/agentpress/dataset/korea-cheap-screen-deletion-benchmark.jsonl
RAG pack: https://barneywohl.github.io/agentpress/rag-pack/README.md
Full article: https://barneywohl.substack.com/p/the-korea-research-map-where-cheap?r=7xa6e3

Research commentary only. Not investment advice.

Questions for builders: How would you score deletion quality? Would you reward abstention when filing/liquidity evidence is incomplete?
