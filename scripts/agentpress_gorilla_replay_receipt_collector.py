#!/usr/bin/env python3
"""Collect a local-only receipt for the Gorilla replay helper without executing public actions."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_HARNESS = "agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96.json"
DEFAULT_REPLAY = "agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96-replay.sh"
DEFAULT_OUT = "agentpress/evidence/agentpress-gorilla-replay-receipt-collector-wave97.json"
DEFAULT_MD = "agentpress/evidence/agentpress-gorilla-replay-receipt-collector-wave97.md"
SCRIPT_PATH = "scripts/agentpress_gorilla_replay_receipt_collector.py"
TEST_PATH = "tests/test_agentpress_gorilla_replay_receipt_collector.py"
SCRIPT_NAME = "rc:agentpress-gorilla-replay-receipt-collector"
PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD, DEFAULT_HARNESS, DEFAULT_REPLAY]
GENERATED_ARTIFACTS = {DEFAULT_OUT, DEFAULT_MD}
ALLOWED_PREFIXES = ("python3 scripts/agentpress.py ", "npm run ", "node bin/agentpress.js ", "echo ")
FORBIDDEN_RE = re.compile(r"\b(git\s+push|npm\s+publish|deploy|payment|wallet|secret|token|outreach|email|sendgrid|external-message|external\s+message|curl\s+http|wget\s+http|sudo|rm\s+-rf)\b", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"json_error:{exc}"
    return (data, None) if isinstance(data, dict) else (None, "json_root_not_object")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


def script_commands(text: str) -> list[str]:
    commands: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line in {"set -euo pipefail"} or line.startswith("#!/"):
            continue
        commands.append(line)
    return commands


def command_safe(line: str) -> bool:
    normalized = " ".join(line.split())
    if not normalized:
        return False
    if normalized.startswith("echo "):
        return True
    return normalized.startswith(ALLOWED_PREFIXES) and not FORBIDDEN_RE.search(normalized)


def package_expectations(root: Path) -> tuple[dict[str, Any], list[str]]:
    pkg, err = load_json(root / "package.json")
    if err or pkg is None:
        return {"script": "", "required": []}, [f"package_json_{err}"]
    scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
    files = pkg.get("files") if isinstance(pkg.get("files"), list) else []
    blockers: list[str] = []
    if SCRIPT_NAME not in scripts:
        blockers.append(f"package_json_missing_script:{SCRIPT_NAME}")
    required = []
    for rel in PACKAGE_FILES:
        row = {"path": rel, "exists_local": (root / rel).exists(), "listed_in_package_files": rel in files}
        required.append(row)
        if rel not in GENERATED_ARTIFACTS and not row["exists_local"]:
            blockers.append(f"package_required_missing_local:{rel}")
        if not row["listed_in_package_files"]:
            blockers.append(f"package_json_files_missing:{rel}")
    return {"script": scripts.get(SCRIPT_NAME, ""), "required": required}, blockers


def run_pack(root: Path) -> dict[str, Any]:
    proc = subprocess.run(["npm", "pack", "--dry-run", "--json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=180)
    result: dict[str, Any] = {"command": "npm pack --dry-run --json", "returncode": proc.returncode, "json_parseable": False, "required_included": []}
    if proc.returncode != 0:
        result.update({"stdout_tail": proc.stdout[-1000:], "stderr_tail": proc.stderr[-1000:]})
        return result
    try:
        payload = json.loads(proc.stdout)
        result["json_parseable"] = True
    except Exception as exc:  # noqa: BLE001
        result["parse_error"] = str(exc)
        return result
    names = {item.get("path") for item in (payload[0].get("files", []) if isinstance(payload, list) and payload else []) if isinstance(item, dict)}
    result["required_included"] = [{"path": rel, "included": rel in names} for rel in PACKAGE_FILES]
    return result


def build_receipt(root: Path, *, harness_rel: str = DEFAULT_HARNESS, replay_rel: str = DEFAULT_REPLAY, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    harness, err = load_json(root / harness_rel)
    if err or harness is None:
        harness = {}
        blockers.append(f"harness_{err}:{harness_rel}")
    if harness.get("status") != "ok":
        blockers.append("harness_status_not_ok")
    recorded_replay = (((harness.get("acceptance_harness") or {}) if isinstance(harness.get("acceptance_harness"), dict) else {}).get("local_replay_script"))
    if recorded_replay and recorded_replay != replay_rel:
        blockers.append("replay_path_mismatch")
    replay_path = root / replay_rel
    replay_text = replay_path.read_text(encoding="utf-8") if replay_path.exists() else ""
    if not replay_text:
        blockers.append(f"replay_missing:{replay_rel}")
    commands = script_commands(replay_text)
    command_rows = []
    for idx, line in enumerate(commands, start=1):
        safe = command_safe(line)
        if not safe:
            blockers.append(f"replay_command_unsafe_or_nonlocal:{idx}")
        command_rows.append({"index": idx, "command": line, "safe_local_only": safe, "status": "ready_to_run_locally" if safe else "blocked"})
    if not any(row["command"].startswith("python3 scripts/agentpress.py ") for row in command_rows):
        blockers.append("replay_missing_agentpress_cli_command")
    package, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required:{row.get('path')}")
    receipt_id = "wave97-gorilla-replay-receipt-" + sha256(replay_path)[:12]
    return {
        "kind": "agentpress_gorilla_replay_receipt_collector",
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "ok" if not blockers else "blocked",
        "receipt_id": receipt_id,
        "source_harness": harness_rel,
        "source_replay_script": replay_rel,
        "source_replay_sha256": sha256(replay_path),
        "painpoint_solved": "Lets a recipient agent verify the wave96 Gorilla replay helper is packaged, local-only, and ready for evidence capture before running it.",
        "replay_commands": command_rows,
        "expected_local_artifacts_after_replay": ["agentpress/gorilla/utility-pack", "agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof"],
        "public_actions_taken": [],
        "external_actions": [],
        "payment_actions_taken": [],
        "secret_material_included": False,
        "operator_next_steps": [
            "Inspect this receipt and the replay script.",
            "Run only safe_local_only commands in a private checkout if local artifacts need refreshing.",
            "Attach resulting local artifacts to the sealed handoff packet.",
            "Stop before public push, publish, deploy, outreach, wallet, payment, or external-send action unless Jake explicitly approves.",
        ],
        "public_publish_push_gate": "Jake explicit approval required; no public action performed.",
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "blockers": blockers,
    }


def markdown(doc: dict[str, Any]) -> str:
    lines = [
        "# AgentPress Gorilla replay receipt collector (wave97)",
        "",
        f"- Status: `{doc['status']}`",
        f"- Receipt ID: `{doc['receipt_id']}`",
        f"- Source replay: `{doc['source_replay_script']}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "- Payment actions taken: `[]`",
        "",
        "## Replay commands",
    ]
    for row in doc.get("replay_commands", []):
        lines.append(f"- {row['index']}. `{row['command']}` — safe_local_only={row['safe_local_only']} — {row['status']}")
    lines.extend(["", "## Safety gate", "", doc.get("public_publish_push_gate", ""), "", "## Blockers"])
    lines.extend([f"- {b}" for b in doc.get("blockers", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, doc: dict[str, Any], out_rel: str, md_rel: str) -> None:
    (root / out_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / out_rel).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / md_rel).write_text(markdown(doc), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--harness", default=DEFAULT_HARNESS)
    parser.add_argument("--replay-script", default=DEFAULT_REPLAY)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    doc = build_receipt(root, harness_rel=args.harness, replay_rel=args.replay_script, include_pack=False)
    write_outputs(root, doc, args.out, args.markdown_out)
    if args.include_pack_check:
        doc = build_receipt(root, harness_rel=args.harness, replay_rel=args.replay_script, include_pack=True)
        write_outputs(root, doc, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    return 0 if doc["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
