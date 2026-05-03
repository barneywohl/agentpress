# AgentPress Routing

Static capability routing tells agents where a request should go before any hosted relay exists.

- `capability-index.json`: capability → candidate agents/contract profiles
- messages use `to[].capability_requested`
- responders ACK with `agent-ack-v1`
