#!/usr/bin/env bash
set -euo pipefail
echo "AgentPress sandbox guard active" >&2
case "${1:-}" in
  *clawd_secrets*|*.ssh*|*.gnupg*|*wallet*|*seed*|*.env*) echo "blocked sensitive path" >&2; exit 64;;
esac
exec "$@"
