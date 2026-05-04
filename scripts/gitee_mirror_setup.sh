#!/usr/bin/env bash
# gitee_mirror_setup.sh — Bootstrap AgentPress China/Gitee mirror.
#
# What this script does:
#   1. Validates that the canonical repo is clean (no secrets in mirror payload)
#   2. Produces a mirrors.json entry for CN/Gitee
#   3. Prints the exact manual steps required for account creation
#   4. Outputs git commands to push static mirror artifacts to Gitee
#
# DOES NOT: log in, create Gitee accounts, store credentials, or post anything.
# Human action required: Gitee phone/captcha/2FA account creation.
#
# Usage:
#   bash scripts/gitee_mirror_setup.sh [--canonical-url URL] [--gitee-user USER] [--gitee-repo REPO] [--dry-run]

set -euo pipefail

CANONICAL_URL="${CANONICAL_URL:-https://barneywohl.github.io/agentpress}"
GITEE_USER="${GITEE_USER:-}"
GITEE_REPO="${GITEE_REPO:-agentpress}"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --canonical-url) CANONICAL_URL="$2"; shift 2 ;;
    --gitee-user) GITEE_USER="$2"; shift 2 ;;
    --gitee-repo) GITEE_REPO="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "=== AgentPress Gitee Mirror Bootstrap ==="
echo "Canonical: $CANONICAL_URL"
echo "Gitee target: https://gitee.com/${GITEE_USER:-<USER>}/${GITEE_REPO}"
echo ""

# --- Step 1: Human actions required (cannot be automated) ---
echo "STEP 1 — Human actions required (BLOCKED until complete):"
echo "  a) Register a Gitee account at https://gitee.com/signup"
echo "     Requires: phone number (CN or international), SMS verification"
echo "     Captcha: GEETEST slider captcha present at signup"
echo "  b) After signup: create repo at https://gitee.com/projects/new"
echo "     Repo name: ${GITEE_REPO}"
echo "     Visibility: Public"
echo "     Initialize: No (we push from canonical)"
echo "  c) Get Gitee username and set GITEE_USER environment variable"
echo ""

if [ -z "$GITEE_USER" ]; then
  echo "BLOCKER: GITEE_USER not set. Set it once account is created:"
  echo "  export GITEE_USER=your-gitee-username"
  echo "  bash scripts/gitee_mirror_setup.sh --gitee-user your-gitee-username"
  # Still generate mirrors.json template
fi

# --- Step 2: Safety check — no secrets in mirror payload ---
echo "STEP 2 — Safety check: scan mirror payload for secret patterns"
SECRETS_FOUND=0
SECRET_PATTERNS='(sk-[A-Za-z0-9]{20,}|PRIVATE KEY|api_key\s*[:=]|clawd_secrets|\.ssh/id_)'
if command -v grep &>/dev/null; then
  # Scan only static public assets (not ops, scripts, secrets dirs)
  HITS=$(grep -rIn --include="*.json" --include="*.txt" --include="*.yaml" --include="*.yml" \
    -E "$SECRET_PATTERNS" \
    . \
    --exclude-dir=.git \
    --exclude-dir=node_modules \
    2>/dev/null | grep -v 'test[s]\?/fixtures' | grep -v 'bad-proof-receipt' | head -10 || true)
  if [ -n "$HITS" ]; then
    echo "SECRET HITS found — do not mirror until resolved:"
    echo "$HITS"
    SECRETS_FOUND=1
  else
    echo "  Secret scan: clean (ok)"
  fi
fi

# --- Step 3: Generate mirrors.json entry ---
COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

MIRRORS_ENTRY=$(python3 - <<PYEOF
import json, sys
entry = {
  "schema_version": "1.0",
  "mirrors": [
    {
      "region": "CN",
      "host": "gitee",
      "url": "https://gitee.com/${GITEE_USER:-PLACEHOLDER}/${GITEE_REPO}",
      "canonical_url": "${CANONICAL_URL}",
      "canonical_commit": "${COMMIT}",
      "last_sync_utc": "${TIMESTAMP}",
      "operator": "${GITEE_USER:-PLACEHOLDER}",
      "mirror_type": "static_assets_only",
      "mirrored_paths": [
        "llms.txt",
        "llms.zh-CN.txt",
        ".well-known/agentpress.json",
        ".well-known/ai-ingestion.json",
        "agentpress/agentpress-registry.json",
        "agentpress/schemas/index.json",
        "agentpress/hash-manifest.json",
        "locales/llms.zh-CN.txt",
        "agent-sitemap.xml",
        "openapi.yaml"
      ],
      "not_mirrored": [
        "ops/", "agents/", "compliance/", "scripts/*.sh", ".github/",
        "credentials", "tokens", "private status logs"
      ],
      "verification_command": "curl -sS https://gitee.com/${GITEE_USER:-PLACEHOLDER}/${GITEE_REPO}/raw/main/llms.txt | sha256sum",
      "canonical_hash_source": "agentpress/hash-manifest.json",
      "status": "pending_account_creation",
      "blockers": ["gitee_account_phone_verification_required"]
    }
  ]
}
print(json.dumps(entry, indent=2))
PYEOF
)

echo ""
echo "STEP 3 — mirrors.json entry (save to agentpress/mirrors.json):"
echo "$MIRRORS_ENTRY"

MIRRORS_PATH="agentpress/mirrors.json"
if $DRY_RUN; then
  echo ""
  echo "[DRY RUN] Would write to $MIRRORS_PATH"
else
  mkdir -p agentpress
  echo "$MIRRORS_ENTRY" > "$MIRRORS_PATH"
  echo ""
  echo "Written: $MIRRORS_PATH"
fi

# --- Step 4: Git commands to push to Gitee (once account exists) ---
echo ""
echo "STEP 4 — Git commands to push to Gitee (run after Step 1 complete):"
echo ""
echo "  # Add Gitee as remote (run once)"
echo "  git remote add gitee https://gitee.com/\${GITEE_USER}/${GITEE_REPO}.git"
echo ""
echo "  # Push main branch (requires Gitee credentials / SSH key)"
echo "  git push gitee main"
echo ""
echo "  # Verify key file hash on Gitee vs canonical:"
echo "  GITEE_HASH=\$(curl -sS https://gitee.com/\${GITEE_USER}/${GITEE_REPO}/raw/main/llms.txt | sha256sum | cut -d' ' -f1)"
echo "  CANON_HASH=\$(curl -sS ${CANONICAL_URL}/llms.txt | sha256sum | cut -d' ' -f1)"
echo "  [ \"\$GITEE_HASH\" = \"\$CANON_HASH\" ] && echo 'HASH MATCH: ok' || echo 'HASH MISMATCH: investigate'"
echo ""
echo "  # Scheduled sync (cron, weekly):"
echo "  0 4 * * 0 cd /path/to/agentpress && git pull origin main && git push gitee main"

# --- Step 5: China-reachability verification ---
echo ""
echo "STEP 5 — China reachability verification (requires CN network access):"
echo "  Option A: Use a China-based CI runner (Alibaba Cloud, Tencent Cloud Actions)"
echo "  Option B: Request a CN-based volunteer to run:"
echo "    curl -sS --max-time 30 https://gitee.com/\${GITEE_USER}/${GITEE_REPO}/raw/main/llms.txt | sha256sum"
echo "    curl -sS --max-time 30 https://gitee.com/\${GITEE_USER}/${GITEE_REPO}/raw/main/.well-known/agentpress.json | python3 -m json.tool >/dev/null && echo ok"
echo "  Option C: Use a proxy service that routes through CN (document IP range used)"
echo ""
echo "  Do NOT count local fetch as CN reachability proof."

if [ "$SECRETS_FOUND" -eq 1 ]; then
  echo ""
  echo "WARNING: Secret patterns found above. Do not mirror until resolved."
  exit 1
fi

echo ""
echo "=== Done. Review blockers above before mirroring. ==="
