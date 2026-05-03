# AgentPress Browser Smoke Evidence Spec — 2026-05-03

## Real feature

AgentPress now ships a live URL smoke-test CLI for browser/RAG agents. It checks public entrypoints, verifies HTTP success, validates JSON where required, records response metadata, and publishes machine-readable evidence.

## Command

```bash
python3 scripts/agentpress.py browser-smoke --json --require-json
```

## Output

- `agentpress/evidence/browser-smoke.json`

## Acceptance

- Checks core public URLs.
- Fails if any URL is down/empty.
- Optionally validates JSON surfaces.
- Emits HTTP status, content type, bytes read, SHA256 prefix, and elapsed time.
- Included in tools manifest, search, release package, attestation, and live Pages deployment.
