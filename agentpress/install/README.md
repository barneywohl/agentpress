# AgentPress Installer

`install.py` is a dependency-free Python bootstrapper for agents. It downloads `release-index.json`, verifies package and manifest SHA256 hashes, extracts the offline AgentPress package, and verifies every packaged asset.

```bash
python3 -c "$(curl -fsSL https://barneywohl.github.io/agentpress/agentpress/install/install.py)" --json
```
