#!/usr/bin/env python3
"""Convert launchpad/first-run output into a recipient-ready comms + proof handoff packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUT = "agentpress/evidence/agentpress-launchpad-comms-handoff-wave92.json"
DEFAULT_MD = "agentpress/evidence/agentpress-launchpad-comms-handoff-wave92.md"
SCRIPT_PATH = "scripts/agentpress_launchpad_comms_handoff.py"
TEST_PATH = "tests/test_agentpress_launchpad_comms_handoff.py"
SCRIPT_NAME = "rc:agentpress-launchpad-comms-handoff"
DEFAULT_LAUNCHPAD = "agentpress/onboarding/first-run-wizard.json"
DEFAULT_RECOVERY = "agentpress/evidence/agent-facing-launchpad-recovery-card-wave91.json"
DEFAULT_HARNESS = "agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.json"
FORBIDDEN_RE = re.compile(r"\b(npm\s+publish|git\s+push|deploy|payment|wallet|secret|token|outreach|email|sendgrid|external-message)\b", re.I)
LOCAL_ONLY_COMMANDS = [
    "python3 scripts/agentpress.py launchpad --json",
    "npm run rc:agent-facing-launchpad-recovery-card --silent",
    "npm run rc:agent-facing-acceptance-harness-replay-wave90 --silent",
]
PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]


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


def command_texts(*docs: dict[str, Any] | None) -> list[str]:
    texts: list[str] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        for key in ("exact_next_command", "then_command", "safe_paste_command", "recommended_next_command"):
            value = doc.get(key)
            if isinstance(value, str):
                texts.append(value)
        commands = doc.get("commands")
        if isinstance(commands, dict):
            texts.extend(str(v) for v in commands.values() if isinstance(v, str))
        elif isinstance(commands, list):
            texts.extend(str(v) for v in commands if isinstance(v, str))
        recovery = doc.get("safe_recovery_commands")
        if isinstance(recovery, list):
            texts.extend(str(v) for v in recovery if isinstance(v, str))
    return texts


def forbidden_hits(values: list[str]) -> list[str]:
    hits: set[str] = set()
    for value in values:
        for match in FORBIDDEN_RE.finditer(value or ""):
            hits.add(match.group(0).lower())
    return sorted(hits)


def package_expectations(root: Path) -> tuple[dict[str, Any], list[str]]:
    package, err = load_json(root / "package.json")
    if err or package is None:
        return {"script": "", "required": []}, [f"package_json_{err}"]
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    files = package.get("files") if isinstance(package.get("files"), list) else []
    blockers: list[str] = []
    if SCRIPT_NAME not in scripts:
        blockers.append(f"package_json_missing_script_{SCRIPT_NAME}")
    required = []
    for rel in PACKAGE_FILES:
        row = {"path": rel, "exists_local": (root / rel).exists(), "listed_in_package_files": rel in files}
        required.append(row)
        if not row["exists_local"] and rel not in {DEFAULT_OUT, DEFAULT_MD}:
            blockers.append(f"package_required_missing_local: {rel}")
        if not row["listed_in_package_files"]:
            blockers.append(f"package_json_files_missing: {rel}")
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
    names: set[str] = set()
    if isinstance(payload, list) and payload:
        for item in payload[0].get("files", []):
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                names.add(item["path"])
    for rel in PACKAGE_FILES:
        result["required_included"].append({"path": rel, "included": rel in names})
    return result


def summarize_source(root: Path, rel: str, blockers: list[str]) -> dict[str, Any]:
    doc, err = load_json(root / rel)
    if err or doc is None:
        blockers.append(f"source_{err}: {rel}")
        return {"path": rel, "status": "missing"}
    status = str(doc.get("status", "present"))
    return {"path": rel, "status": status, "keys": sorted(doc.keys())[:12], "doc": doc}


def build_packet(root: Path, *, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    launchpad = summarize_source(root, DEFAULT_LAUNCHPAD, blockers)
    recovery = summarize_source(root, DEFAULT_RECOVERY, blockers)
    harness = summarize_source(root, DEFAULT_HARNESS, blockers)
    launchpad_doc = launchpad.get("doc") if isinstance(launchpad.get("doc"), dict) else None
    recovery_doc = recovery.get("doc") if isinstance(recovery.get("doc"), dict) else None
    harness_doc = harness.get("doc") if isinstance(harness.get("doc"), dict) else None

    texts = LOCAL_ONLY_COMMANDS + command_texts(launchpad_doc, recovery_doc, harness_doc)
    unsafe = forbidden_hits(texts)
    if unsafe:
        blockers.append(f"unsafe_command_text_detected: {unsafe}")

    package, package_blockers = package_expectations(root)
    blockers.extend(package_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required: {row.get('path')}")

    handoff_id = "wave92-handoff-" + hashlib.sha256(json.dumps({"commands": LOCAL_ONLY_COMMANDS, "launchpad": launchpad.get("status"), "recovery": recovery.get("status"), "harness": harness.get("status")}, sort_keys=True).encode()).hexdigest()[:16]
    recipient_message = {
        "message_type": "agentpress_launchpad_to_comms_hub_handoff",
        "to_agent_role": "recipient_agent",
        "capability": "verify_agentpress_first_run_and_acceptance_packet",
        "task": "Use the local commands and proof refs to verify AgentPress launchpad readiness before any public action.",
        "copy_paste_commands": LOCAL_ONLY_COMMANDS,
        "proof_refs": [DEFAULT_LAUNCHPAD, DEFAULT_RECOVERY, DEFAULT_HARNESS],
        "reply_required": {"status": "ok|blocked", "evidence_path": "local proof JSON path", "blockers": []},
    }
    proof_handoff = {
        "handoff_id": handoff_id,
        "from_surface": "launchpad/first-run-wizard",
        "to_surface": "agent-comms/proof-hub",
        "recipient_ready": not blockers,
        "source_outputs": [{k: v for k, v in row.items() if k != "doc"} for row in (launchpad, recovery, harness)],
        "recipient_message": recipient_message,
    }
    return {
        "kind": "agentpress_launchpad_comms_handoff_packet",
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "ok" if not blockers else "blocked",
        "handoff_id": handoff_id,
        "local_only_commands": LOCAL_ONLY_COMMANDS,
        "comms_hub_packet": proof_handoff,
        "proof_receipt_expectations": {
            "must_include": ["handoff_id", "commands_run", "artifacts", "result_status", "redaction_attestation"],
            "public_action_gate": "closed_until_jake_explicit_approval",
            "prohibited_without_approval": ["push", "publish", "deploy", "payment", "external_message"],
        },
        "public_actions_taken": [],
        "external_actions": [],
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "blockers": blockers,
    }


def markdown(doc: dict[str, Any]) -> str:
    lines = [
        "# AgentPress launchpad → comms handoff packet (wave92)",
        "",
        f"- Status: `{doc['status']}`",
        f"- Handoff ID: `{doc['handoff_id']}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Local-only commands",
    ]
    lines.extend([f"- `{cmd}`" for cmd in doc.get("local_only_commands", [])])
    lines.extend(["", "## Proof refs"])
    for ref in doc["comms_hub_packet"]["proof_handoff" if False else "proof_refs"] if False else doc["comms_hub_packet"].get("source_outputs", []):
        if isinstance(ref, dict):
            lines.append(f"- `{ref.get('path')}` status `{ref.get('status')}`")
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
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    doc = build_packet(root, include_pack=False)
    write_outputs(root, doc, args.out, args.markdown_out)
    if args.include_pack_check:
        doc = build_packet(root, include_pack=True)
        write_outputs(root, doc, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    return 0 if doc["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
