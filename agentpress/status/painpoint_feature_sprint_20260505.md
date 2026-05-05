# AgentPress Painpoint Feature Sprint

Mission: `mission-20260505-133622-52df70`
Date: `2026-05-05`
Owner context: shipping AgentPress features for Jake

## Ranked Painpoints

1. P0 `first_run_onboarding_friction`: agents do not know what to run first.
   Target: keep `start --json`, `doctor --json`, `llms-init`, and `first-run-wizard` as the first ranked actions.
2. P0 `python_runtime_dependency_friction`: npm shim can hit Python/runtime friction before value is visible.
   Target: keep Node fast paths useful before Python and label full CLI requirements clearly.
3. P0 `secret_path_guardrails`: agents can leak/read secret paths if boundaries are implicit.
   Target: fail closed on sensitive roots and refuse sensitive handoff evidence paths before reads.
4. P0 `proof_handoff_evidence`: agents need artifacts and hashes for handoffs, not prose claims.
   Target: make `proof-capture` and `handoff-pack` produce reviewable evidence metadata.
5. P1 `docs_command_drift`: long docs and stale examples create command drift.
   Target: keep `docs-command-check` in gates and prefer compact command cards.
6. P1 `stable_vs_rc_confusion`: agents confuse local rc metadata with stable latest.
   Target: expose `version_channel` and avoid stable registry claims without live proof.
7. P1 `compact_task_cards_source_maps`: agents need task cards/source maps before huge docs.
   Target: map every painpoint to compact runnable surfaces.
8. P1 `offline_mirror_freshness_hashes`: fallback, freshness, and hash checks need to stay adjacent to install flows.
   Target: continue `package-verify`, hash manifests, and freshness reports; defer signature work pending key policy.
9. P2 `native_adapter_ecosystem_gaps`: Cline/Roo/OpenHands/MCP/LangChain/LlamaIndex/CrewAI need native adapter polish.
   Target: keep local adapter kits safe; defer external submissions until manual approval.

## Backlog

P0:
- Ranked `painpoint-map` CLI output.
- `start --json` ranked first actions.
- Version channel clarity in first-run and registry diagnostics.
- Handoff evidence hashes with secret-path refusal.

P1:
- Expand docs-command drift gates beyond the current high-signal entrypoints.
- Add freshness/hash manifest checks into more release/mirror diagnostics.
- Generate smaller task cards/source maps for large docs and adapter packs.

P2:
- External adapter submissions after manual approval.
- Signed manifests after signing key ownership and rotation policy are approved.

## Shipped In This Sprint

- `painpoint-map` CLI command with ranked painpoints, concrete target features, P0/P1/P2 backlog, safe scope, and deferred blockers.
- `start --json` now includes `ranked_first_actions`, `version_channel`, and a `painpoint_map_command`.
- `doctor` and `package-registry-doctor` now expose stable-vs-rc channel guidance without claiming live registry state.
- `proof-capture` now emits a follow-on `handoff_command`.
- `handoff-pack` now emits `evidence_manifest` rows with SHA-256 hashes, missing markers, secret scan status, and sensitive-path refusal.

## Deferred Or Blocked

- No npm/PyPI publish: package/account ownership and live publish approval are not in scope.
- No external adapter submissions or issue comments: require separate manual approval.
- No signed manifests: requires approved key ownership, rotation, revocation, and storage policy.
- No Nexio org/prod/mainnet work.

## Validation Plan

Run:

```bash
python3 -m pytest -q
npm test
npm run validate
python3 scripts/agentpress.py docs-command-check --json
python3 scripts/agentpress.py schema-validate-all --json
npm_config_cache=/tmp/agentpress-npm-cache npm pack --dry-run --json
git diff --check
```
