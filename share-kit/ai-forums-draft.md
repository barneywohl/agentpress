# Korea Cheap Screen Deletion Benchmark for Stock Research Agents

I built a small financial-agent eval around a common failure mode: stock-research LLMs can summarize cheap screens, but they often fail to delete weak ideas before inventing a thesis.

The domain is Korean public equities because Korea forces source discipline outside clean US datasets: KRX/KIND identity checks, DART financial verification, liquidity/access, minority economics, and theme-to-P&L validation.

Benchmark / files: https://github.com/barneywohl/agentpress
Agent page: https://barneywohl.github.io/agentpress/

What I would like feedback on from agent/RAG builders:

1. Is the eval strict enough about source verification?
2. How would you score deletion quality versus thesis generation?
3. What additional failure cases would you add for non-US public equities?

Research commentary only. Not investment advice.
