# AgentPress Release Notes

## 0.1.0 — static agent-native publication toolkit

Status: package/install readiness gate added 2026-05-02.

### Ships

- Installable Python package metadata via `pyproject.toml`.
- Console command: `agentpress` → `agentpress_cli.cli:main`.
- Repo-local fallback command: `python3 scripts/agentpress.py`.
- Core commands: `init`, `validate`, `audit`, `score`, `build`, `build-all`, `index-articles`.
- CI smoke test that builds the wheel, installs it, runs `agentpress --help`, scaffolds a fresh package-smoke publication, audits/scores it, builds static output, and verifies `index.html` exists.

### Install smoke path

```bash
python3 -m pip install --upgrade pip build
python3 -m build
python3 -m pip install dist/*.whl
agentpress --help
agentpress init /tmp/agentpress-package-smoke --title "Package Smoke" --canonical "https://example.com/package-smoke/"
agentpress audit /tmp/agentpress-package-smoke
agentpress score /tmp/agentpress-package-smoke
agentpress build /tmp/agentpress-package-smoke --out /tmp/agentpress-package-smoke-public
test -f /tmp/agentpress-package-smoke-public/index.html
```

### Release gate

Do not tag or publish a package unless the GitHub Actions `AgentPress Validate` workflow passes, including:

- asset validation across examples,
- JSON/XML parsing,
- static build smoke test,
- package build/install smoke test,
- local availability gate,
- cross-agent eval prompt parse gate.

### Non-goals for 0.1.0

- No hosted CMS.
- No external posting/account actions.
- No telemetry beyond ethical aggregate discovery surfaces.
- Public reference only; verify source claims before external use.
