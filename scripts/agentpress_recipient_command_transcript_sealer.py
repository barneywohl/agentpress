#!/usr/bin/env python3
"""Seal the recipient-side simulated command transcript from the wave93 comms handoff receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_WAVE93 = "agentpress/evidence/agentpress-comms-handoff-recipient-receipt-verifier-wave93.json"
DEFAULT_OUT = "agentpress/evidence/agentpress-recipient-command-transcript-sealer-wave94.json"
DEFAULT_MD = "agentpress/evidence/agentpress-recipient-command-transcript-sealer-wave94.md"
SCRIPT_PATH = "scripts/agentpress_recipient_command_transcript_sealer.py"
TEST_PATH = "tests/test_agentpress_recipient_command_transcript_sealer.py"
SCRIPT_NAME = "rc:agentpress-recipient-command-transcript-sealer"
PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD, DEFAULT_WAVE93, "agentpress/evidence/agentpress-comms-handoff-recipient-receipt-verifier-wave93.md"]
FORBIDDEN_RE = re.compile(r"\b(git\s+push|npm\s+publish|deploy|payment|wallet|secret|token|outreach|email|sendgrid|external-message|external\s+message|rm\s+-rf|sudo)\b", re.I)
LOCAL_PREFIXES = ("python3 ", "npm run ", "node ")


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


def validate_wave93(root: Path, rel: str) -> tuple[dict[str, Any] | None, list[str], list[dict[str, Any]]]:
    blockers: list[str] = []
    transcript: list[dict[str, Any]] = []
    doc, err = load_json(root / rel)
    if err or doc is None:
        return None, [f"wave93_{err}:{rel}"], transcript
    if doc.get("status") != "ok":
        blockers.append("wave93_status_not_ok")
    if doc.get("blockers") != []:
        blockers.append("wave93_blockers_not_empty")
    if doc.get("public_actions_taken") != []:
        blockers.append("wave93_public_actions_taken_not_empty")
    if doc.get("external_actions") != []:
        blockers.append("wave93_external_actions_not_empty")
    ack = doc.get("simulated_recipient_acknowledgement") if isinstance(doc.get("simulated_recipient_acknowledgement"), dict) else {}
    if ack.get("result_status") != "ok":
        blockers.append("wave93_ack_result_not_ok")
    if not str(ack.get("redaction_attestation", "")).startswith("No secrets"):
        blockers.append("wave93_missing_redaction_attestation")
    commands = ack.get("commands_run") if isinstance(ack.get("commands_run"), list) else []
    if not commands:
        blockers.append("wave93_missing_commands_run")
    for idx, row in enumerate(commands, start=1):
        if not isinstance(row, dict):
            blockers.append(f"wave93_command_row_not_object:{idx}")
            continue
        command = str(row.get("command", ""))
        status = row.get("status")
        safe = command_is_local_only(command)
        transcript.append({
            "step": idx,
            "command": command,
            "source_status": status,
            "safe_local_only": safe,
            "sealed_status": "sealed-ok" if safe and status == "ok" else "blocked",
            "transcript_note": "Local-only simulated recipient command preserved for handoff replay; not executed here.",
        })
        if status != "ok":
            blockers.append(f"wave93_command_status_not_ok:{idx}")
        if not safe:
            blockers.append(f"unsafe_or_nonlocal_command:{command}")
    return doc, blockers, transcript


def build_seal(root: Path, *, wave93_rel: str = DEFAULT_WAVE93, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    wave93, wave_blockers, transcript = validate_wave93(root, wave93_rel)
    blockers.extend(wave_blockers)
    package, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required:{row.get('path')}")
    source_handoff_id = "missing"
    if wave93:
        source_handoff_id = str(wave93.get("source_handoff_id", "missing"))
    replay_seal = {
        "source_handoff_id": source_handoff_id,
        "sealed_at": utc_now(),
        "transcript_steps": transcript,
        "operator_next_command": "npm run rc:agentpress-recipient-command-transcript-sealer --silent",
        "operator_usefulness": "A receiving agent can inspect one JSON/Markdown pair to confirm launchpad -> comms handoff commands are local-only, safe, and replay-ready without public actions.",
        "redaction_attestation": "No secrets, tokens, credentials, customer data, outreach payloads, or external messages included.",
        "public_publish_push_gate": "Jake explicit approval required; no public action performed.",
    }
    if source_handoff_id == "missing":
        blockers.append("seal_missing_source_handoff_id")
    if not transcript:
        blockers.append("seal_missing_transcript_steps")
    return {
        "kind": "agentpress_recipient_command_transcript_sealer",
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "ok" if not blockers else "blocked",
        "source_wave93": wave93_rel,
        "source_handoff_id": source_handoff_id,
        "recipient_command_transcript_seal": replay_seal,
        "public_actions_taken": [],
        "external_actions": [],
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "blockers": blockers,
    }


def markdown(doc: dict[str, Any]) -> str:
    seal = doc["recipient_command_transcript_seal"]
    lines = [
        "# AgentPress recipient command transcript sealer (wave94)",
        "",
        f"- Status: `{doc['status']}`",
        f"- Source handoff ID: `{doc['source_handoff_id']}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Sealed transcript",
    ]
    for row in seal.get("transcript_steps", []):
        lines.append(f"- {row.get('step')}. `{row.get('command')}` => `{row.get('sealed_status')}`")
    lines.extend(["", "## Operator next command", "", f"`{seal.get('operator_next_command')}`", "", "## Blockers"])
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
    parser.add_argument("--wave93", default=DEFAULT_WAVE93)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    doc = build_seal(root, wave93_rel=args.wave93, include_pack=False)
    write_outputs(root, doc, args.out, args.markdown_out)
    if args.include_pack_check:
        doc = build_seal(root, wave93_rel=args.wave93, include_pack=True)
        write_outputs(root, doc, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    return 0 if doc["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
