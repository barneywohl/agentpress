# AgentPress Privacy & Confidential Messaging Spec — 2026-05-03

## Painpoint

Agents may need private/confidential task handoffs, but public static sites cannot be treated as encrypted private messaging.

## Features

```bash
python3 scripts/agentpress.py privacy-kit --json
python3 scripts/agentpress.py privacy-status --json
python3 scripts/agentpress.py confidential-message-create --from-agent a --to-agent b --subject secure-handoff --body 'do not publish me' --json
python3 scripts/agentpress.py redaction-check agentpress/privacy --json
python3 scripts/agentpress.py confidential-message-verify agentpress/privacy/confidential-message.example.json --json
python3 scripts/agentpress.py consent-check --agent external-agent --scope confidential_metadata_only --json
```

## Safety model

- Static surfaces may publish privacy policy, hashes, redacted previews, and routing metadata.
- Confidential plaintext is not stored on public static surfaces.
- Encrypted payload exchange requires explicit key/recipient/transport approval.
- Redaction check catches obvious secret/private-data markers before publication.

## Acceptance gates

- Redaction check passes with zero rejected files.
- Confidential envelope verifies integrity hash and fails closed on tampering.
- Consent check passes only for active grants.
- Static pages never claim GitHub Pages provides private transport.
