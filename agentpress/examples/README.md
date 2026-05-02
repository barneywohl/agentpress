# AgentPress Examples Registry

These examples dogfood AgentPress as agent-native publications. Each example should pass `validate`, `audit`, and `score` before being referenced by the main repo.

## Primary reference examples

| Example | Purpose | Primary task | Score target | Canonical files |
|---|---|---|---:|---|
| [Agent Knowledge Sharing Reference](./agent-knowledge-sharing/) | Neutral global reference for agent-to-agent knowledge sharing, mirrors, translation, citation, and CLI/offline use. | Choose best entrypoints/mirrors/locales and return a safe knowledge-transfer plan with citations. | >=90 | `AGENT_ENTRYPOINT.md`, `agent-task-card.json`, `source-map.json`, `freshness.json`, `allowed-actions.json`, `translation-policy.md`, `mirrors.json`, `llms.txt` |
| [Universal Agent Reachability](./universal-agent-reachability/) | Compatibility article for global agent/crawler discovery needs. | Verify whether an AgentPress bundle is reachable by browser, coding, RAG, crawler, MCP-style, and eval agents. | >=90 | same bundle |

## Legacy stress-test examples

These are retained for ingestion/citation/eval stress testing only. They should not define product identity or primary discovery.

| Example | Purpose | Primary task | Score target | Canonical files |
|---|---|---|---:|---|
| [Korea Liquidity Trap Agent Benchmark](./liquidity-trap/) | Legacy Korea equity liquidity/access trap test. | Verify liquidity/access constraints and return survive/delete/needs-more-diligence. | >=90 | same bundle |
| [Korea Theme-to-Cash-Flow Agent Benchmark](./theme-cashflow/) | Legacy theme-to-financial-exposure test. | Map theme narrative to revenue/backlog/cash flow evidence and return a supported verdict. | >=90 | same bundle |
| [Innospace Thesis](./innospace-thesis/) | Legacy ticker-thesis diligence wrapper. | Validate Korea thesis format as an AgentPress bundle. | >=90 | same bundle |
| [Samsung HBM Margin](./samsung-hbm-margin/) | Legacy ticker-thesis diligence wrapper. | Verify qualification/yield/margin evidence and kill tests. | >=90 | same bundle |
| [SK Hynix HBM Supply](./sk-hynix-hbm-supply/) | Legacy ticker-thesis diligence wrapper. | Verify backlog/capex/customer evidence and kill tests. | >=90 | same bundle |
| [POSCO Green Steel](./posco-green-steel/) | Legacy ticker-thesis diligence wrapper. | Verify HyREX/offtake/carbon-policy evidence and kill tests. | >=90 | same bundle |
| [KB-FINRATE Korean Bank NIM Compression](./kb-finrate/) | Legacy Korean bank NIM stress-test. | Verify BOK rate path, NIM disclosures, funding mix, and kill tests. | >=90 | same bundle |

## Registry commands

```bash
python3 scripts/agentpress.py list
python3 scripts/agentpress.py list --json
python3 scripts/agentpress.py build-all agentpress/examples --out public/agentpress --clean
python3 scripts/validate_agentpress_assets.py
```

`build-all` writes a static registry with `agentpress-registry.json` so crawlers and agents can discover every shipped bundle from one path.
