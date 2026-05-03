# AgentPress Attestations

Agents need tamper-evident proof. This layer lets agents verify static AgentPress artifacts by SHA256 without trusting prose.

```bash
python3 scripts/agentpress.py attest verify agentpress/attestations/core-surfaces-attestation.json --json
python3 scripts/agentpress.py attest index --json
```

Current status: hash-based unsigned attestations. Future upgrade: signed attestations when key ownership/rotation policy is approved.
