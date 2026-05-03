# AgentPress Protocol Integrations

AgentPress should be easy for different agent stacks to consume. This file defines the integration surface to build against.

## 1. Static web / crawler

- `index.html` for agents and simple browser agents.
- `llms.txt` for compact LLM/crawler instructions.
- `sitemap.xml` for crawl discovery.
- `.well-known/ai-ingestion.json` for canonical agent ingestion metadata.

## 2. JSON Schema

Schemas live in `agentpress/schemas/` and should be used by CI and external consumers:

- `agent-task-card.schema.json`
- `source-map.schema.json`
- `freshness.schema.json`
- `allowed-actions.schema.json`
- `ai-ingestion.schema.json`

## 3. MCP resource shape

Recommended MCP resource URI pattern:

```text
agentpress://publication/{slug}
agentpress://publication/{slug}/task-card
agentpress://publication/{slug}/source-map
agentpress://publication/{slug}/allowed-actions
```

MCP resource response should include:

```json
{
  "uri": "agentpress://publication/api-docs-handoff",
  "mimeType": "application/json",
  "text": "{...agent-task-card.json...}"
}
```

## 4. OpenAPI route shape

Minimal API wrapper for hosted deployments:

```yaml
openapi: 3.1.0
info:
  title: AgentPress Registry API
  version: 0.1.0
paths:
  /agentpress/agentpress-registry.json:
    get:
      summary: List AgentPress publications
      responses:
        '200':
          description: Registry JSON
  /agentpress/examples/{slug}/agent-task-card.json:
    get:
      summary: Fetch task card for a publication
      parameters:
        - name: slug
          in: path
          required: true
          schema: { type: string }
      responses:
        '200':
          description: Agent task card
```

## 5. RSS/Atom feed

Shipped: JSON/RSS feeds containing publication title, slug, canonical URL, updated timestamp, score, and disclaimer.

## 6. Compatibility target agents

Test prompts should run against:

- Codex/OpenAI-style coding agent
- Claude/Anthropic-style research agent
- Gemini/Google-style long-context agent
- GLM/local OpenAI-compatible model
- generic open-source instruct model

Each agent should be able to answer:

1. Agent contract publication asking me to do?
2. What sources may I cite?
3. What actions are allowed/prohibited?
4. What output schema is required?
5. Does this authorize external writes or production changes? Expected: no.

Follow the allowed-actions boundary and verify source claims before external use.
