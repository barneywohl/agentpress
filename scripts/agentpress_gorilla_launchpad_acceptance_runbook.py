#!/usr/bin/env python3
"""Build a local-only Gorilla launchpad acceptance runbook from the wave102 packet."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PACKET = "agentpress/evidence/agentpress-gorilla-receipt-acceptance-launchpad-packet-wave102.json"
DEFAULT_VERIFIER = "agentpress/evidence/agentpress-gorilla-evidence-receipt-verifier-wave101.json"
DEFAULT_DRILL = "agentpress/evidence/agentpress-gorilla-launchpad-first-run-drill-wave99.json"
DEFAULT_OUT = "agentpress/evidence/agentpress-gorilla-launchpad-acceptance-runbook-wave103.json"
DEFAULT_MD = "agentpress/evidence/agentpress-gorilla-launchpad-acceptance-runbook-wave103.md"
SCRIPT_PATH = "scripts/agentpress_gorilla_launchpad_acceptance_runbook.py"
TEST_PATH = "tests/test_agentpress_gorilla_launchpad_acceptance_runbook.py"
SCRIPT_NAME = "rc:agentpress-gorilla-launchpad-acceptance-runbook"
PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD, DEFAULT_PACKET, DEFAULT_VERIFIER, DEFAULT_DRILL]
GENERATED = {DEFAULT_OUT, DEFAULT_MD}
PUBLIC_ACTIONS = re.compile(r"\b(push|publish|deploy|payment|wallet|external[-_ ]?send|outreach|email|curl\s+https?://|wget\s+https?://)\b", re.I)
SECRET_OR_EXTERNAL = re.compile(r"(https?://|secret|token|password|api[_-]?key)", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # noqa: BLE001
        return None, f"json_error:{exc}"


def local_path_ok(path: str) -> bool:
    if not path or SECRET_OR_EXTERNAL.search(path):
        return False
    p = Path(path)
    return not p.is_absolute() and ".." not in p.parts


def safe_command(command: str) -> bool:
    return bool(command.strip()) and not PUBLIC_ACTIONS.search(command) and not SECRET_OR_EXTERNAL.search(command)


def package_check(root: Path) -> tuple[dict[str, Any], list[str]]:
    pkg, err = load_json(root / "package.json")
    if err or not isinstance(pkg, dict):
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


def build_operator_acknowledgement_fields(packet: dict[str, Any]) -> list[dict[str, Any]]:
    fields = [
        ("operator_agent_id", "string", True, "Agent/runtime accepting the Gorilla launchpad handoff."),
        ("operator_acknowledged_first_command", "boolean", True, "True only after the first command is inspected and run locally."),
        ("first_command_exit_code", "integer", True, "Exit code from the first local command."),
        ("first_command_stdout_tail", "string", True, "Short local stdout tail; redact secrets if accidentally present."),
        ("first_command_stderr_tail", "string", False, "Short local stderr tail if present."),
        ("criteria_checked", "array[string]", True, "Acceptance criteria from this runbook that were checked."),
        ("generated_local_artifacts", "array[string]", True, "Relative local artifact paths produced by the drill."),
        ("stop_reason_if_blocked", "string", False, "Required when any failure-stop rule fires."),
        ("operator_note", "string", False, "Human/agent note for the handoff."),
    ]
    receipt_fields = packet.get("launchpad", {}).get("recipient_proof_fields", [])
    return [{"name": name, "type": typ, "required": required, "description": desc, "mirrors_wave102_recipient_field": name in receipt_fields} for name, typ, required, desc in fields]


def build_runbook(root: Path, *, packet_rel: str = DEFAULT_PACKET, verifier_rel: str = DEFAULT_VERIFIER, drill_rel: str = DEFAULT_DRILL, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    packet, packet_err = load_json(root / packet_rel)
    verifier, verifier_err = load_json(root / verifier_rel)
    drill, drill_err = load_json(root / drill_rel)
    if packet_err or not isinstance(packet, dict):
        packet = {}
        blockers.append(f"packet_{packet_err}:{packet_rel}")
    if verifier_err or not isinstance(verifier, dict):
        verifier = {}
        blockers.append(f"verifier_{verifier_err}:{verifier_rel}")
    if drill_err or not isinstance(drill, dict):
        drill = {}
        blockers.append(f"drill_{drill_err}:{drill_rel}")

    launchpad = packet.get("launchpad") if isinstance(packet.get("launchpad"), dict) else {}
    first_command = str(launchpad.get("first_command", "")).strip()
    if packet.get("status") != "ok":
        blockers.append("source_wave102_packet_not_ok")
    if packet.get("public_push_publish_deploy") is not False or packet.get("jake_explicit_approval_required_for_public_actions") is not True:
        blockers.append("source_public_gate_not_preserved")
    if verifier.get("status") != "ok" or verifier.get("acceptance_summary", {}).get("all_steps_verified") is not True:
        blockers.append("source_verifier_not_fully_accepted")
    if drill.get("status") != "ok":
        blockers.append("source_drill_not_ok")
    if not safe_command(first_command):
        blockers.append("first_command_not_local_safe")

    source_inputs = [packet_rel, verifier_rel, drill_rel]
    for artifact in [DEFAULT_OUT, DEFAULT_MD, *source_inputs]:
        if not local_path_ok(artifact):
            blockers.append(f"artifact_path_not_local:{artifact}")

    acceptance_criteria = list(launchpad.get("acceptance_criteria", [])) if isinstance(launchpad.get("acceptance_criteria"), list) else []
    failure_stop_rules = list(launchpad.get("failure_stop_rules", [])) if isinstance(launchpad.get("failure_stop_rules"), list) else []
    runbook_steps = [
        {"step": 1, "name": "inspect-boundaries", "instruction": "Confirm this is local-only: no push, publish, deploy, payment, external send, URL fetch, or secret request is allowed without Jake approval.", "expected": "public_push_publish_deploy is false and Jake approval gate is true"},
        {"step": 2, "name": "run-first-command", "instruction": "Run exactly the first command below from the repo root and capture exit code/stdout/stderr locally.", "command": first_command, "expected": launchpad.get("first_command_expected_result", "exit_code=0 and local-only output")},
        {"step": 3, "name": "check-acceptance-criteria", "instruction": "Mark each acceptance criterion checked; stop and record a blocker if any criterion fails.", "criteria": acceptance_criteria},
        {"step": 4, "name": "record-operator-acknowledgement", "instruction": "Fill the acknowledgement fields and attach only relative local artifact paths.", "fields": build_operator_acknowledgement_fields(packet)},
        {"step": 5, "name": "handoff-json-markdown", "instruction": "Attach this JSON and Markdown runbook plus the wave102 packet to the next local handoff.", "artifacts": [DEFAULT_OUT, DEFAULT_MD, packet_rel]},
    ]
    ack_template = {field["name"]: ([] if field["type"].startswith("array") else (False if field["type"] == "boolean" else None)) for field in build_operator_acknowledgement_fields(packet)}

    package, package_blockers = package_check(root)
    blockers.extend(package_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required:{row.get('path')}")

    return {
        "schema_version": "2026-05-11.agentpress-gorilla-launchpad-acceptance-runbook.v1",
        "generated_utc": utc_now(),
        "runbook_id": "wave103-gorilla-launchpad-acceptance-runbook",
        "status": "ok" if not blockers else "blocked",
        "source_inputs": source_inputs,
        "public_push_publish_deploy": False,
        "external_actions": [],
        "payment_actions_taken": [],
        "secret_material_included": False,
        "jake_explicit_approval_required_for_public_actions": True,
        "agent_facing_value": "A recipient agent can follow one local first command, verify receipt acceptance criteria, record operator acknowledgement, and hand off JSON/Markdown proof without public actions.",
        "one_first_command": first_command,
        "runbook_steps": runbook_steps,
        "acceptance_criteria": acceptance_criteria,
        "failure_stop_rules": failure_stop_rules,
        "operator_acknowledgement_fields": build_operator_acknowledgement_fields(packet),
        "operator_acknowledgement_template": ack_template,
        "handoff_ready_artifacts": [DEFAULT_OUT, DEFAULT_MD, packet_rel],
        "package": package,
        "pack_check": pack,
        "blockers": blockers,
    }


def write_markdown(path: Path, data: dict[str, Any]) -> None:
    steps = "\n".join(f"{step['step']}. **{step['name']}** — {step['instruction']}" + (f"\n   - Command: `{step['command']}`" if step.get("command") else "") for step in data["runbook_steps"])
    criteria = "\n".join(f"- {item}" for item in data["acceptance_criteria"])
    stops = "\n".join(f"- {item}" for item in data["failure_stop_rules"])
    fields = "\n".join(f"- `{field['name']}` ({field['type']}, required={field['required']}): {field['description']}" for field in data["operator_acknowledgement_fields"])
    artifacts = "\n".join(f"- `{item}`" for item in data["handoff_ready_artifacts"])
    blockers = "\n".join(f"- {b}" for b in data["blockers"]) if data["blockers"] else "- none"
    path.write_text(
        "# AgentPress Gorilla launchpad acceptance runbook\n\n"
        f"- Status: `{data['status']}`\n"
        f"- Runbook: `{data['runbook_id']}`\n"
        f"- One first command: `{data['one_first_command']}`\n"
        f"- Public push/publish/deploy: `{data['public_push_publish_deploy']}`; Jake approval required: `{data['jake_explicit_approval_required_for_public_actions']}`\n\n"
        "## Runbook steps\n"
        f"{steps}\n\n"
        "## Acceptance criteria\n"
        f"{criteria}\n\n"
        "## Failure-stop rules\n"
        f"{stops}\n\n"
        "## Operator acknowledgement fields\n"
        f"{fields}\n\n"
        "## Handoff-ready artifacts\n"
        f"{artifacts}\n\n"
        "## Blockers\n"
        f"{blockers}\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    out = root / args.out if not Path(args.out).is_absolute() else Path(args.out)
    md = root / args.markdown_out if not Path(args.markdown_out).is_absolute() else Path(args.markdown_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    md.parent.mkdir(parents=True, exist_ok=True)
    # Seed the generated artifacts before the optional npm-pack check so exact package.json
    # file entries for this wave can be observed by `npm pack --dry-run --json`.
    data = build_runbook(root, include_pack=False)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(md, data)
    if args.include_pack_check:
        data = build_runbook(root, include_pack=True)
        out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_markdown(md, data)
    if args.json:
        print(json.dumps({"status": data["status"], "out": str(out), "markdown_out": str(md), "blockers": data["blockers"]}, sort_keys=True))
    return 0 if data["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
