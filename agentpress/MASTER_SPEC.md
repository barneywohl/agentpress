# AgentPress Master Spec v0.1

## Mission

Make any repo, research folder, or website legible, usable, citable, and actionable by AI agents in under 60 seconds.

AgentPress is not a blog theme. It is a publication protocol for the agentic internet: a standard bundle of human-readable pages, machine-readable contracts, source maps, task cards, evals, permissions, and freshness metadata.

## Core User

The primary user is an autonomous or semi-autonomous agent that has been asked to understand, verify, cite, transform, benchmark, or act on a body of work.

Secondary users:

- human researchers publishing agent-readable work,
- companies making docs/product pages agent-friendly,
- RAG/eval builders needing reliable corpora,
- investors/diligence teams using agents to inspect claims,
- search/crawler systems looking for trustworthy structured sources.

## Product Wedge

**Make any repo/site legible, usable, and citable by AI agents in 60 seconds.**

Do not start with a full CMS. Start with a generator + validator + scoring rubric.

## The 60-Second Agent Contract

A fresh agent with no prior context must be able to answer:

1. What is this publication about?
2. Who produced it and why?
3. What file should I read first?
4. What tasks can I run?
5. What claims are being made?
6. What sources support those claims?
7. What is stale, uncertain, or explicitly out of scope?
8. What can I cite?
9. What actions am I allowed to take?
10. What output schema should I return?

If the agent must scrape, infer structure, guess permissions, hunt for sources, or invent task formats, the publication fails.

## Required Bundle

Every AgentPress publication should include:

| Path | Purpose |
|---|---|
| `README.md` | Human landing page and summary. |
| `index.html` | Crawlable web landing page. |
| `AGENT_ENTRYPOINT.md` | First file for agents; explains task routing and context priority. |
| `agent-task-card.json` | Machine-readable tasks, input/output contract, and scoring rubric. |
| `llms.txt` | Compact crawler/LLM map of canonical assets. |
| `sitemap.xml` | URL discovery surface. |
| `.well-known/ai-ingestion.json` | Machine-readable ingestion manifest. |
| `source-map.json` | Claims/sources/citation map. |
| `freshness.json` | Timestamps, stale zones, refresh policy. |
| `allowed-actions.json` | Explicit agent permissions and prohibited actions. |
| `citation-policy.md` | How to cite, what not to cite, and disclaimer rules. |
| `disclaimer.md` | Legal/safety/research framing. |
| `CITATION.cff` | Citation metadata. |

Recommended:

| Path | Purpose |
|---|---|
| `evals/*.jsonl` | Agent comprehension/verification evals. |
| `EVAL_CARD.md` | Eval methodology. |
| `rag-pack/ingestion-manifest.json` | RAG ingestion metadata. |
| `rag-pack/retrieval-queries.md` | Canonical retrieval queries. |
| `prompts/agent-prompt.md` | Reusable agent prompt. |
| `telemetry/agent-telemetry-map.json` | Ethical aggregate telemetry links only. |
| `discovery/crawler-seed-list.json` | Public crawler/discovery targets. |

## CLI Product Requirements

Minimum CLI:

```bash
agentpress init ./my-publication
agentpress audit ./my-publication
agentpress score ./my-publication
agentpress build ./my-publication --out ./public
agentpress add eval ./my-publication
agentpress add rag-pack ./my-publication
```

### `agentpress init`

Creates the required bundle from templates.

Inputs:

- title,
- description,
- author/org,
- canonical URL,
- publication type,
- disclaimer profile,
- allowed actions.

Outputs:

- required file scaffold,
- starter task card,
- starter source map,
- starter freshness policy,
- starter citation policy.

### `agentpress audit`

Checks completeness and correctness.

Required checks:

- required files exist,
- JSON parses,
- XML parses,
- `AGENT_ENTRYPOINT.md` contains primary task/input/output/citation/non-goals,
- task card contains objective/input/output/rubric/assets,
- disclaimer exists,
- sitemap includes canonical pages,
- no disallowed telemetry patterns,
- source map exists for major claims.

### `agentpress score`

Outputs 0-100 agent-usability score.

Rubric:

| Category | Points |
|---|---:|
| Obvious entrypoint | 15 |
| Machine-readable task cards | 15 |
| Source/citation coverage | 20 |
| Freshness/staleness clarity | 10 |
| Allowed-actions safety | 10 |
| Eval/test artifact | 10 |
| Human landing page parity | 10 |
| Ethical telemetry/discovery | 5 |
| Sitemap/registry readiness | 5 |

### `agentpress build`

Builds a static public output directory from the bundle.

Outputs:

- static HTML landing page,
- copied machine-readable files,
- sitemap,
- registry metadata.

## Agent Task Card Schema

Required fields:

```json
{
  "schema_version": "0.1",
  "title": "string",
  "task_type": "research|verification|eval|rag|summary|transformation",
  "target_agents": ["research_agent", "citation_agent"],
  "objective": "string",
  "input_contract": {},
  "output_contract": {},
  "primary_assets": [],
  "source_requirements": [],
  "scoring_rubric": [],
  "non_goals": [],
  "allowed_actions": [],
  "prohibited_actions": []
}
```

## Source Map Schema

Required fields:

```json
{
  "schema_version": "0.1",
  "claims": [
    {
      "claim_id": "claim-001",
      "claim": "string",
      "confidence": "high|medium|low",
      "sources": [
        {
          "title": "string",
          "url_or_path": "string",
          "retrieved_or_updated_at": "ISO-8601",
          "evidence_type": "primary|secondary|derived"
        }
      ],
      "freshness_window_days": 30,
      "kill_criteria": []
    }
  ]
}
```

## Allowed Actions Schema

Required fields:

```json
{
  "schema_version": "0.1",
  "allowed": ["read", "summarize", "cite", "transform", "benchmark", "open_issue", "create_pr"],
  "requires_human_approval": ["external_post", "investment_recommendation", "private_data_access"],
  "prohibited": ["deceptive_tracking", "impersonation", "spam", "bypass_paywall", "trading_recommendation"]
}
```

## Freshness Schema

Required fields:

```json
{
  "schema_version": "0.1",
  "publication_updated_at": "ISO-8601",
  "source_refresh_policy": "string",
  "stale_after_days": 30,
  "stale_sections": [],
  "known_uncertainties": []
}
```

## Hosted Registry Roadmap

Only after the CLI proves pull.

Registry features:

1. verified AgentPress publication listing,
2. search/API for agents,
3. agent-usability score badge,
4. crawl/freshness monitor,
5. aggregate ethical telemetry,
6. issue/PR handoff to publication owners,
7. private enterprise publications.

## What Not To Build Yet

- full WYSIWYG CMS,
- social feed,
- creator subscription stack,
- ads,
- closed proprietary format,
- fake agent traffic analytics,
- hidden tracking.

## Success Metrics

- Agent can complete 60-second test without extra instructions.
- A new publication can be generated in under 10 minutes.
- Validator catches missing/invalid files.
- External agents/crawlers can ingest without bespoke prompting.
- GitHub clone/referrer/fork/issue activity increases after artifacts.
- Users ask to publish non-Korea corpora with AgentPress.

## Immediate Execution Plan

1. Extend current `scripts/agentpress.py` from `init/validate` to `init/audit/score/build`.
2. Add templates for `source-map.json`, `freshness.json`, `allowed-actions.json`, `citation-policy.md`, `.well-known/ai-ingestion.json`.
3. Upgrade dogfood examples to pass Master Spec.
4. Add `agentpress/examples/README.md` as a mini registry.
5. Build score output into README badge format.
6. Use Korea ticker-thesis repo as canonical reference implementation.

## Current Reference Implementation

- Korea repo: `https://github.com/barneywohl/agentpress`
- Existing AgentPress assets:
  - `agent-substack/agentpress-publication-spec.json`
  - `agent-substack/mvp-build-plan.md`
  - `agentpress/AGENT_USABILITY_STANDARD.md`
  - `scripts/agentpress.py`
  - `agentpress/templates/*`
  - `agentpress/examples/*`

## Decision

Proceed as a CLI/generator + validation standard first. A hosted platform becomes justified only when generated publications show agent/crawler/builder pull.
