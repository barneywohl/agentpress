#!/bin/sh
set -eu
python3 scripts/agentpress.py doctor --json
python3 scripts/agentpress.py first-run-wizard --json
python3 scripts/agentpress.py landing-receipt --agent-id agentpress-smoke --runtime unknown --discovery-channel adoption-fixpack --out /tmp/agentpress-smoke-landing.json --json
python3 scripts/agentpress.py self-test --agent-id agentpress-smoke --out /tmp/agentpress-smoke-self-test.jsonl
python3 scripts/agentpress.py submission-pack --receipt /tmp/agentpress-smoke-landing.json --out /tmp/agentpress-smoke-submission --json
