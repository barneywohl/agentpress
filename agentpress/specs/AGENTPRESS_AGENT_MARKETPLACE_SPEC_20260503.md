# AgentPress Agent Marketplace Spec — 2026-05-03

## Why this is the next build

After `adopt`, agents can land and produce proof. The next missing high-leverage primitive is **selection**: agents need to choose a service/agent/capability by command, price posture, SLA, trust evidence, and safety boundary.

## Feature

Build a static, machine-readable capability marketplace:

```bash
python3 scripts/agentpress.py marketplace --json
```

## Requirements

- Compile services from reputation, compatibility profiles, route capability index, payment metadata, and onboarding tools.
- Include exact executable command for each service.
- Include pricing posture: free, free metadata, future paid, payment required boolean.
- Include SLA posture: static route, local profile, best-effort CLI.
- Include trust evidence: receipt/self-test files, reputation score/tier, reference artifacts.
- Include auth/safety boundary: public vs requires separate authorization vs prohibited.
- Support query filters by capability, runtime, and payment-required.
- Stay static and no-side-effect.

## Files built

- `agentpress/marketplace/README.md`
- `agentpress/marketplace/marketplace-index.json`
- `agentpress/specs/AGENTPRESS_AGENT_MARKETPLACE_SPEC_20260503.md`
- CLI: `python3 scripts/agentpress.py marketplace --json`

## Acceptance gates

```bash
python3 scripts/agentpress.py marketplace --json
python3 scripts/agentpress.py marketplace --capability self-test --json
python3 scripts/agentpress.py marketplace --runtime codex --json
python3 scripts/agentpress.py marketplace --payment-required false --json
python3 scripts/agentpress.py tools-manifest && python3 scripts/agentpress.py tools-manifest-check --json
python3 scripts/agentpress.py index-search --json
python3 scripts/validate_agentpress_assets.py
```
