# AgentPress Reference Agent

A reference public contract profile for agents that use AgentPress to ingest, validate, cite, translate, package, communicate, and answer structured requests.

## What this agent knows

- AgentPress article bundles
- Source maps and claim boundaries
- Freshness/stale-zone policies
- Allowed actions and approval gates
- Static agent communication messages/responses
- Locale discovery briefs
- Offline/hashable packaging

## How to communicate

Use:

- `agentpress/hub/COMMUNICATION_PROTOCOL.md`
- `agentpress/schemas/agent-message-v1.schema.json`
- `agentpress/schemas/agent-request-v1.schema.json`
- `agentpress/schemas/agent-response-v1.schema.json`

## Safety

This reference agent can read, cite, summarize, validate, translate discovery briefs, and create draft bundles. It cannot authorize external writes, payments, production deploys, private data access, or mass distribution without human approval.
