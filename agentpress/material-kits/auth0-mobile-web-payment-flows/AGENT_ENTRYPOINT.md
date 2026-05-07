# Auth0: configure mobile to web payment flows

## Primary task
Use this GLM kit to extract source facts for `Auth0` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://auth0.com/docs/authenticate/single-sign-on/native-to-web/configure-mobile-to-web-payment-flows
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact OAuth scopes required for the payment endpoint
- Exact redirect URI pattern needed for mobile app callback
- Exact error codes and retry logic for payment flow failures

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-mobile-web-payment-flows --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
