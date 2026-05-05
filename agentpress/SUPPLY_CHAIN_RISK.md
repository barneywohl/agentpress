# AgentPress Supply Chain Risk Controls

AgentPress intentionally keeps the npm package boring and auditable.

## Current controls

- **No runtime npm dependencies**: `package.json` must not contain `dependencies`, `optionalDependencies`, or bundled dependencies.
- **Small tarball budget**: npm package must stay under `300KB` and `100` files.
- **Explicit package whitelist**: `package.json.files` controls published paths.
- **Forbidden publish entries**: CI rejects `.env`, secrets/tokens, `node_modules`, `.git`, runtime state, and sprint/internal directories in `npm pack` output.
- **Manifest integrity**: `.well-known/agentpress.json` must pin the current `llms.txt` SHA-256 and `scripts/verify_manifest_integrity.py` must pass.
- **Install scripts disabled in smoke test**: CI installs the packed tarball with `--ignore-scripts` to reduce install-time attack surface.
- **Security disclosure path**: root `SECURITY.md` defines supported versions and reporting.

## Remaining risk reductions

1. Use npm trusted publishing/provenance from GitHub Actions for all future non-RC releases.
2. Add Sigstore/SLSA attestation for release artifacts.
3. Keep PyPI release under Trusted Publishing, not long-lived API tokens.
4. Require CODEOWNERS review before package/release workflow changes.
5. Keep third-party dependency count at zero unless a security review approves an exception.
