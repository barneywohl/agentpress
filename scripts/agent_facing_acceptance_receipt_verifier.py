#!/usr/bin/env python3
"""Verify wave72 agent-facing acceptance readiness receipt and emit wave73 certificate."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE = "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json"
GUARDRAIL = "agentpress/evidence/rc-public-action-guardrail-audit-wave52.json"
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_receipt_verifier.py"
TEST_PATH = "tests/test_agent_facing_acceptance_receipt_verifier.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-receipt-verifier"
REQUIRED_LANES = {
    "glm_gorilla_bootstrap_conveyor",
    "launchpad",
    "comms_hub",
    "marketplace",
    "safety_guardrails",
    "acceptance_harness",
}
FORBIDDEN_FRAGMENTS = [
    "git push",
    "npm publish",
    "npm dist-tag",
    "wrangler pages deploy",
    "vercel --prod",
    "gh release",
    "sendgrid",
    "discord webhook",
    "slack api",
    "payment",
    "secret access",
]
PACKAGE_REQUIRED = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]


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


def fragment_hits(values: list[str]) -> list[str]:
    text = "\n".join(values).lower()
    return sorted({frag for frag in FORBIDDEN_FRAGMENTS if frag in text})


def package_expectations(root: Path) -> tuple[dict[str, Any], list[str]]:
    package, err = load_json(root / "package.json")
    if err or package is None:
        return {"script": "", "required": []}, [f"package_json_{err}"]
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    files = package.get("files") if isinstance(package.get("files"), list) else []
    blockers: list[str] = []
    script = scripts.get(SCRIPT_NAME, "")
    if not script:
        blockers.append(f"package_json_missing_script_{SCRIPT_NAME}")
    required = []
    generated = {DEFAULT_OUT, DEFAULT_MD}
    for rel in PACKAGE_REQUIRED:
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
    result["required_included"] = [{"path": rel, "included": rel in names} for rel in PACKAGE_REQUIRED]
    return result


def certificate_id(source: dict[str, Any], generated_at: str) -> str:
    payload = json.dumps({
        "source_generated_at": source.get("generated_at"),
        "source_receipt_id": (source.get("readiness_receipt") or {}).get("receipt_id") if isinstance(source.get("readiness_receipt"), dict) else None,
        "lanes": [lane.get("id") for lane in source.get("replayed_lane_summaries", []) if isinstance(lane, dict)],
        "generated_at": generated_at,
    }, sort_keys=True).encode("utf-8")
    return "wave73-certificate-" + hashlib.sha256(payload).hexdigest()[:16]


def build_certificate(root: Path, *, include_pack: bool = False) -> dict[str, Any]:
    source, err = load_json(root / SOURCE)
    blockers: list[str] = []
    generated_at = utc_now()
    if err or source is None:
        source = {}
        blockers.append(f"wave72_source_{err}: {SOURCE}")
    else:
        if source.get("status") != "ok":
            blockers.append(f"wave72_source_status_not_ok: {source.get('status')!r}")
        if source.get("blockers") not in ([], None):
            blockers.append("wave72_source_has_blockers")
        if source.get("public_actions_taken") not in ([], None):
            blockers.append("wave72_source_records_public_actions_taken")
        if source.get("external_actions") not in ([], None):
            blockers.append("wave72_source_records_external_actions")
        gate = source.get("public_action_gate") if isinstance(source.get("public_action_gate"), dict) else {}
        if gate.get("state") != "closed_until_jake_explicit_approval":
            blockers.append(f"public_action_gate_not_closed: {gate.get('state')!r}")

    receipt = source.get("readiness_receipt") if isinstance(source.get("readiness_receipt"), dict) else None
    if not receipt:
        receipt = {}
        blockers.append("wave72_missing_readiness_receipt")
    else:
        if not str(receipt.get("receipt_id", "")).startswith("wave72-readiness-"):
            blockers.append("wave72_receipt_id_invalid")
        if receipt.get("all_required_lanes_understood") is not True:
            blockers.append("wave72_receipt_not_all_required_lanes_understood")
        if receipt.get("public_action_gate_state") != "closed_until_jake_explicit_approval":
            blockers.append("wave72_receipt_gate_not_closed")

    lanes = source.get("replayed_lane_summaries", []) if isinstance(source.get("replayed_lane_summaries"), list) else []
    lane_ids = {lane.get("id") for lane in lanes if isinstance(lane, dict)}
    missing = sorted(REQUIRED_LANES - lane_ids)
    extra = sorted(str(lane_id) for lane_id in lane_ids - REQUIRED_LANES)
    if missing:
        blockers.append(f"wave72_missing_required_lanes: {missing}")
    if extra:
        blockers.append(f"wave72_unexpected_lanes: {extra}")
    for lane in lanes:
        if not isinstance(lane, dict):
            blockers.append("wave72_lane_summary_not_object")
            continue
        if lane.get("passed") is not True:
            blockers.append(f"wave72_lane_not_passed: {lane.get('id')}")
        if not lane.get("required_sources"):
            blockers.append(f"wave72_lane_missing_required_sources: {lane.get('id')}")

    commands = receipt.get("exact_local_commands", []) if isinstance(receipt, dict) else []
    if not isinstance(commands, list) or not commands:
        commands = []
        blockers.append("wave72_receipt_missing_exact_local_commands")
    commands = [str(command) for command in commands]
    required_command_fragments = [
        "rc:agent-facing-acceptance-handoff-drill",
        "py_compile scripts/agent_facing_acceptance_handoff_drill.py",
        "pytest -q tests/test_agent_facing_acceptance_handoff_drill.py",
        "npm pack --dry-run --json",
    ]
    for fragment in required_command_fragments:
        if not any(fragment in command for command in commands):
            blockers.append(f"wave72_receipt_missing_command_fragment: {fragment}")
    hits = fragment_hits(commands)
    if hits:
        blockers.append(f"wave72_receipt_contains_forbidden_fragments: {hits}")

    guardrail, guardrail_err = load_json(root / GUARDRAIL)
    guardrail_summary = {"path": GUARDRAIL, "status": None, "loaded": guardrail_err is None}
    if guardrail_err is None and guardrail is not None:
        guardrail_summary["status"] = guardrail.get("status")
    elif guardrail_err != "missing":
        blockers.append(f"guardrail_audit_{guardrail_err}: {GUARDRAIL}")

    package, package_blockers = package_expectations(root)
    blockers.extend(package_blockers)
    pack = run_pack(root) if include_pack else None
    if pack:
        if pack.get("returncode") != 0 or not pack.get("json_parseable"):
            blockers.append("npm_pack_dry_run_failed")
        for item in pack.get("required_included", []):
            if not item.get("included"):
                blockers.append(f"npm_pack_missing_required: {item.get('path')}")

    certificate = {
        "certificate_id": certificate_id(source, generated_at),
        "source_receipt_id": receipt.get("receipt_id"),
        "lane_count": len(lane_ids & REQUIRED_LANES),
        "required_lane_count": len(REQUIRED_LANES),
        "command_count": len(commands),
        "all_required_lanes_verified": not missing and len(lane_ids & REQUIRED_LANES) == len(REQUIRED_LANES),
        "public_action_gate": "closed_until_jake_explicit_approval",
        "operator_statement": "Wave72 readiness receipt, six lane claims, local commands, package inclusion, and no-public-action boundary were verified locally only.",
    }
    if certificate["lane_count"] != certificate["required_lane_count"]:
        blockers.append("certificate_lane_count_mismatch")

    return {
        "kind": "agentpress_agent_facing_acceptance_receipt_verifier",
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "ok" if not blockers else "blocked",
        "local_only": True,
        "source_receipt": SOURCE,
        "operator_certificate": certificate,
        "verified_lane_ids": sorted(lane_ids & REQUIRED_LANES),
        "verified_command_fragments": required_command_fragments,
        "guardrail_audit_summary": guardrail_summary,
        "public_actions_taken": [],
        "external_actions": [],
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "blockers": blockers,
    }


def write_markdown(cert: dict[str, Any], path: Path) -> None:
    operator = cert["operator_certificate"]
    lines = [
        "# AgentPress agent-facing acceptance receipt verifier (wave73)",
        "",
        f"- Status: `{cert['status']}`",
        f"- Generated at: `{cert['generated_at']}`",
        f"- Certificate: `{operator['certificate_id']}`",
        f"- Source receipt: `{operator.get('source_receipt_id')}`",
        f"- Lane count: `{operator['lane_count']}/{operator['required_lane_count']}`",
        f"- Command count: `{operator['command_count']}`",
        "- Public action gate: `closed_until_jake_explicit_approval`",
        "- Public publish/push/deploy/outreach/payment/secret access: `not executed`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Verified lanes",
    ]
    lines.extend(f"- `{lane}`" for lane in cert["verified_lane_ids"])
    lines.extend(["", "## Verified command fragments"])
    lines.extend(f"- `{frag}`" for frag in cert["verified_command_fragments"])
    lines.extend(["", "## Operator statement", "", operator["operator_statement"], "", "## Blockers"])
    if cert["blockers"]:
        lines.extend(f"- {blocker}" for blocker in cert["blockers"])
    else:
        lines.append("- None")
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
    cert = build_certificate(root, include_pack=False)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cert, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(cert, root / args.markdown_out)
    if args.include_pack_check:
        cert = build_certificate(root, include_pack=True)
        out.write_text(json.dumps(cert, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_markdown(cert, root / args.markdown_out)
    if args.json:
        print(json.dumps(cert, indent=2, sort_keys=True))
    return 0 if cert["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
