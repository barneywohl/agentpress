#!/usr/bin/env python3
"""AgentPress MCP Config Guard — backup, diff, and restore local MCP server configs.

Usage:
  python3 scripts/mcp_config_guard.py backup --json
  python3 scripts/mcp_config_guard.py diff --json
  python3 scripts/mcp_config_guard.py restore --from BACKUP_DIR --json
  python3 scripts/mcp_config_guard.py list-backups --json

Guards ~/.config/mcp/ (and Claude Code ~/.claude.json MCP sections) from
accidental clobber during AgentPress adopt/integrate operations.
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import sys
from datetime import datetime, timezone

MCP_SEARCH_PATHS = [
    pathlib.Path.home() / ".config" / "mcp",
    pathlib.Path.home() / ".claude.json",
    pathlib.Path.home() / ".config" / "claude" / "claude_desktop_config.json",
    pathlib.Path("/Users") / os.environ.get("USER", "barneywohl") / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
]

BACKUP_ROOT = pathlib.Path.home() / ".config" / "agentpress-mcp-backups"


def _sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def _collect_mcp_files() -> list[dict]:
    found = []
    for candidate in MCP_SEARCH_PATHS:
        if candidate.is_file():
            found.append({"path": str(candidate), "kind": "file", "sha256": _sha256_file(candidate)})
        elif candidate.is_dir():
            for f in sorted(candidate.rglob("*.json")):
                found.append({"path": str(f), "kind": "file", "sha256": _sha256_file(f)})
    return found


def cmd_backup(args):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = BACKUP_ROOT / ts
    backup_dir.mkdir(parents=True, exist_ok=True)

    files = _collect_mcp_files()
    manifest = {
        "schema_version": "2026-05-04.agentpress-mcp-guard.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "backup_dir": str(backup_dir),
        "files": [],
    }

    for entry in files:
        src = pathlib.Path(entry["path"])
        rel = src.name
        # Preserve enough path uniqueness to avoid collisions
        slug = entry["path"].replace("/", "_").lstrip("_")
        dst = backup_dir / slug
        shutil.copy2(src, dst)
        manifest["files"].append({
            "original": entry["path"],
            "backup": str(dst),
            "sha256": entry["sha256"],
        })

    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = {
        "status": "ok",
        "backup_dir": str(backup_dir),
        "files_backed_up": len(manifest["files"]),
        "manifest": str(backup_dir / "manifest.json"),
    }
    print(json.dumps(result, indent=2) if args.json else f"Backup OK → {backup_dir} ({len(manifest['files'])} files)")
    return 0


def cmd_diff(args):
    if not BACKUP_ROOT.exists():
        result = {"status": "no_backup", "message": "No backups found. Run backup first."}
        print(json.dumps(result, indent=2) if args.json else "No backup found.")
        return 1

    backups = sorted(BACKUP_ROOT.iterdir())
    if not backups:
        result = {"status": "no_backup", "message": "No backup directories found."}
        print(json.dumps(result, indent=2) if args.json else "No backup directories found.")
        return 1

    latest = backups[-1]
    manifest_path = latest / "manifest.json"
    if not manifest_path.exists():
        result = {"status": "error", "message": f"manifest.json missing in {latest}"}
        print(json.dumps(result, indent=2) if args.json else f"Corrupt backup: {latest}")
        return 1

    manifest = json.loads(manifest_path.read_text())
    diffs = []
    for entry in manifest["files"]:
        orig = pathlib.Path(entry["original"])
        if not orig.exists():
            diffs.append({"file": entry["original"], "change": "deleted", "backup_sha256": entry["sha256"], "current_sha256": None})
            continue
        current_sha = _sha256_file(orig)
        if current_sha != entry["sha256"]:
            diffs.append({"file": entry["original"], "change": "modified", "backup_sha256": entry["sha256"], "current_sha256": current_sha})

    result = {
        "status": "ok",
        "backup_dir": str(latest),
        "backup_utc": manifest.get("created_utc"),
        "files_checked": len(manifest["files"]),
        "diffs": diffs,
        "drift_detected": len(diffs) > 0,
    }
    print(json.dumps(result, indent=2) if args.json else (f"Drift detected: {len(diffs)} changed file(s)" if diffs else "No drift — MCP configs match backup."))
    return 1 if diffs else 0


def cmd_restore(args):
    backup_dir = pathlib.Path(args.from_dir)
    if not backup_dir.exists():
        result = {"status": "error", "message": f"Backup dir not found: {backup_dir}"}
        print(json.dumps(result, indent=2) if args.json else f"Not found: {backup_dir}")
        return 1

    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        result = {"status": "error", "message": "manifest.json missing in backup dir"}
        print(json.dumps(result, indent=2) if args.json else "Corrupt backup.")
        return 1

    manifest = json.loads(manifest_path.read_text())
    restored = []
    for entry in manifest["files"]:
        src = pathlib.Path(entry["backup"])
        dst = pathlib.Path(entry["original"])
        if not src.exists():
            result = {"status": "error", "message": f"Backup file missing: {src}"}
            print(json.dumps(result, indent=2) if args.json else f"Missing backup file: {src}")
            return 1
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        restored.append(entry["original"])

    result = {
        "status": "ok",
        "restored_from": str(backup_dir),
        "files_restored": len(restored),
        "restored": restored,
    }
    print(json.dumps(result, indent=2) if args.json else f"Restored {len(restored)} file(s) from {backup_dir}")
    return 0


def cmd_list_backups(args):
    if not BACKUP_ROOT.exists():
        result = {"status": "ok", "backups": []}
        print(json.dumps(result, indent=2) if args.json else "No backups.")
        return 0

    backups = []
    for d in sorted(BACKUP_ROOT.iterdir()):
        mf = d / "manifest.json"
        if mf.exists():
            m = json.loads(mf.read_text())
            backups.append({"dir": str(d), "created_utc": m.get("created_utc"), "files": len(m.get("files", []))})

    result = {"status": "ok", "backups": backups, "count": len(backups)}
    print(json.dumps(result, indent=2) if args.json else f"{len(backups)} backup(s) in {BACKUP_ROOT}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="AgentPress MCP Config Guard")
    ap.add_argument("--json", action="store_true", help="JSON output")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("backup", help="Snapshot current MCP configs")
    sub.add_parser("diff", help="Diff current MCP configs against latest backup")

    r = sub.add_parser("restore", help="Restore MCP configs from a backup")
    r.add_argument("--from", dest="from_dir", required=True, help="Backup directory to restore from")

    sub.add_parser("list-backups", help="List all backups")

    args = ap.parse_args()
    if args.cmd == "backup":
        sys.exit(cmd_backup(args))
    elif args.cmd == "diff":
        sys.exit(cmd_diff(args))
    elif args.cmd == "restore":
        sys.exit(cmd_restore(args))
    elif args.cmd == "list-backups":
        sys.exit(cmd_list_backups(args))
    else:
        ap.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
