# AgentPress Host Transcript + TTF-Green Conformance Cycle Spec — 2026-05-03

## Why

After closing GLM’s fail-closed concerns, the next cycle is converting real outside host runs into scored conformance evidence. Agents need host transcript validation and time-to-first-green telemetry import so Cline/Roo/OpenHands/MCP/LangChain/LlamaIndex/CrewAI failures become actionable backlog.

## Commands

```bash
python3 scripts/agentpress.py host-transcript-validate tests/fixtures/conformance/host-transcript-good.json --json
python3 scripts/agentpress.py ttf-green-import tests/fixtures/metrics/ttf-green-good.json --json
python3 scripts/agentpress.py conformance-evidence-score --json
```

## Acceptance

- Good host transcript passes and bad host transcript fails.
- Good TTF-green telemetry passes and malformed telemetry fails.
- CI gates host transcript validation, TTF-green import, and conformance scoring.
- Conformance evidence score combines host + UX evidence without overclaiming external adoption.
