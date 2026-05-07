# Redis: probabilistic data structures compact context

## Primary task
Use this GLM kit to extract source facts for `Redis` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/probabilistic
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact Redis command names for probabilistic operations (e.g., PFADD, PFCOUNT)
- Parameter signatures and return value shapes for those commands
- Accuracy and memory overhead characteristics of the probabilistic structures

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-probabilistic --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
