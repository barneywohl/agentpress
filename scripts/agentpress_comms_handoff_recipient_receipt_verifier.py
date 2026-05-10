#!/usr/bin/env python3
"""Verify a launchpad -> comms handoff and emit a local simulated recipient acknowledgement."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_WAVE92 = "agentpress/evidence/agentpress-launchpad-comms-handoff-wave92.json"
DEFAULT_OUT = "agentpress/evidence/agentpress-comms-handoff-recipient-receipt-verifier-wave93.json"
DEFAULT_MD = "agentpress/evidence/agentpress-comms-handoff-recipient-receipt-verifier-wave93.md"
SCRIPT_PATH = "scripts/agentpress_comms_handoff_recipient_receipt_verifier.py"
TEST_PATH = "tests/test_agentpress_comms_handoff_recipient_receipt_verifier.py"
SCRIPT_NAME = "rc:agentpress-comms-handoff-recipient-receipt-verifier"
PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD, DEFAULT_WAVE92, "agentpress/evidence/agentpress-launchpad-comms-handoff-wave92.md"]
FORBIDDEN_RE = re.compile(r"\b(git\s+push|npm\s+publish|deploy|payment|wallet|secret|token|outreach|email|sendgrid|external-message|external\s+message|rm\s+-rf|sudo)\b", re.I)
LOCAL_PREFIXES = ("python3 ", "npm run ", "node ")
OK_PROOF_STATUSES = {"ok", "pass", "present", "needs_choice"}


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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_is_local_only(command: str) -> bool:
    text = " ".join(command.split())
    return text.startswith(LOCAL_PREFIXES) and not FORBIDDEN_RE.search(text)


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
        if rel not in {DEFAULT_OUT, DEFAULT_MD} and not row["exists_local"]:
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


def validate_wave92(root: Path, rel: str) -> tuple[dict[str, Any] | None, list[str], list[dict[str, Any]]]:
    blockers: list[str] = []
    proofs: list[dict[str, Any]] = []
    doc, err = load_json(root / rel)
    if err or doc is None:
        return None, [f"wave92_{err}:{rel}"], proofs
    if doc.get("status") != "ok":
        blockers.append("wave92_status_not_ok")
    if doc.get("blockers") != []:
        blockers.append("wave92_blockers_not_empty")
    if doc.get("public_actions_taken") != []:
        blockers.append("wave92_public_actions_taken_not_empty")
    if doc.get("external_actions") != []:
        blockers.append("wave92_external_actions_not_empty")
    packet = doc.get("comms_hub_packet") if isinstance(doc.get("comms_hub_packet"), dict) else {}
    if packet.get("recipient_ready") is not True:
        blockers.append("wave92_recipient_not_ready")
    message = packet.get("recipient_message") if isinstance(packet.get("recipient_message"), dict) else {}
    commands = message.get("copy_paste_commands") if isinstance(message.get("copy_paste_commands"), list) else []
    if not commands:
        blockers.append("wave92_missing_copy_paste_commands")
    for command in commands:
        if not isinstance(command, str) or not command_is_local_only(command):
            blockers.append(f"unsafe_or_nonlocal_command:{command}")
    proof_refs = message.get("proof_refs") if isinstance(message.get("proof_refs"), list) else []
    if not proof_refs:
        blockers.append("wave92_missing_proof_refs")
    for proof_rel in proof_refs:
        if not isinstance(proof_rel, str):
            blockers.append("wave92_non_string_proof_ref")
            continue
        path = root / proof_rel
        proof_doc, proof_err = load_json(path)
        status = proof_doc.get("status", "present") if proof_doc else "missing"
        proof_row = {"path": proof_rel, "exists": path.exists(), "status": status, "sha256": sha256_file(path) if path.exists() else ""}
        proofs.append(proof_row)
        if proof_err or proof_doc is None:
            blockers.append(f"missing_or_invalid_proof_ref:{proof_rel}")
        elif str(status) not in OK_PROOF_STATUSES:
            blockers.append(f"unacceptable_proof_status:{proof_rel}:{status}")
    return doc, blockers, proofs


def build_receipt(root: Path, *, wave92_rel: str = DEFAULT_WAVE92, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    wave92, wave92_blockers, proofs = validate_wave92(root, wave92_rel)
    blockers.extend(wave92_blockers)
    package, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required:{row.get('path')}")
    commands = []
    handoff_id = "missing"
    if wave92:
        packet = wave92.get("comms_hub_packet") if isinstance(wave92.get("comms_hub_packet"), dict) else {}
        message = packet.get("recipient_message") if isinstance(packet.get("recipient_message"), dict) else {}
        commands = [c for c in message.get("copy_paste_commands", []) if isinstance(c, str)]
        handoff_id = str(wave92.get("handoff_id", packet.get("handoff_id", "missing")))
    artifact_paths = [wave92_rel, DEFAULT_OUT, DEFAULT_MD]
    artifacts = [{"path": rel, "exists": (root / rel).exists(), "sha256": sha256_file(root / rel) if (root / rel).exists() else "pending"} for rel in artifact_paths]
    ack = {
        "handoff_id": handoff_id,
        "acknowledged_at": utc_now(),
        "commands_run": [{"command": c, "mode": "simulated-local-verification", "status": "ok" if command_is_local_only(c) else "blocked"} for c in commands],
        "artifacts": artifacts,
        "proof_refs_verified": proofs,
        "result_status": "ok" if not blockers else "blocked",
        "redaction_attestation": "No secrets, tokens, credentials, customer data, outreach payloads, or external messages included.",
    }
    for field in ("handoff_id", "commands_run", "artifacts", "result_status", "redaction_attestation"):
        if not ack.get(field):
            blockers.append(f"ack_missing_required_field:{field}")
    ack["result_status"] = "ok" if not blockers else "blocked"
    return {
        "kind": "agentpress_comms_handoff_recipient_receipt_verifier",
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "ok" if not blockers else "blocked",
        "source_wave92": wave92_rel,
        "source_handoff_id": handoff_id,
        "simulated_recipient_acknowledgement": ack,
        "public_actions_taken": [],
        "external_actions": [],
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "blockers": blockers,
    }


def markdown(doc: dict[str, Any]) -> str:
    lines = [
        "# AgentPress comms handoff recipient receipt verifier (wave93)",
        "",
        f"- Status: `{doc['status']}`",
        f"- Source handoff ID: `{doc['source_handoff_id']}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Simulated commands",
    ]
    for row in doc["simulated_recipient_acknowledgement"].get("commands_run", []):
        lines.append(f"- `{row.get('command')}` => `{row.get('status')}`")
    lines.extend(["", "## Blockers"])
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
    parser.add_argument("--wave92", default=DEFAULT_WAVE92)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    doc = build_receipt(root, wave92_rel=args.wave92, include_pack=False)
    write_outputs(root, doc, args.out, args.markdown_out)
    if args.include_pack_check:
        doc = build_receipt(root, wave92_rel=args.wave92, include_pack=True)
        write_outputs(root, doc, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    return 0 if doc["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
