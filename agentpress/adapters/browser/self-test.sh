#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/agentpress.py self-test --agent-id browser-agent --out /tmp/browser-agentpress-self-test.jsonl
python3 scripts/agentpress.py search 'message route capability' --json >/tmp/browser-agentpress-search.json
