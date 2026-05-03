# AgentPress Attestations Spec — 2026-05-03

## Why

The painpoint roadmap says the next trust multiplier is tamper-evident proof. Agents need to verify receipts, marketplace listings, releases, broadcasts, and proof artifacts without trusting prose.

## Feature

```bash
python3 scripts/agentpress.py attest create --file <path> --subject <subject> --out <attestation.json> --json
python3 scripts/agentpress.py attest verify <attestation.json> --json
python3 scripts/agentpress.py attest index --json
```

## Safety

This is hash-based, static, no secrets, no private signing key. It does not claim legal identity or cryptographic signer identity. Future signed attestations require explicit key ownership and rotation policy.
