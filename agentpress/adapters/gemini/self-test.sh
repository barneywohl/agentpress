#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/agentpress.py self-test --agent-id gemini-agent --out /tmp/gemini-agentpress-self-test.jsonl
python3 scripts/agentpress.py search 'message route capability' --json >/tmp/gemini-agentpress-search.json
