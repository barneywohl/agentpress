# AgentPress Team Capability Packs

Privacy-safe context packs for agents. These are not private dossiers. They describe capabilities, public/consented sources, handoff boundaries, and prohibited uses.

Use:

```bash
python3 scripts/agentpress.py team-pack --slug example-research-team --display-name "Example Research Team" --capability research:market-map --capability writing:brief --consent-source public_source --out agentpress/team-packs/example-research-team.json
python3 scripts/agentpress.py team-pack-validate agentpress/team-packs/example-research-team.json --json
```
