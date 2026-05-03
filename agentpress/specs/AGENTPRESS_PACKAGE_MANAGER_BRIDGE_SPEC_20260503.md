# AgentPress Package Manager Bridge Spec — 2026-05-03

## Why

Agents expect package-manager install paths. Public npm/PyPI publication requires working registry credentials, but AgentPress can still expose live package-manager compatible install lanes through Git, GitHub release assets, and the offline installer.

## Command

```bash
python3 scripts/agentpress.py package-manager-bridge --json
```

## Live install lanes

```bash
python3 -m pip install git+https://github.com/barneywohl/agentpress.git
python3 -m pip install https://github.com/barneywohl/agentpress/archive/refs/heads/main.zip
npm install github:barneywohl/agentpress
python3 -c "$(curl -fsSL https://barneywohl.github.io/agentpress/agentpress/install/install.py)" --base-url https://barneywohl.github.io/agentpress/ --out agentpress-offline
```

## Acceptance

- Publishes `agentpress/package-registry/package-manager-bridge.json`.
- Reports zero-credential pip/npm/git/offline install lanes.
- Reports npm/PyPI auth readiness without exposing credentials.
- Keeps GitHub release/offline package as the durable registry-equivalent distribution lane.
