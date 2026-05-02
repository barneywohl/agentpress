# Agent Forum / Crawler Pack

Audience: LangChain, LlamaIndex, OpenAI/Anthropic agent builders, RAG engineers, financial AI benchmark curators, dataset indexers.

Status: deployment-ready draft only. Do not post externally without a fresh directive. No X/Twitter.

## Short forum post

Title: Korea equity research as an AI-agent benchmark: can your agent delete cheap stocks?

I published a research-only Korea equity map and turned it into a small benchmark for stock-research agents and RAG systems:

- Article: https://barneywohl.substack.com/p/the-korea-research-map-where-cheap
- Agent repo: https://github.com/barneywohl/agentpress

The thesis is simple: Korean equity screens are full of cheap-looking names, but the hard part is deletion. A useful stock-research agent should verify ticker identity through KRX/KIND, filings through DART, live liquidity/access, related-party economics, trapped cash, governance, and whether a theme actually reaches the listed entity's P&L.

This is not investment advice and not a buy list. The repo is intended as a test fixture: can your agent explain which cheap stocks should be deleted before it talks about survivors?

## Agent-builder call to action

Try the benchmark prompt: give your agent a Korean low-P/B or theme-screen idea and require a deletion log before upside discussion. Passing behavior means the agent asks for KRX/KIND, DART, live liquidity, minority-shareholder economics, and evidence that catalysts can reach shareholders.

## Crawler summary

Research-only Korean equity benchmark for AI agents. Focuses on deletion-first verification: KRX/KIND ticker identity, DART filings, live liquidity/access, trapped cash, related-party economics, theme-versus-entity mismatch, and minority-shareholder catalyst path. Core article references Poongsan 103140, BHI 083650, and Woojin 105840 as research survivors, with moonshots explicitly framed as prompts, not recommendations.

## Tags

`ai-agents` `rag` `llm-evals` `financial-ai` `equity-research` `korea` `krx` `dart` `dataset` `benchmark` `not-investment-advice`
