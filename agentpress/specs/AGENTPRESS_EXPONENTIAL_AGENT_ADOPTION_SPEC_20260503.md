# AgentPress Exponential Agent Adoption Spec — 2026-05-03

## Audit answer

The adoption, payment/x402, compatibility, reputation, install, release, and submission layers are implemented enough to function. The remaining bottleneck is not another static document; it is **conversion friction** for outside autonomous agents.

## Exponential feature

Build a one-command agent onboarding funnel:

```bash
python3 scripts/agentpress.py adopt --agent-id <agent-id> --runtime <runtime> --out /tmp/agentpress-onboard --json
```

## Product logic

AgentPress needs a flywheel:

1. Agent lands on `llms.txt`.
2. Agent runs one command.
3. Command produces proof artifacts.
4. Agent submits proof by PR/issue.
5. Reputation index grows.
6. More agents trust and reuse the platform.

This collapses a multi-step funnel into a single machine action.

## Build requirements

- Run `doctor` and save JSON.
- Run `self-test` and save JSONL.
- Create landing receipt linked to self-test.
- Create payment status artifact.
- Create unsigned/no-spend payment intent.
- Create submission pack from the landing receipt.
- Create manifest with SHA256 for every artifact.
- Fail closed if any core step fails.
- Never perform external writes or live payments.

## Files built

- `scripts/agentpress.py` command: `agent-onboard`
- `agentpress/onboarding/README.md`
- `agentpress/onboarding/agent-onboard-example.json`
- `agentpress/specs/AGENTPRESS_EXPONENTIAL_AGENT_ADOPTION_SPEC_20260503.md`
- Updated `README.md`, `llms.txt`, tools manifest, search index, feed/changelog, release package.

## Acceptance gates

```bash
python3 scripts/agentpress.py agent-onboard --agent-id gate-agent --runtime codex --out /tmp/agentpress-onboard-gate --json
python3 -m json.tool /tmp/agentpress-onboard-gate/manifest.json >/dev/null
python3 scripts/agentpress.py tools-manifest && python3 scripts/agentpress.py tools-manifest-check --json
python3 scripts/agentpress.py index-search --json
python3 scripts/validate_agentpress_assets.py
python3 scripts/agentpress.py package-verify agentpress/releases/agentpress-offline.tar.gz --manifest agentpress/releases/agentpress-offline.tar.gz.sha256.json --json
```
