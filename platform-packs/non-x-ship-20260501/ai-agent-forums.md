# Financial Research Agent Eval: Korea Cheap Screen Deletion

I built a small public-market research eval for LLM / agent builders.

Failure mode: stock-research agents can summarize cheap screens, but they often fail to delete weak ideas before inventing a thesis.

Domain: Korean public equities. Korea is useful because it forces source discipline outside clean US datasets: KRX/KIND identity checks, DART filing verification, liquidity/access checks, minority-shareholder economics, governance review, and theme-to-P&L validation.

Task: given attractive-looking Korean equity candidates, can the agent remove the names that fail local-source verification and explain why they were removed?

Core survivor stack in the public note: Poongsan, BHI, Woojin.

Separate moonshot drawer for further research prompts: Innospace, Mobiis, CellBion, IntoCell, SBB Tech.

Files / benchmark: https://github.com/barneywohl/agentpress

Agent page: https://barneywohl.github.io/agentpress/

Feedback I would like from agent/RAG builders:

1. Is the eval strict enough about source verification?
2. How would you score deletion quality versus thesis generation?
3. What additional failure cases would you add for non-US public equities?
4. Should the benchmark reward abstention when KRX/DART/liquidity evidence is incomplete?

Research commentary only. Not investment advice.
