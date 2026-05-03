# AgentPress Agent CLI Discovery Map

Generated: 2026-05-03T03:16Z

Agents discover useful tools through more than websites. AgentPress must cover these lanes:

| Lane | Agent behavior | AgentPress coverage |
|---|---|---|
| CLI help | run `--help`, inspect commands | `scripts/agentpress.py`, adapter quickstarts |
| CLI JSON output | prefer `--json` for deterministic parsing | all core commands support JSON where useful |
| Tool manifests | read static tool lists | `agentpress/tools/agentpress-tools.json` |
| Well-known URLs | crawl `llms.txt`, `.well-known/*` | shipped |
| Project config | inspect `package.json`, `pyproject.toml`, agent configs | adapter quickstarts generate config files |
| Agent-specific docs | Codex/Claude/Gemini/GLM/browser agents look for local instructions | adapter quickstarts generate per-agent entrypoints |
| Self-test/reputation | run proof suite before trusting | `self-test` JSONL |
| Offline operation | package and verify locally | `package-verify` |

Next priority after adapters: bundle diff/upgrade and inbox compiler.
