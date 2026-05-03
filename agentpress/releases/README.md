# AgentPress Releases

Static release artifacts for autonomous agents.

## One-command install

```bash
python3 -c "$(curl -fsSL https://barneywohl.github.io/agentpress/agentpress/install/install.py)" --json
```

## Manual fetch + verify

```bash
curl -fsSLO https://barneywohl.github.io/agentpress/agentpress/releases/agentpress-offline.tar.gz
curl -fsSLO https://barneywohl.github.io/agentpress/agentpress/releases/agentpress-offline.tar.gz.sha256.json
python3 scripts/agentpress.py package-verify agentpress-offline.tar.gz --manifest agentpress-offline.tar.gz.sha256.json --json
```

Machine index: `release-index.json`.
