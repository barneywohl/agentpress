#!/usr/bin/env bash
set -euo pipefail
want="${AGENTPRESS_VERSION:-0.1.0}"
echo "AgentPress fallback installer (target ${want})"
try_cmd() { echo "+ $*" >&2; "$@"; }
if command -v npm >/dev/null 2>&1; then
  if try_cmd npm install -g "@agent_press/agentpress@${want}"; then
    agentpress --help >/dev/null && echo "installed via npm" && exit 0
  fi
fi
if command -v python3 >/dev/null 2>&1; then
  tmp="$(mktemp -d)"
  if python3 -m venv "$tmp/venv" && "$tmp/venv/bin/python" -m pip install -q "agentpress-static==${want}"; then
    "$tmp/venv/bin/agentpress" --help >/dev/null && echo "installed via PyPI venv: $tmp/venv/bin/agentpress" && exit 0
  fi
fi
if command -v git >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  dir="${AGENTPRESS_DIR:-$HOME/.agentpress-src}"
  rm -rf "$dir"
  git clone --depth 1 https://github.com/barneywohl/agentpress.git "$dir"
  python3 "$dir/scripts/agentpress.py" doctor --json >/dev/null && echo "installed from git source: python3 $dir/scripts/agentpress.py" && exit 0
fi
if command -v curl >/dev/null 2>&1; then
  tmp="$(mktemp -d)"
  curl -fsSL https://agentpress.pages.dev/llms.txt -o "$tmp/llms.txt"
  curl -fsSL https://agentpress.pages.dev/.well-known/agentpress.json -o "$tmp/agentpress.json"
  test -s "$tmp/llms.txt" -a -s "$tmp/agentpress.json" && echo "static fallback fetched: $tmp" && exit 0
fi
echo "AgentPress install failed across npm/PyPI/git/static fallbacks" >&2
exit 1
