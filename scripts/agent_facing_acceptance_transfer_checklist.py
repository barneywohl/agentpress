#!/usr/bin/env python3
"""Generate a fresh-agent transfer checklist from wave70-74 acceptance evidence."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WAVE74 = "agentpress/evidence/agent-facing-acceptance-certificate-replay-drill-wave74.json"
WAVE73 = "agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.json"
WAVE72 = "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json"
WAVE71 = "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json"
WAVE70 = "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json"
REQUIRED_INPUTS = [WAVE74, WAVE73, WAVE72, WAVE71, WAVE70]
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-transfer-checklist-wave75.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-transfer-checklist-wave75.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_transfer_checklist.py"
TEST_PATH = "tests/test_agent_facing_acceptance_transfer_checklist.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-transfer-checklist"
REQUIRED_OUTPUTS = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]
REQUIRED_LANE_COUNT = 6
FORBIDDEN_PUBLIC_FIELDS = ("public_actions_taken", "external_actions")
GATE_CLOSED = "closed_until_jake_explicit_approval"


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


def _gate_state(doc: dict[str, Any]) -> str | None:
    gate = doc.get("public_action_gate")
    if isinstance(gate, dict):
        return gate.get("state")
    if isinstance(gate, str):
        return gate
    receipt = doc.get("readiness_receipt")
    if isinstance(receipt, dict):
        return receipt.get("public_action_gate_state")
    operator = doc.get("operator_certificate")
    if isinstance(operator, dict):
        return operator.get("public_action_gate")
    return None


def _lane_count(doc: dict[str, Any]) -> int | None:
    if isinstance(doc.get("lane_count"), int):
        return doc["lane_count"]
    operator = doc.get("operator_certificate")
    if isinstance(operator, dict) and isinstance(operator.get("lane_count"), int):
        return operator["lane_count"]
    receipt = doc.get("readiness_receipt")
    if isinstance(receipt, dict) and isinstance(receipt.get("understood_lane_count"), int):
        return receipt["understood_lane_count"]
    coverage = doc.get("coverage")
    if isinstance(coverage, dict) and isinstance(coverage.get("covered_lane_ids"), list):
        return len(coverage["covered_lane_ids"])
    lanes = doc.get("lanes")
    if isinstance(lanes, list):
        return len(lanes)
    return None


def _commands(doc: dict[str, Any]) -> list[Any]:
    for key in ("exact_local_verification_commands", "verified_command_fragments"):
        if isinstance(doc.get(key), list):
            return doc[key]
    receipt = doc.get("readiness_receipt")
    if isinstance(receipt, dict) and isinstance(receipt.get("exact_local_commands"), list):
        return receipt["exact_local_commands"]
    return []


def build_transfer_checklist(root: Path, *, include_pack: bool = False) -> dict[str, Any]:
    generated_at = utc_now()
    blockers: list[str] = []
    inputs: dict[str, dict[str, Any]] = {}
    docs: dict[str, dict[str, Any]] = {}

    for rel in REQUIRED_INPUTS:
        doc, err = load_json(root / rel)
        name = Path(rel).stem
        if err or doc is None:
            inputs[name] = {"path": rel, "loaded": False, "error": err}
            blockers.append(f"missing_prior_artifact: {rel}" if err == "missing" else f"prior_artifact_{err}: {rel}")
            docs[name] = {}
        else:
            inputs[name] = {"path": rel, "loaded": True, "status": doc.get("status")}
            docs[name] = doc

    certificate_id = docs.get(Path(WAVE74).stem, {}).get("certificate_id")
    source_receipt_id = docs.get(Path(WAVE74).stem, {}).get("source_receipt_id")
    command_count = docs.get(Path(WAVE74).stem, {}).get("command_count")
    replayed_assertion_count = docs.get(Path(WAVE74).stem, {}).get("replayed_assertion_count")

    lane_sources: dict[str, int | None] = {}
    command_sources: dict[str, int] = {}
    for rel in REQUIRED_INPUTS:
        name = Path(rel).stem
        doc = docs.get(name, {})
        if not doc:
            continue
        if doc.get("status") != "ok":
            blockers.append(f"prior_artifact_status_not_ok: {rel}: {doc.get('status')!r}")
        if doc.get("blockers") not in ([], None):
            blockers.append(f"prior_artifact_has_blockers: {rel}")
        for field in FORBIDDEN_PUBLIC_FIELDS:
            if doc.get(field) not in ([], None):
                blockers.append(f"prior_artifact_{field}_contaminated: {rel}")
        gate_state = _gate_state(doc)
        if gate_state is not None and gate_state != GATE_CLOSED:
            blockers.append(f"prior_artifact_public_gate_open: {rel}: {gate_state!r}")
        lane_sources[name] = _lane_count(doc)
        commands = _commands(doc)
        if commands:
            command_sources[name] = len(commands)

    if not isinstance(certificate_id, str) or not certificate_id.startswith("wave73-certificate-"):
        blockers.append("certificate_id_missing_or_invalid")
    if not isinstance(source_receipt_id, str) or not source_receipt_id.startswith("wave72-readiness-"):
        blockers.append("source_receipt_id_missing_or_invalid")
    if not isinstance(command_count, int) or command_count <= 0:
        blockers.append("command_count_zero_or_invalid")
    if not isinstance(replayed_assertion_count, int) or replayed_assertion_count <= 0:
        blockers.append("replayed_assertion_count_zero_or_invalid")

    lane_values = {name: value for name, value in lane_sources.items() if value is not None}
    if len(lane_values) != len(REQUIRED_INPUTS):
        blockers.append("lane_count_missing_from_prior_artifact")
    if any(value != REQUIRED_LANE_COUNT for value in lane_values.values()):
        blockers.append("lane_count_mismatch")

    transfer_steps = [
        {"step": 1, "lane": "evidence_inventory", "action": "Verify wave70-74 artifacts are present, JSON-parseable, status ok, and blocker-free."},
        {"step": 2, "lane": "certificate_replay", "action": "Use the wave74 replay drill to recover the wave73 certificate and wave72 source receipt ids."},
        {"step": 3, "lane": "harness_matrix", "action": "Read wave70 coverage and confirm all six acceptance lanes are represented."},
        {"step": 4, "lane": "operator_capsule", "action": "Follow wave71 copy-paste instructions and exact local verification commands only."},
        {"step": 5, "lane": "handoff_receipt", "action": "Use wave72 readiness receipt commands as the transfer verification path."},
        {"step": 6, "lane": "package_gate", "action": "Confirm package files include this script, test, JSON evidence, and Markdown evidence without public actions."},
    ]

    package, package_blockers = package_expectations(root)
    blockers.extend(package_blockers)
    pack = run_pack(root) if include_pack else None
    if pack:
        if pack.get("returncode") != 0 or not pack.get("json_parseable"):
            blockers.append("npm_pack_dry_run_failed")
        for item in pack.get("required_included", []):
            if not item.get("included"):
                blockers.append(f"npm_pack_missing_required: {item.get('path')}")

    return {
        "kind": "agentpress_agent_facing_acceptance_transfer_checklist",
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "ok" if not blockers else "blocked",
        "local_only": True,
        "certificate_id": certificate_id,
        "source_receipt_id": source_receipt_id,
        "lane_count": REQUIRED_LANE_COUNT if not any(value != REQUIRED_LANE_COUNT for value in lane_values.values()) else None,
        "required_lane_count": REQUIRED_LANE_COUNT,
        "lane_sources": lane_sources,
        "command_count": command_count,
        "command_source_counts": command_sources,
        "replayed_assertion_count": replayed_assertion_count,
        "transfer_step_count": len(transfer_steps),
        "transfer_steps": transfer_steps,
        "prior_artifacts": inputs,
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "public_action_gate": GATE_CLOSED,
        "public_actions_taken": [],
        "external_actions": [],
        "blockers": blockers,
    }


def write_markdown(receipt: dict[str, Any], path: Path) -> None:
    lines = [
        "# AgentPress agent-facing acceptance transfer checklist (wave75)",
        "",
        f"- Status: `{receipt['status']}`",
        f"- Generated at: `{receipt['generated_at']}`",
        f"- Certificate: `{receipt.get('certificate_id')}`",
        f"- Source receipt: `{receipt.get('source_receipt_id')}`",
        f"- Lane count: `{receipt.get('lane_count')}/{receipt.get('required_lane_count')}`",
        f"- Command count: `{receipt.get('command_count')}`",
        f"- Replayed assertion count: `{receipt.get('replayed_assertion_count')}`",
        f"- Transfer step count: `{receipt.get('transfer_step_count')}`",
        "- Public action gate: `closed_until_jake_explicit_approval`",
        "- Public publish/push/deploy/outreach/payment/secret access: `not executed`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Transfer steps",
    ]
    lines.extend(f"{step['step']}. `{step['lane']}` — {step['action']}" for step in receipt.get("transfer_steps", []))
    lines.extend(["", "## Prior artifacts"])
    for item in receipt.get("prior_artifacts", {}).values():
        lines.append(f"- `{item.get('path')}` loaded={item.get('loaded')} status={item.get('status')}")
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
    receipt = build_transfer_checklist(root, include_pack=False)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(receipt, root / args.markdown_out)
    if args.include_pack_check:
        receipt = build_transfer_checklist(root, include_pack=True)
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_markdown(receipt, root / args.markdown_out)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
