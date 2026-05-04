#!/usr/bin/env bash
# AgentPress package-registry-fallback-installer
# Tries install paths in order: npm → pip-git → offline-tarball → local-static
# Exits 0 if any path succeeds. Each step reports which path was used.
#
# Usage:
#   bash scripts/fallback_installer.sh [--out DIR] [--json]
#   bash scripts/fallback_installer.sh --base-url URL --out agentpress-offline

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

OUT_DIR="${OUT_DIR:-agentpress-offline}"
JSON_OUT=false
BASE_URL="https://barneywohl.github.io/agentpress/"
TIMEOUT=30

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT_DIR="$2"; shift 2 ;;
    --json) JSON_OUT=true; shift ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

LOG=()
METHOD=""

log() { LOG+=("$*"); }

emit_result() {
  local status="$1" method="${2:-}" error="${3:-}"
  if $JSON_OUT; then
    printf '{\n  "status": "%s",\n  "method": "%s",\n  "out": "%s",\n  "log": %s,\n  "error": "%s"\n}\n' \
      "$status" "$method" "$OUT_DIR" "$(printf '%s\n' "${LOG[@]}" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip().splitlines()))')" "$error"
  else
    echo "[$status] method=$method out=$OUT_DIR"
    printf '  %s\n' "${LOG[@]}"
    [[ -n "$error" ]] && echo "  error: $error"
  fi
}

# --- Path 1: npm global install ---
try_npm() {
  log "trying: npm install -g @agent_press/agentpress"
  if command -v npm &>/dev/null; then
    if npm install -g "@agent_press/agentpress" --prefer-offline 2>/dev/null; then
      METHOD="npm_global"
      return 0
    fi
    log "npm install failed (auth or registry error)"
  else
    log "npm not found, skipping"
  fi
  return 1
}

# --- Path 2: pip install from git ---
try_pip_git() {
  local repo="https://github.com/barneywohl/agentpress.git"
  log "trying: pip install git+$repo"
  if command -v pip3 &>/dev/null || command -v pip &>/dev/null; then
    local pip_cmd
    pip_cmd="$(command -v pip3 || command -v pip)"
    if "$pip_cmd" install "git+$repo" --quiet 2>/dev/null; then
      METHOD="pip_git"
      return 0
    fi
    log "pip git install failed"
  else
    log "pip/pip3 not found, skipping"
  fi
  return 1
}

# --- Path 3: offline release tarball via static site ---
try_offline_tarball() {
  log "trying: offline release tarball via install.py"
  if command -v python3 &>/dev/null; then
    local install_py="$REPO_ROOT/agentpress/install/install.py"
    if [[ -f "$install_py" ]]; then
      if python3 "$install_py" --base-url "$BASE_URL" --out "$OUT_DIR" 2>/dev/null; then
        METHOD="offline_tarball"
        return 0
      fi
      log "offline tarball install failed (network or sha256 error)"
    else
      log "install.py not found at $install_py"
    fi
  else
    log "python3 not found, skipping tarball path"
  fi
  return 1
}

# --- Path 4: local static copy ---
try_local_static() {
  log "trying: copy local repo static surface"
  if [[ -d "$REPO_ROOT/agentpress" ]]; then
    mkdir -p "$OUT_DIR"
    cp -r "$REPO_ROOT/agentpress" "$OUT_DIR/"
    cp -f "$REPO_ROOT/llms.txt" "$OUT_DIR/" 2>/dev/null || true
    cp -f "$REPO_ROOT/README.md" "$OUT_DIR/" 2>/dev/null || true
    METHOD="local_static"
    log "copied local static surface to $OUT_DIR"
    return 0
  fi
  log "local agentpress dir not found at $REPO_ROOT/agentpress"
  return 1
}

# --- Run fallback chain ---
if try_npm; then
  emit_result "ok" "$METHOD"
  exit 0
elif try_pip_git; then
  emit_result "ok" "$METHOD"
  exit 0
elif try_offline_tarball; then
  emit_result "ok" "$METHOD"
  exit 0
elif try_local_static; then
  emit_result "ok" "$METHOD"
  exit 0
else
  emit_result "error" "none" "all install paths failed"
  exit 1
fi
