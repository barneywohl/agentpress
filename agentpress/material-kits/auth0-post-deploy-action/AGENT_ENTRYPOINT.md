# Auth0: post deploy action

## Primary task
Use this GLM kit to extract source facts for `Auth0` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://auth0.com/docs/api/management/v2/actions/post-deploy-action
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact trigger event name for post-deploy actions in Auth0
- Exact payload shape and required fields for the post-deploy action
- Exact error codes and timeout limits for post-deploy actions

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-post-deploy-action --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
