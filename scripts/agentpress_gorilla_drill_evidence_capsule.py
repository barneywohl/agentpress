#!/usr/bin/env python3
"""Build a local-only evidence capsule checklist from the Gorilla first-run drill."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = "agentpress/evidence/agentpress-gorilla-launchpad-first-run-drill-wave99.json"
DEFAULT_OUT = "agentpress/evidence/agentpress-gorilla-drill-evidence-capsule-wave100.json"
DEFAULT_MD = "agentpress/evidence/agentpress-gorilla-drill-evidence-capsule-wave100.md"
SCRIPT_PATH = "scripts/agentpress_gorilla_drill_evidence_capsule.py"
TEST_PATH = "tests/test_agentpress_gorilla_drill_evidence_capsule.py"
SCRIPT_NAME = "rc:agentpress-gorilla-drill-evidence-capsule"
PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD, DEFAULT_SOURCE]
GENERATED = {DEFAULT_OUT, DEFAULT_MD}
FORBIDDEN = re.compile(r"\b(git\s+push|npm\s+publish|deploy|payment|wallet|secret|token|outreach|email|sendgrid|external-message|external\s+message|curl\s+https?://|wget\s+https?://|sudo|rm\s+-rf)\b", re.I)


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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_command(command: str) -> bool:
    return bool(command.strip()) and not FORBIDDEN.search(" ".join(command.split()))


def package_check(root: Path) -> tuple[dict[str, Any], list[str]]:
    pkg, err = load_json(root / "package.json")
    if err or not pkg:
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
        if rel not in GENERATED and not row["exists_local"]:
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


def evidence_slot(step: dict[str, Any]) -> dict[str, Any]:
    command = str(step.get("command", ""))
    return {
        "step": int(step.get("step", 0) or 0),
        "command_sha256": sha256_text(command),
        "command": command,
        "safe_local_only": bool(step.get("safe_local_only")) and safe_command(command),
        "required_fields": ["command_sha256", "exit_code", "stdout_tail", "stderr_tail", "generated_local_artifact_paths", "operator_note"],
        "acceptance_rule": "exit_code must be 0, command_sha256 must match this capsule, and generated artifacts must remain local until Jake approves public actions",
        "receipt_template": {
            "command_sha256": sha256_text(command),
            "exit_code": None,
            "stdout_tail": "",
            "stderr_tail": "",
            "generated_local_artifact_paths": [],
            "operator_note": "",
        },
    }


def build_capsule(root: Path, *, source_rel: str = DEFAULT_SOURCE, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    source, err = load_json(root / source_rel)
    if err or not source:
        source = {}
        blockers.append(f"source_{err}:{source_rel}")
    if source.get("status") != "ok":
        blockers.append("source_status_not_ok")
    if source.get("blockers") != []:
        blockers.append("source_blockers_not_empty")
    if source.get("public_push_publish_deploy") is not False or source.get("jake_explicit_approval_required_for_public_actions") is not True:
        blockers.append("source_public_gate_not_preserved")
    drill = source.get("first_run_drill") if isinstance(source.get("first_run_drill"), dict) else {}
    steps = drill.get("steps") if isinstance(drill.get("steps"), list) else []
    slots = [evidence_slot(row) for row in steps if isinstance(row, dict)]
    if not slots:
        blockers.append("source_missing_drill_steps")
    if not all(slot["safe_local_only"] for slot in slots):
        blockers.append("not_all_capsule_steps_safe_local_only")
    package, pkg_blockers = package_check(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required:{row.get('path')}")
    return {
        "schema_version": "2026-05-10.agentpress-gorilla-drill-evidence-capsule.v1",
        "generated_utc": utc_now(),
        "source_drill": source_rel,
        "status": "ok" if not blockers else "blocked",
        "public_push_publish_deploy": False,
        "external_actions": [],
        "payment_actions_taken": [],
        "secret_material_included": False,
        "jake_explicit_approval_required_for_public_actions": True,
        "capsule_id": "wave100-gorilla-drill-evidence-capsule",
        "agent_facing_value": "A fresh agent can now collect tamper-evident local drill receipts step-by-step, verify command hashes, and stop before any public action.",
        "receipt_schema": {
            "required_top_level_fields": ["capsule_id", "source_drill", "step_receipts", "public_action_attestation"],
            "public_action_attestation": "No push/publish/deploy/payment/external-send was attempted; Jake approval remains required.",
        },
        "evidence_slots": slots,
        "completion_rule": "every evidence slot has a matching command_sha256, exit_code=0, non-empty operator_note, and only local artifact paths",
        "package": package,
        "pack_check": pack,
        "blockers": blockers,
    }


def write_markdown(path: Path, data: dict[str, Any]) -> None:
    lines = ["# AgentPress Gorilla drill evidence capsule", "", f"Status: `{data['status']}`", "", data["agent_facing_value"], "", "## Evidence slots"]
    for row in data["evidence_slots"]:
        lines.append(f"- Step {row['step']}: `{row['command']}` — command_sha256=`{row['command_sha256']}`")
    lines += ["", "## Public action gate", "No public push/publish/deploy/payment/external-send is allowed without Jake explicit approval."]
    if data["blockers"]:
        lines += ["", "## Blockers"] + [f"- {b}" for b in data["blockers"]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--markdown-out", default=DEFAULT_MD)
    ap.add_argument("--include-pack-check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    data = build_capsule(root, source_rel=args.source, include_pack=args.include_pack_check)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(root / args.markdown_out, data)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(f"wrote {out} status={data['status']}")
    return 0 if data["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
