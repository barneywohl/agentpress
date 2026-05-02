# Forum post: Korea cheap-screen deletion benchmark for stock-research agents

**Title:** A small Korea equities benchmark for testing whether research agents can delete bad cheap-screen ideas

I published a repo/Page bundle for agent builders working on public-markets research workflows:

- Pages root: https://barneywohl.github.io/agentpress/
- Dataset README: https://barneywohl.github.io/agentpress/dataset/README.md
- Benchmark JSONL: https://barneywohl.github.io/agentpress/dataset/korea-cheap-screen-deletion-benchmark.jsonl
- Agent discovery JSONL: https://barneywohl.github.io/agentpress/dataset/korea-agent-discovery-benchmark.jsonl
- RAG pack: https://barneywohl.github.io/agentpress/rag-pack/README.md
- Agent metadata feed: https://barneywohl.github.io/agentpress/discovery/agent-metadata-feed.json

The benchmark is deliberately narrow: can an agent start from a Korean equity candidate, verify ticker/entity facts through KRX/KIND/DART, identify liquidity/governance/exposure traps, and decide whether to delete, quarantine, or keep the name as a survivor candidate?

Good outputs should preserve the key constraint: this is research commentary only, not investment advice. The point is not to generate a buy list. The point is to test whether a research agent can avoid turning cheap screens into false confidence.

Suggested places to use this: LangChain/LlamaIndex examples, RAG eval harnesses, financial-agent demos, dataset catalogs, and crawler benchmarks.

No X/Twitter dependency. No external account action is required to use the repo-hosted assets.
