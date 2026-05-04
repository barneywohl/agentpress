#!/usr/bin/env bash
# End-to-end acceptance gate for AgentPress 8h sprint features.
# Usage: bash scripts/verify-sprint-features.sh [repo-root]
# Exits 0 on all-pass, 1 on any failure.
set -euo pipefail

REPO="${1:-$(dirname "$(dirname "$(realpath "$0")")")}"
SCRIPT="$REPO/scripts/agentpress.py"
PASS=0
FAIL=0
ERRORS=()

_pass() { echo "  PASS: $1"; ((PASS+=1)); }
_fail() { echo "  FAIL: $1"; ((FAIL+=1)); ERRORS+=("$1"); }
_assert() {
  local desc="$1"; shift
  if "$@" 2>/dev/null; then _pass "$desc"; else _fail "$desc"; fi
}

echo "=== AgentPress Sprint Features Verification ==="
echo "Repo: $REPO"
echo ""

# Gate 0: syntax
echo "[Gate 0] Syntax"
_assert "py_compile passes" python3 -m py_compile "$SCRIPT"

# Gate 1: first-user-bootstrap
echo "[Gate 1] first-user-bootstrap"
TMP_FUB="$(mktemp -d)"
OUT="$(python3 "$SCRIPT" first-user-bootstrap --platform cline --no-write --json 2>/dev/null)"
_assert "status=ready_for_paste" bash -c "echo '$OUT' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['status']=='ready_for_paste'\""
_assert "no_secrets_required=True" bash -c "echo '$OUT' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['safety']['no_secrets_required']==True\""
_assert "rollback pointer present" bash -c "echo '$OUT' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'rollback' in d['safety']\""
UNSUP="$(python3 "$SCRIPT" first-user-bootstrap --platform unsupported_xyz --no-write --json 2>/dev/null)"
_assert "unsupported platform != ready_for_paste" bash -c "echo '$UNSUP' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['status']!='ready_for_paste'\""

# Gate 2: proof-capture
echo "[Gate 2] proof-capture"
TMP_PROOF="$(mktemp -d)"
python3 "$SCRIPT" proof-capture --task-id gate-test --evidence-dir "$TMP_PROOF" --json >/dev/null 2>&1 || true
_assert "proof-bundle.json written" test -f "$TMP_PROOF/proof-bundle.json"
_assert "proof-card.md written" test -f "$TMP_PROOF/proof-card.md"
BUNDLE="$(cat "$TMP_PROOF/proof-bundle.json" 2>/dev/null || echo '{}')"
_assert "bundle_sha256 is 64-char hex" bash -c "echo '$BUNDLE' | python3 -c \"import sys,json; b=json.load(sys.stdin); sha=b.get('bundle_sha256',''); assert len(sha)==64 and all(c in '0123456789abcdef' for c in sha)\"" || \
  _assert "task_id present in bundle" bash -c "echo '$BUNDLE' | python3 -c \"import sys,json; b=json.load(sys.stdin); assert 'task_id' in b or 'status' in b\""
_assert "secret_scan_status present" bash -c "echo '$BUNDLE' | python3 -c \"import sys,json; b=json.load(sys.stdin); assert 'secret_scan_status' in b.get('privacy',{})\""

# Gate 3: sandbox-guard
echo "[Gate 3] sandbox-guard"
TMP_SBX="$(mktemp -d)"
SBX="$(python3 "$SCRIPT" sandbox-guard --scope read-only --paths ./src --no-write --json 2>/dev/null)"
_assert "forbidden_markers key present" bash -c "echo '$SBX' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'forbidden_markers' in d\""
_assert "allowlist_enforced key present" bash -c "echo '$SBX' | python3 -c \"import sys,json; d=json.load(sys.stdin); p=d.get('policy',{}); assert 'allowlist_enforced' in p\""
_assert "status ok" bash -c "echo '$SBX' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d.get('status') in ('ok','fail_closed')\""

# Gate 4: adoption-tracker
echo "[Gate 4] adoption-tracker"
ADO="$(python3 "$SCRIPT" adoption-tracker --period 7d --no-write --json 2>/dev/null)"
_assert "funnel stages present" bash -c "echo '$ADO' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'funnel' in d\""
_assert "privacy local-only note present" bash -c "echo '$ADO' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'local' in d.get('privacy','')\""
_assert "period in output" bash -c "echo '$ADO' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert '7d' in str(d.get('period',''))\""

# Gate 5: handoff-pack
echo "[Gate 5] handoff-pack"
HOP="$(python3 "$SCRIPT" handoff-pack --from glm --to rflo --task-id sprint-gate --no-write --json 2>/dev/null)"
_assert "from_agent present" bash -c "echo '$HOP' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'from_agent' in d\""
_assert "to_agent present" bash -c "echo '$HOP' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'to_agent' in d\""
_assert "task_id present" bash -c "echo '$HOP' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'task_id' in d\""
_assert "acceptance_gates present" bash -c "echo '$HOP' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'acceptance_gates' in d\""

# Gate 6: batch-painpoints
echo "[Gate 6] batch-painpoints"
TMP_BP="$(mktemp -d)"
echo '[{"id":"p1","text":"test painpoint one"},{"id":"p2","text":"test painpoint two"}]' > "$TMP_BP/issues.json"
python3 "$SCRIPT" batch-painpoints --input "$TMP_BP/issues.json" --output "$TMP_BP/out" --json >/dev/null 2>&1 || true
BPSUM="$TMP_BP/out/batch-painpoints-summary.json"
_assert "batch-painpoints-summary.json written" test -f "$BPSUM"
_assert "processed_count >= 2" bash -c "python3 -c \"import json; d=json.load(open('$BPSUM')); assert d.get('processed_count',0)>=2\""
_assert "approval_required_for_all=True" bash -c "python3 -c \"import json; d=json.load(open('$BPSUM')); assert d.get('approval_required_for_all')==True\""

# Gate 7: release-candidate
echo "[Gate 7] release-candidate"
RC="$(python3 "$SCRIPT" release-candidate --version 0.2.0-rc --no-write --json 2>/dev/null)"
_assert "deploy_blocked=True" bash -c "echo '$RC' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d.get('deploy_blocked')==True\""

# Gate 8: integration commands
echo "[Gate 8] Integration"
_assert "doctor passes" python3 "$SCRIPT" doctor --json
_assert "lint passes" python3 "$SCRIPT" lint . --allow-warnings --json
_assert "docs-command-check passes" python3 "$SCRIPT" docs-command-check --json
_assert "schema-validate-all passes" python3 "$SCRIPT" schema-validate-all --json

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
if [[ ${#ERRORS[@]} -gt 0 ]]; then
  echo "Failed gates:"
  for e in "${ERRORS[@]}"; do echo "  - $e"; done
fi
[[ $FAIL -eq 0 ]]
