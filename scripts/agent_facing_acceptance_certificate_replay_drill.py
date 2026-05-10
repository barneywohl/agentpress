#!/usr/bin/env python3
"""Replay wave73 agent-facing acceptance certificate assertions against wave72 source receipt."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CERTIFICATE = "agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.json"
SOURCE = "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json"
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-certificate-replay-drill-wave74.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-certificate-replay-drill-wave74.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_certificate_replay_drill.py"
TEST_PATH = "tests/test_agent_facing_acceptance_certificate_replay_drill.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-certificate-replay-drill"
REQUIRED_OUTPUTS = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]
REQUIRED_LANE_COUNT = 6
FORBIDDEN_PUBLIC_FIELDS = ("public_actions_taken", "external_actions")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"json_error: {exc}"
    if not isinstance(data, dict):
        return None, "json_root_not_object"
    return data, None


def package_expectations(root: Path) -> tuple[dict[str, Any], list[str]]:
    package, err = load_json(root / "package.json")
    if err or package is None:
        return {"script": "", "required": []}, [f"package_json_{err}"]
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    files = package.get("files") if isinstance(package.get("files"), list) else []
    script = scripts.get(SCRIPT_NAME, "")
    blockers: list[str] = []
    if not script:
        blockers.append(f"package_json_missing_script_{SCRIPT_NAME}")
    required = []
    generated = {DEFAULT_OUT, DEFAULT_MD}
    for rel in REQUIRED_OUTPUTS:
        item = {"path": rel, "exists_local": (root / rel).exists(), "listed_in_package_files": rel in files}
        required.append(item)
        if not item["exists_local"] and rel not in generated:
            blockers.append(f"package_required_missing_local: {rel}")
        if not item["listed_in_package_files"]:
            blockers.append(f"package_json_files_missing: {rel}")
    return {"script": script, "required": required}, blockers


def run_pack(root: Path) -> dict[str, Any]:
    proc = subprocess.run(["npm", "pack", "--dry-run", "--json"], cwd=root, text=True, capture_output=True, check=False)
    result: dict[str, Any] = {"command": "npm pack --dry-run --json", "returncode": proc.returncode, "json_parseable": False, "required_included": []}
    if proc.returncode != 0:
        result.update({"stdout": proc.stdout, "stderr": proc.stderr})
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
    result["required_included"] = [{"path": rel, "included": rel in names} for rel in REQUIRED_OUTPUTS]
    return result


def _non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def replay(root: Path, *, include_pack: bool = False) -> dict[str, Any]:
    generated_at = utc_now()
    blockers: list[str] = []
    replayed: list[str] = []

    cert_doc, cert_err = load_json(root / CERTIFICATE)
    if cert_err or cert_doc is None:
        cert_doc = {}
        blockers.append(f"missing_certificate: {CERTIFICATE}" if cert_err == "missing" else f"certificate_{cert_err}: {CERTIFICATE}")
    source_doc, source_err = load_json(root / SOURCE)
    if source_err or source_doc is None:
        source_doc = {}
        blockers.append(f"missing_source_receipt: {SOURCE}" if source_err == "missing" else f"source_{source_err}: {SOURCE}")

    operator = cert_doc.get("operator_certificate") if isinstance(cert_doc.get("operator_certificate"), dict) else {}
    source_receipt = source_doc.get("readiness_receipt") if isinstance(source_doc.get("readiness_receipt"), dict) else {}

    if cert_doc.get("status") != "ok":
        blockers.append(f"certificate_status_not_ok: {cert_doc.get('status')!r}")
    else:
        replayed.append("certificate_status_ok")
    if source_doc.get("status") != "ok":
        blockers.append(f"source_status_not_ok: {source_doc.get('status')!r}")
    else:
        replayed.append("source_status_ok")
    if cert_doc.get("blockers") not in ([], None):
        blockers.append("certificate_has_blockers")
    else:
        replayed.append("certificate_blockers_empty")
    if source_doc.get("blockers") not in ([], None):
        blockers.append("source_has_blockers")
    else:
        replayed.append("source_blockers_empty")

    cert_id = operator.get("certificate_id")
    if not isinstance(cert_id, str) or not cert_id.startswith("wave73-certificate-"):
        blockers.append("certificate_id_missing_or_invalid")
    else:
        replayed.append("certificate_id_valid")

    source_receipt_id = operator.get("source_receipt_id")
    actual_source_receipt_id = source_receipt.get("receipt_id")
    if not source_receipt_id or not actual_source_receipt_id:
        blockers.append("missing_source_receipt_id")
    elif source_receipt_id != actual_source_receipt_id:
        blockers.append("source_receipt_id_mismatch")
    else:
        replayed.append("source_receipt_id_matches")

    lane_count = operator.get("lane_count")
    if lane_count != REQUIRED_LANE_COUNT or operator.get("required_lane_count") != REQUIRED_LANE_COUNT:
        blockers.append("lane_count_mismatch")
    else:
        replayed.append("lane_count_6")
    if operator.get("all_required_lanes_verified") is not True:
        blockers.append("all_required_lanes_not_verified")
    else:
        replayed.append("all_required_lanes_verified")

    command_count = operator.get("command_count")
    if not isinstance(command_count, int) or command_count <= 0:
        blockers.append("command_count_zero_or_invalid")
    else:
        replayed.append("command_count_positive")
    commands = source_receipt.get("exact_local_commands")
    if not _non_empty_list(commands):
        blockers.append("source_exact_local_commands_missing")
    elif isinstance(command_count, int) and command_count != len(commands):
        blockers.append("command_count_source_mismatch")
    else:
        replayed.append("command_count_matches_source")

    gate_values = [operator.get("public_action_gate"), source_receipt.get("public_action_gate_state")]
    source_gate = source_doc.get("public_action_gate") if isinstance(source_doc.get("public_action_gate"), dict) else {}
    gate_values.append(source_gate.get("state"))
    if any(value != "closed_until_jake_explicit_approval" for value in gate_values):
        blockers.append("public_action_gate_not_closed")
    else:
        replayed.append("public_action_gate_closed")

    for doc_name, doc in (("certificate", cert_doc), ("source", source_doc)):
        for field in FORBIDDEN_PUBLIC_FIELDS:
            if doc.get(field) not in ([], None):
                blockers.append(f"{doc_name}_{field}_contaminated")
            else:
                replayed.append(f"{doc_name}_{field}_empty")

    package, package_blockers = package_expectations(root)
    blockers.extend(package_blockers)
    if not package_blockers:
        replayed.append("package_json_includes_wave74")

    pack = run_pack(root) if include_pack else None
    if pack:
        if pack.get("returncode") != 0 or not pack.get("json_parseable"):
            blockers.append("npm_pack_dry_run_failed")
        for item in pack.get("required_included", []):
            if not item.get("included"):
                blockers.append(f"npm_pack_missing_required: {item.get('path')}")
        if not any(str(blocker).startswith("npm_pack") for blocker in blockers):
            replayed.append("npm_pack_includes_wave74")

    return {
        "kind": "agentpress_agent_facing_acceptance_certificate_replay_drill",
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "ok" if not blockers else "blocked",
        "local_only": True,
        "certificate_id": cert_id,
        "source_receipt_id": source_receipt_id,
        "source_receipt_path": SOURCE,
        "certificate_path": CERTIFICATE,
        "lane_count": lane_count,
        "required_lane_count": REQUIRED_LANE_COUNT,
        "command_count": command_count,
        "replayed_assertion_count": len(set(replayed)),
        "replayed_assertions": sorted(set(replayed)),
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "public_action_gate": "closed_until_jake_explicit_approval",
        "public_actions_taken": [],
        "external_actions": [],
        "blockers": blockers,
    }


def write_markdown(receipt: dict[str, Any], path: Path) -> None:
    lines = [
        "# AgentPress agent-facing acceptance certificate replay drill (wave74)",
        "",
        f"- Status: `{receipt['status']}`",
        f"- Generated at: `{receipt['generated_at']}`",
        f"- Certificate: `{receipt.get('certificate_id')}`",
        f"- Source receipt: `{receipt.get('source_receipt_id')}`",
        f"- Lane count: `{receipt.get('lane_count')}/{receipt.get('required_lane_count')}`",
        f"- Command count: `{receipt.get('command_count')}`",
        f"- Replayed assertion count: `{receipt.get('replayed_assertion_count')}`",
        "- Public action gate: `closed_until_jake_explicit_approval`",
        "- Public publish/push/deploy/outreach/payment/secret access: `not executed`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Replayed assertions",
    ]
    lines.extend(f"- `{item}`" for item in receipt.get("replayed_assertions", []))
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {blocker}" for blocker in receipt["blockers"]) if receipt["blockers"] else lines.append("- None")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt = replay(root, include_pack=False)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(receipt, root / args.markdown_out)
    if args.include_pack_check:
        receipt = replay(root, include_pack=True)
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_markdown(receipt, root / args.markdown_out)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
