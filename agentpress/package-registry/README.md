# AgentPress Package Registry Plan

Agents want `pipx`, `uvx`, and `npx` install paths. Live package publishing is intentionally blocked until package/account ownership is approved.

```bash
python3 scripts/agentpress.py package-registry-plan --json
```

Safe scope now: publish-readiness metadata, dry-run checklist, install target plan. Unsafe without approval: live PyPI/npm publish or name reservation.
