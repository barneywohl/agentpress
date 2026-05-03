# AgentPress Edge-Case Gap Closure Spec — 2026-05-03

## Why

The follow-up audit found missed edge cases: `native-adapter-kit --no-write` created directories, unknown native adapter targets returned ok, and prior trust/schema/native gates needed adversarial probes. This closes those gaps and adds a repeatable edge-case scan.

## Commands

```bash
python3 scripts/agentpress.py native-adapter-kit --out /tmp/agentpress-edge-nowrite --no-write --json
python3 scripts/agentpress.py edge-case-gap-scan --json
```

## Acceptance

- `native-adapter-kit --no-write` creates no files or directories.
- `native-adapter-kit --target nonexistent` fails closed.
- Missing trust report and bad trust fixtures fail closed.
- Bad approval and bad host transcript fixtures fail closed.
- CI runs the edge-case gap scan.
