#!/usr/bin/env python3
"""Build a wave84 fresh-agent handoff capsule from the wave83 verifier certificate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WAVE83 = "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json"
WAVE82 = "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json"
WAVE81 = "agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.json"
WAVE79 = "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json"
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_verifier_handoff_capsule.py"
TEST_PATH = "tests/test_agent_facing_acceptance_verifier_handoff_capsule.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-verifier-handoff-capsule"
VERIFIER_SCRIPT_NAME = "rc:agent-facing-acceptance-smoke-replay-receipt-verifier"
GATE_CLOSED = "closed_until_jake_explicit_approval"
RECOMMENDED_COMMAND = "npm run rc:agent-facing-acceptance-smoke-replay-receipt-verifier --silent"
REQUIRED_PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]
SOURCE_PACKAGE_FILES = [
    "scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py",
    "tests/test_agent_facing_acceptance_smoke_replay_receipt_verifier.py",
    WAVE83,
    WAVE83.replace(".json", ".md"),
]
INSPECTION_FILES = [WAVE83, WAVE83.replace(".json", ".md"), WAVE82, WAVE81, WAVE79]
FORBIDDEN_RE = re.compile(r"\b(npm\s+publish|git\s+push|deploy|curl\b|wget\b|payment|wallet|secret|token|outreach|email|send)\b", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"json_error: {exc}"
    return (data, None) if isinstance(data, dict) else (None, "json_root_not_object")


def check_clean(doc: dict[str, Any], label: str, blockers: list[str]) -> None:
    if doc.get("status") != "ok":
        blockers.append(f"{label}_status_not_ok: {doc.get('status')!r}")
    if doc.get("blockers") not in ([], None):
        blockers.append(f"{label}_has_blockers")
    if doc.get("public_actions_taken") not in ([], None):
        blockers.append(f"{label}_public_actions_contaminated")
    if doc.get("external_actions") not in ([], None):
        blockers.append(f"{label}_external_actions_contaminated")


def forbidden_hits(values: list[str]) -> list[str]:
    hits: set[str] = set()
    for value in values:
        for match in FORBIDDEN_RE.finditer(value or ""):
            hits.add(match.group(0).lower())
    return sorted(hits)


def package_expectations(root: Path) -> tuple[dict[str, Any], list[str]]:
    package, err = load_json(root / "package.json")
    if err or package is None:
        return {"script": "", "verifier_script": "", "required": []}, [f"package_json_{err}"]
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    files = package.get("files") if isinstance(package.get("files"), list) else []
    blockers: list[str] = []
    script = scripts.get(SCRIPT_NAME, "")
    verifier_script = scripts.get(VERIFIER_SCRIPT_NAME, "")
    if not script:
        blockers.append(f"package_json_missing_script_{SCRIPT_NAME}")
    if not verifier_script:
        blockers.append(f"package_json_missing_script_{VERIFIER_SCRIPT_NAME}")
    required = []
    generated = {DEFAULT_OUT, DEFAULT_MD}
    for rel in REQUIRED_PACKAGE_FILES:
        row = {"path": rel, "exists_local": (root / rel).exists(), "listed_in_package_files": rel in files}
        required.append(row)
        if not row["exists_local"] and rel not in generated:
            blockers.append(f"package_required_missing_local: {rel}")
        if not row["listed_in_package_files"]:
            blockers.append(f"package_json_files_missing: {rel}")
    return {"script": script, "verifier_script": verifier_script, "required": required}, blockers


def run_verifier_command(root: Path) -> dict[str, Any]:
    proc = subprocess.run(["npm", "run", VERIFIER_SCRIPT_NAME, "--silent"], cwd=root, text=True, capture_output=True, check=False, timeout=120)
    return {
        "command": RECOMMENDED_COMMAND,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-1200:],
        "stderr_tail": proc.stderr[-1200:],
        "local_only": True,
        "public_action_free": True,
    }


def run_pack(root: Path) -> dict[str, Any]:
    proc = subprocess.run(["npm", "pack", "--dry-run", "--json"], cwd=root, text=True, capture_output=True, check=False)
    result: dict[str, Any] = {"command": "npm pack --dry-run --json", "returncode": proc.returncode, "json_parseable": False, "required_included": []}
    if proc.returncode != 0:
        result.update({"stdout": proc.stdout[-1000:], "stderr": proc.stderr[-1000:]})
        return result
    try:
        payload = json.loads(proc.stdout)
        result["json_parseable"] = True
    except Exception as exc:  # noqa: BLE001
        result["parse_error"] = str(exc)
        return result
    names: set[str] = set()
    if isinstance(payload, list) and payload:
        for item in payload[0].get("files", []):
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                names.add(item["path"])
    for rel in REQUIRED_PACKAGE_FILES + SOURCE_PACKAGE_FILES:
        result["required_included"].append({"path": rel, "included": rel in names})
    return result


def build_capsule(root: Path, *, include_pack: bool = False, run_verifier: bool = True) -> dict[str, Any]:
    generated_at = utc_now()
    blockers: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    loaded: dict[str, dict[str, Any]] = {}
    for label, rel in [("wave83", WAVE83), ("wave82", WAVE82), ("wave81", WAVE81), ("wave79", WAVE79)]:
        doc, err = load_json(root / rel)
        if err or doc is None:
            docs[label] = {}
            loaded[label] = {"path": rel, "loaded": False, "error": err}
            blockers.append(f"{label}_source_{err}: {rel}")
        else:
            docs[label] = doc
            loaded[label] = {"path": rel, "loaded": True, "status": doc.get("status")}
            check_clean(doc, label, blockers)

    wave83 = docs["wave83"]
    certificate = wave83.get("operator_certificate") if isinstance(wave83.get("operator_certificate"), dict) else {}
    command_chain_verified = certificate.get("command_chain_verified") is True
    replay_returncode = certificate.get("selected_command_replay_returncode")
    expected_output_count = int(certificate.get("expected_output_count") or 0)
    if not command_chain_verified:
        blockers.append("wave83_command_chain_not_verified")
    if replay_returncode != 0:
        blockers.append("wave83_selected_command_replay_returncode_not_zero")
    if expected_output_count < 4:
        blockers.append("wave83_expected_output_count_lt_4")
    if wave83.get("public_action_gate") != GATE_CLOSED or certificate.get("public_action_gate") != GATE_CLOSED:
        blockers.append("wave83_public_action_gate_not_closed")

    inspection_files = []
    for rel in INSPECTION_FILES:
        row = {"path": rel, "exists_local": (root / rel).exists(), "required_for_fresh_agent": True}
        inspection_files.append(row)
        if not row["exists_local"]:
            blockers.append(f"inspection_file_missing: {rel}")

    recommended_commands = [{
        "command": RECOMMENDED_COMMAND,
        "purpose": "Fresh-agent deterministic verification of the wave83 certificate and upstream replay evidence.",
        "local_only": True,
        "public_action_free": True,
        "requires_jake_approval": False,
    }]
    hits = forbidden_hits([row["command"] for row in recommended_commands])
    if hits:
        blockers.append(f"forbidden_command_text_detected: {hits}")
    if len(recommended_commands) != 1:
        blockers.append("recommended_safe_paste_command_count_not_one")

    verifier_run = run_verifier_command(root) if run_verifier else {"skipped": True, "returncode": 0, "command": RECOMMENDED_COMMAND}
    if verifier_run.get("returncode") != 0:
        blockers.append("verifier_command_failed")

    pkg, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required: {row.get('path')}")

    digest = json.dumps({"certificate": certificate.get("certificate_id"), "command": RECOMMENDED_COMMAND, "generated_at": generated_at}, sort_keys=True)
    handoff_capsule = {
        "capsule_id": "wave84-handoff-" + hashlib.sha256(digest.encode()).hexdigest()[:16],
        "source_wave83_certificate_id": certificate.get("certificate_id"),
        "recommended_safe_paste_commands": recommended_commands,
        "recommended_safe_paste_command_count": len(recommended_commands),
        "fresh_agent_inspection_files": inspection_files,
        "stop_go_criteria": {
            "go_if": [
                "wave83 status is ok and blockers is empty",
                "command_chain_verified is true",
                "selected_command_replay_returncode is 0",
                "expected_output_count is at least 4",
                "public_action_gate is closed_until_jake_explicit_approval",
                "public_actions_taken and external_actions are empty",
            ],
            "stop_if": [
                "any blocker is present",
                "the verifier command exits non-zero",
                "any recommended command contains publish/push/deploy/outreach/payment/secret text",
                "any public or external action is required before Jake approval",
            ],
        },
        "command_chain_verified": command_chain_verified,
        "selected_command_replay_returncode": replay_returncode,
        "expected_output_count": expected_output_count,
    }
    return {
        "kind": "agentpress_agent_facing_acceptance_verifier_handoff_capsule",
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "ok" if not blockers else "blocked",
        "local_only": True,
        "source_certificate": WAVE83,
        "handoff_capsule": handoff_capsule,
        "loaded_sources": loaded,
        "verifier_command_run": verifier_run,
        "package_json_inclusion_expectations": pkg,
        "npm_pack_dry_run": pack,
        "public_action_gate": GATE_CLOSED,
        "public_actions_taken": [],
        "external_actions": [],
        "blockers": blockers,
    }


def markdown(doc: dict[str, Any]) -> str:
    cap = doc["handoff_capsule"]
    lines = [
        "# Agent-facing acceptance verifier handoff capsule (wave84)",
        "",
        f"- Status: `{doc['status']}`",
        f"- Generated at: `{doc['generated_at']}`",
        f"- Capsule: `{cap['capsule_id']}`",
        f"- Source certificate: `{cap.get('source_wave83_certificate_id')}`",
        f"- Safe paste command: `{cap['recommended_safe_paste_commands'][0]['command']}`",
        f"- Command chain verified: `{cap.get('command_chain_verified')}`",
        f"- Replay return code: `{cap.get('selected_command_replay_returncode')}`",
        f"- Expected output count: `{cap.get('expected_output_count')}`",
        f"- Public action gate: `{doc['public_action_gate']}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Fresh-agent inspection files",
    ]
    lines.extend([f"- `{row['path']}`" for row in cap["fresh_agent_inspection_files"]])
    lines.extend(["", "## Stop/go criteria", "", "Go if:"])
    lines.extend([f"- {item}" for item in cap["stop_go_criteria"]["go_if"]])
    lines.append("Stop if:")
    lines.extend([f"- {item}" for item in cap["stop_go_criteria"]["stop_if"]])
    lines.extend(["", "## Blockers"])
    lines.extend([f"- {b}" for b in doc.get("blockers", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, doc: dict[str, Any], out_rel: str, md_rel: str) -> None:
    out = root / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = root / md_rel
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(markdown(doc), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--skip-verifier-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    doc = build_capsule(root, include_pack=False, run_verifier=not args.skip_verifier_run)
    write_outputs(root, doc, args.out, args.markdown_out)
    if args.include_pack_check:
        doc = build_capsule(root, include_pack=True, run_verifier=not args.skip_verifier_run)
        write_outputs(root, doc, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    return 0 if doc["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
