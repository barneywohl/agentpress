#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/agentpress.py self-test --agent-id codex-agent --out /tmp/codex-agentpress-self-test.jsonl
python3 scripts/agentpress.py search 'message route capability' --json >/tmp/codex-agentpress-search.json
