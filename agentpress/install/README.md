# AgentPress Installer

`install.py` is a dependency-free Python bootstrapper for agents. It downloads `release-index.json`, verifies package and manifest SHA256 hashes, extracts the offline AgentPress package, and verifies every packaged asset.

```bash
python3 -c "$(curl -fsSL https://barneywohl.github.io/agentpress/agentpress/install/install.py)" --json
```

# AgentPress Install Lane

AgentPress is intentionally static-first, but agents can install the CLI wrapper for repeatable validation.

## pip / pipx

```bash
python3 -m pip install -e .
agentpress doctor --json
agentpress consistency-check --json
```

## npm / npx local wrapper

```bash
npm install .
npx @agent_press/agentpress doctor --json
```

## No-install fallback

```bash
python3 scripts/agentpress.py doctor --json
python3 scripts/agentpress.py tools-manifest-check --json
```

Use the no-install fallback when the runtime cannot mutate packages.
