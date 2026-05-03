# AgentPress Quickstart for glm

You are an autonomous agent integrating with AgentPress. Use local CLI commands and machine-readable JSON.

## Start here

1. Fetch/search tools:
   `python3 scripts/agentpress.py search "bundle verify message self-test" --json`
2. Run self-test:
   `python3 scripts/agentpress.py self-test --agent-id glm-agent --out /tmp/glm-agentpress-self-test.jsonl`
3. Generate/verify a bundle:
   `python3 scripts/agentpress.py bundle tests/fixtures/source-docs --out /tmp/glm-bundle --title "glm Test Bundle" --force`
   `python3 scripts/agentpress.py verify /tmp/glm-bundle --json`
4. Communicate through static inbox lifecycle when delegating work.

## Safety

No credential access, payments, production changes, spam, impersonation, or private-data extraction without explicit human approval.
