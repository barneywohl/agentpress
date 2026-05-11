#!/usr/bin/env python3
"""Build a local-only AgentPress marketplace fulfillment packet from a verified acknowledgement."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ACK = "agentpress/evidence/agentpress-gorilla-operator-acknowledgement-verifier-wave104.json"
DEFAULT_OUT = "agentpress/evidence/agentpress-marketplace-acknowledged-fulfillment-packet-wave105.json"
DEFAULT_MD = "agentpress/evidence/agentpress-marketplace-acknowledged-fulfillment-packet-wave105.md"
SCRIPT_PATH = "scripts/agentpress_marketplace_acknowledged_fulfillment_packet.py"
TEST_PATH = "tests/test_agentpress_marketplace_acknowledged_fulfillment_packet.py"
SCRIPT_NAME = "rc:agentpress-marketplace-acknowledged-fulfillment-packet"
PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD, DEFAULT_ACK]
GENERATED = {DEFAULT_OUT, DEFAULT_MD}
UNSAFE = re.compile(r"\b(push|publish|deploy|payment|wallet|external[-_ ]?send|outreach|email|curl\s+https?://|wget\s+https?://)\b|https?://", re.I)
SECRET = re.compile(r"(secret|token|password|api[_-]?key)", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # noqa: BLE001
        return None, f"json_error:{exc}"


def local_rel(value: str) -> bool:
    if not value or UNSAFE.search(value) or SECRET.search(value):
        return False
    p = Path(value)
    return not p.is_absolute() and ".." not in p.parts


def safe_freeform(value: Any) -> bool:
    return not UNSAFE.search(str(value)) and not SECRET.search(str(value))


def acknowledgement_ok(source: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    ack = source.get("sample_operator_acknowledgement") if isinstance(source.get("sample_operator_acknowledgement"), dict) else {}
    if source.get("status") != "ok":
        blockers.append("source_ack_verifier_not_ok")
    if source.get("public_push_publish_deploy") is not False or source.get("jake_explicit_approval_required_for_public_actions") is not True:
        blockers.append("source_public_action_gate_not_preserved")
    if source.get("external_actions") not in ([], None):
        blockers.append("source_external_actions_present")
    if source.get("payment_actions_taken") not in ([], None):
        blockers.append("source_payment_actions_present")
    required = ["operator_agent_id", "operator_acknowledged_first_command", "first_command_exit_code", "criteria_checked", "generated_local_artifacts"]
    for key in required:
        if key not in ack or ack[key] in (None, "", []):
            blockers.append(f"ack_missing:{key}")
    if ack.get("operator_acknowledged_first_command") is not True:
        blockers.append("ack_first_command_not_acknowledged")
    if ack.get("first_command_exit_code") != 0:
        blockers.append("ack_first_command_nonzero")
    for artifact in ack.get("generated_local_artifacts", []) if isinstance(ack.get("generated_local_artifacts"), list) else []:
        if not isinstance(artifact, str) or not local_rel(artifact):
            blockers.append(f"ack_artifact_not_local:{artifact}")
    for key in ["operator_agent_id", "first_command_stdout_tail", "first_command_stderr_tail", "operator_note"]:
        if key in ack and not safe_freeform(ack[key]):
            blockers.append(f"ack_unsafe_freeform:{key}")
    return ack, blockers


def package_check(root: Path) -> tuple[dict[str, Any], list[str]]:
    pkg, err = load_json(root / "package.json")
    if err or not isinstance(pkg, dict):
        return {"script": "", "required": []}, [f"package_json_{err}"]
    scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
    files = pkg.get("files") if isinstance(pkg.get("files"), list) else []
    blockers: list[str] = []
    if SCRIPT_NAME not in scripts:
        blockers.append(f"package_json_missing_script:{SCRIPT_NAME}")
    required: list[dict[str, Any]] = []
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


def build_packet(root: Path, *, ack_rel: str = DEFAULT_ACK, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    source, err = load_json(root / ack_rel)
    if err or not isinstance(source, dict):
        source = {}
        blockers.append(f"source_ack_{err}:{ack_rel}")
    if not local_rel(ack_rel):
        blockers.append(f"source_ack_path_not_local:{ack_rel}")
    ack, ack_blockers = acknowledgement_ok(source)
    blockers.extend(ack_blockers)

    fulfillment_packet = {
        "packet_id": "wave105-marketplace-acknowledged-fulfillment-packet",
        "recipient_agent_id": ack.get("operator_agent_id", "local-recipient-agent"),
        "source_acknowledgement": ack_rel,
        "marketplace_listing_ref": "local://agentpress/marketplace/gorilla-launchpad-fulfillment",
        "fulfillment_mode": "local_only_trust_checked",
        "fulfilled_capabilities": [
            "operator acknowledgement verified",
            "first-command local run acknowledged",
            "acceptance criteria mirrored into marketplace packet",
            "local artifacts sealed for reviewer handoff",
        ],
        "local_artifacts": list(ack.get("generated_local_artifacts", [])) + [DEFAULT_OUT, DEFAULT_MD],
        "trust_checks": [
            {"name": "source-verifier-ok", "ok": source.get("status") == "ok"},
            {"name": "operator-acknowledged-first-command", "ok": ack.get("operator_acknowledged_first_command") is True},
            {"name": "first-command-exit-zero", "ok": ack.get("first_command_exit_code") == 0},
            {"name": "local-artifacts-only", "ok": all(isinstance(a, str) and local_rel(a) for a in ack.get("generated_local_artifacts", []))},
            {"name": "no-public-or-payment-action", "ok": True},
        ],
        "reviewer_handoff_commands": [
            "python3 scripts/agentpress_marketplace_acknowledged_fulfillment_packet.py . --json",
            "python3 -m pytest tests/test_agentpress_marketplace_acknowledged_fulfillment_packet.py -q",
        ],
    }
    for row in fulfillment_packet["trust_checks"]:
        if not row["ok"]:
            blockers.append(f"trust_check_failed:{row['name']}")
    if not safe_freeform(fulfillment_packet["marketplace_listing_ref"]):
        blockers.append("marketplace_listing_ref_not_local_safe")

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
        "schema_version": "2026-05-11.agentpress-marketplace-acknowledged-fulfillment-packet.v1",
        "generated_utc": utc_now(),
        "status": "ok" if not blockers else "blocked",
        "wave": "wave105_marketplace_acknowledged_fulfillment_packet",
        "source_inputs": [ack_rel],
        "agent_facing_value": "Agents can convert a verified Gorilla operator acknowledgement into a trust-checked local marketplace fulfillment packet without public publish, payment, external send, or secret access.",
        "public_push_publish_deploy": False,
        "external_actions": [],
        "payment_actions_taken": [],
        "secret_material_included": False,
        "jake_explicit_approval_required_for_public_actions": True,
        "fulfillment_packet": fulfillment_packet,
        "failure_stop_rules": [
            "Stop if the source acknowledgement verifier is not status ok.",
            "Stop if the operator acknowledgement did not run/acknowledge the first command with exit code 0.",
            "Stop if any fulfillment artifact is not a relative local path.",
            "Stop before public publish, marketplace payment, external send, URL fetch, push, deploy, or secret access without Jake approval.",
        ],
        "handoff_ready_artifacts": [DEFAULT_OUT, DEFAULT_MD, ack_rel],
        "package": package,
        "pack_check": pack,
        "blockers": blockers,
    }


def write_markdown(path: Path, data: dict[str, Any]) -> None:
    checks = "\n".join(f"- {row['name']}: `{row['ok']}`" for row in data["fulfillment_packet"]["trust_checks"])
    artifacts = "\n".join(f"- `{item}`" for item in data["handoff_ready_artifacts"])
    stops = "\n".join(f"- {item}" for item in data["failure_stop_rules"])
    blockers = "\n".join(f"- {item}" for item in data["blockers"]) if data["blockers"] else "- none"
    path.write_text(
        "# AgentPress marketplace acknowledged fulfillment packet\n\n"
        f"- Status: `{data['status']}`\n"
        f"- Wave: `{data['wave']}`\n"
        f"- Public push/publish/deploy: `{data['public_push_publish_deploy']}`; Jake approval required: `{data['jake_explicit_approval_required_for_public_actions']}`\n\n"
        "## Trust checks\n"
        f"{checks}\n\n"
        "## Handoff-ready artifacts\n"
        f"{artifacts}\n\n"
        "## Failure-stop rules\n"
        f"{stops}\n\n"
        "## Blockers\n"
        f"{blockers}\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--source", default=DEFAULT_ACK)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    data = build_packet(root, ack_rel=args.source, include_pack=args.include_pack_check)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(root / args.markdown_out, data)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    return 0 if data["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
