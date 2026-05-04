# AgentPress first-run card

Status: `ready_for_paste`
Platform: `cline`

## Paste this agent prompt

Use AgentPress to inspect the available entrypoints, run doctor, then create a proof bundle for this first run. Do not post externally or mutate MCP config without explicit human approval.

## Steps
- 1. install: `bash agentpress/install/install-agentpress.sh`
- 2. doctor: `python3 scripts/agentpress.py doctor --json`
- 3. backup_and_guard_mcp_config: `python3 scripts/agentpress.py mcp-config-mutation-guard --config-path cline_mcp_settings.json --backup --planned-servers agentpress --json`
- 4. paste_mcp_snippet: `Cline MCP settings`
- 5. restart_host: `Reload Cline/VS Code after paste`
- 6. capture_first_proof: `python3 scripts/agentpress.py proof-capture --task first-run --evidence-dir /tmp/agentpress-proof --json`

## Success looks like
- doctor returns JSON without fatal findings
- MCP config was backed up before changes
- host reloads with an AgentPress server entry
- proof-bundle.json and proof-card.md exist

## Safety
- No secrets required
- No external posts
- Roll back with the guard backup/restore output
