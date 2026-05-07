# Auth0: json

## Primary task
Use this GLM kit to extract source facts for `Auth0` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://auth0.com/docs/customize/forms/flows/integrations/json
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- JSON schema structure for flow customization as defined in the Auth0 JSON integration documentation
- OAuth/OIDC endpoint paths and required parameters for JSON flow setup
- Callback URL structures and response codes returned by the Auth0 JSON integration endpoints

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-json-flows --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
