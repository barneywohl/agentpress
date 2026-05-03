# AgentPress Agent Usability Standard v0.1

AgentPress exists to make any publication instantly usable by autonomous agents.
A human homepage is optional polish. The agent entrypoint is the product.

## North Star

**An agent should understand, verify, cite, and act on a publication in under 60 seconds without scraping guesswork.**

If an agent has to infer structure, hunt for sources, guess freshness, or invent next steps, the publication failed.

## The 60-Second Agent Test

A fresh agent with no prior context should be able to answer:

1. Agent contract publication about?
2. Who produced it and what is their intent?
3. What should I read first?
4. What claims are made?
5. What sources support each claim?
6. What is stale or uncertain?
7. What can I cite?
8. What actions am I allowed to take?
9. What tasks can I run?
10. What output format should I return?

## Required Files

Every AgentPress publication should ship these at the root or predictable paths:

| File | Purpose |
|---|---|
| `AGENT_ENTRYPOINT.md` | First file every agent should read. Plain-English routing + priority context. |
| `llms.txt` | Compact crawler/LLM map of canonical pages and artifacts. |
| `agent-task-card.json` | Machine-readable tasks agents can execute. |
| `source-map.json` | Claims/sources/citation map. |
| `freshness.json` | Last updated timestamps, stale zones, refresh policy. |
| `allowed-actions.json` | What agents may/may not do. Prevents overreach. |
| `evals/*.jsonl` | Tests agents can run to prove comprehension/quality. |
| `citation-policy.md` | How to cite and what not to cite. |
| `telemetry/agent-telemetry-map.json` | Ethical source-tagged links and aggregate analytics only. |
| `README.md` or `index.html` | Agent-readable landing page. |

## Agent-First UX Principles

### 1. One obvious first file
Agents should not choose between ten markdown files. `AGENT_ENTRYPOINT.md` must tell them exactly where to start.

### 2. Tasks, not just content
A publication should include runnable tasks:
- summarize with citations
- verify a claim
- refresh stale source data
- compare against a competitor/source
- produce a memo in a defined schema
- run an eval harness

### 3. Citation by construction
Every major claim should map to source evidence. If source confidence is weak, say so directly.

### 4. Explicit uncertainty
Agents need kill criteria, freshness windows, and known-bad assumptions. Do not make agents discover caveats by accident.

### 5. Safe action boundaries
Tell agents what they may do: read, cite, transform, benchmark, open issue, create PR. Also tell them what they may not do: trade, recommend, impersonate, spam, scrape private data, or bypass paywalls.

### 6. Stable schemas
Agents should consume JSON where possible and markdown where helpful. Avoid clever layouts that require visual parsing.

### 7. Human + agent parity
The agent fallback page should explain the same thing the agent files encode. No hidden claims in one surface only.

## Minimum Viable AgentPress Publication

For MVP, the generator must produce:

```text
AGENT_ENTRYPOINT.md
llms.txt
agent-task-card.json
source-map.json
freshness.json
allowed-actions.json
citation-policy.md
README.md
```

Optional but high-leverage:

```text
evals/<publication>-eval.jsonl
telemetry/agent-telemetry-map.json
sitemap.xml
index.html
```

## Agent implementation rule

Do **not** start with a full hosted blogging platform.

Start with a generator that turns an existing repo/folder into an agent-usable publication:

```bash
agentpress init ./my-research
agentpress audit ./my-research
agentpress build ./my-research --out ./public
agentpress score ./my-research
```

The first paid product can be hosted validation + registry:

- score my publication for agent usability
- generate missing files
- publish to a verified agent-readable registry
- show aggregate agent traffic/referrer analytics
- expose API/search for agents looking for trustworthy publications

## Scoring Rubric

Score every publication 0-100:

| Category | Points |
|---|---:|
| Obvious entrypoint | 15 |
| Machine-readable task cards | 15 |
| Source/citation coverage | 20 |
| Freshness/staleness clarity | 10 |
| Allowed-actions safety | 10 |
| Eval/test artifact | 10 |
| Agent fallback page parity | 10 |
| Ethical telemetry/discovery | 5 |
| Sitemap/registry readiness | 5 |

## What Not To Build Yet

- Social feed
- Creator monetization/subscriptions
- Complex WYSIWYG editor
- Full CMS
- Ad network
- Closed proprietary format

Those only matter after the generator and registry prove pull.

## Wedge

**Make any repo/site legible, usable, and citable by agents in 60 seconds.**
