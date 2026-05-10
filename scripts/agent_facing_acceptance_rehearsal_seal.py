#!/usr/bin/env python3
"""Seal the wave76 recipient rehearsal against wave75 and wave70-74 evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WAVE76 = "agentpress/evidence/agent-facing-acceptance-recipient-rehearsal-wave76.json"
WAVE75 = "agentpress/evidence/agent-facing-acceptance-transfer-checklist-wave75.json"
WAVE74 = "agentpress/evidence/agent-facing-acceptance-certificate-replay-drill-wave74.json"
WAVE73 = "agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.json"
WAVE72 = "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json"
WAVE71 = "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json"
WAVE70 = "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json"
REQUIRED_INPUTS = [WAVE76, WAVE75, WAVE74, WAVE73, WAVE72, WAVE71, WAVE70]
SOURCE_INPUTS = [WAVE75, WAVE74, WAVE73, WAVE72, WAVE71, WAVE70]
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-rehearsal-seal-wave77.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-rehearsal-seal-wave77.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_rehearsal_seal.py"
TEST_PATH = "tests/test_agent_facing_acceptance_rehearsal_seal.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-rehearsal-seal"
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
    commands: list[Any] = []
    for key in ("exact_local_verification_commands", "verified_command_fragments"):
        if isinstance(doc.get(key), list):
            commands.extend(doc[key])
    receipt = doc.get("readiness_receipt")
    if isinstance(receipt, dict) and isinstance(receipt.get("exact_local_commands"), list):
        commands.extend(receipt["exact_local_commands"])
    if isinstance(doc.get("package_json_inclusion_expectations"), dict):
        script = doc["package_json_inclusion_expectations"].get("script")
        if isinstance(script, str) and script:
            commands.append(script)
    return commands


def _validate_common(rel: str, doc: dict[str, Any], blockers: list[str]) -> None:
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


def build_rehearsal_seal(root: Path, *, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    inputs: dict[str, dict[str, Any]] = {}
    docs: dict[str, dict[str, Any]] = {}
    for rel in REQUIRED_INPUTS:
        doc, err = load_json(root / rel)
        name = Path(rel).stem
        if err or doc is None:
            label = "missing_wave76_recipient_rehearsal" if rel == WAVE76 and err == "missing" else "missing_prior_artifact"
            blockers.append(f"{label}: {rel}" if err == "missing" else f"prior_artifact_{err}: {rel}")
            inputs[name] = {"path": rel, "loaded": False, "error": err}
            docs[name] = {}
        else:
            inputs[name] = {"path": rel, "loaded": True, "status": doc.get("status")}
            docs[name] = doc

    wave76 = docs.get(Path(WAVE76).stem, {})
    wave75 = docs.get(Path(WAVE75).stem, {})
    for rel in REQUIRED_INPUTS:
        doc = docs.get(Path(rel).stem, {})
        if doc:
            _validate_common(rel, doc, blockers)

    certificate_id = wave76.get("certificate_id")
    source_receipt_id = wave76.get("source_receipt_id")
    lane_count = wave76.get("lane_count")
    command_count = wave76.get("command_count")
    transfer_step_count = wave76.get("transfer_step_count")
    rehearsed_step_count = wave76.get("rehearsed_step_count")
    rehearsed_lane_count = wave76.get("rehearsed_lane_count")

    if wave76:
        if lane_count != REQUIRED_LANE_COUNT:
            blockers.append("wave76_lane_count_mismatch")
        if transfer_step_count != REQUIRED_LANE_COUNT:
            blockers.append("wave76_transfer_step_count_mismatch")
        if rehearsed_step_count != REQUIRED_LANE_COUNT or rehearsed_lane_count != REQUIRED_LANE_COUNT:
            blockers.append("wave76_rehearsal_count_mismatch")
        if not isinstance(certificate_id, str) or not certificate_id.startswith("wave73-certificate-"):
            blockers.append("certificate_id_missing_or_invalid")
        if not isinstance(source_receipt_id, str) or not source_receipt_id.startswith("wave72-readiness-"):
            blockers.append("source_receipt_id_missing_or_invalid")
        if not isinstance(command_count, int) or command_count <= 0:
            blockers.append("command_count_zero_or_invalid")
        pkg = wave76.get("package_json_inclusion_expectations")
        required = pkg.get("required", []) if isinstance(pkg, dict) else []
        if not required or any(not item.get("listed_in_package_files") for item in required if isinstance(item, dict)):
            blockers.append("wave76_package_incomplete")
        pack = wave76.get("npm_pack_dry_run")
        included = pack.get("required_included", []) if isinstance(pack, dict) else []
        if not included or any(not item.get("included") for item in included if isinstance(item, dict)):
            blockers.append("wave76_npm_pack_incomplete")

    cross_checks: dict[str, Any] = {}
    if wave75:
        for field in ("certificate_id", "source_receipt_id", "lane_count", "command_count", "transfer_step_count"):
            source = wave75.get(field)
            target = wave76.get(field)
            ok = source == target
            cross_checks[f"wave76_matches_wave75_{field}"] = {"ok": ok, "wave76": target, "wave75": source}
            if not ok:
                blockers.append(f"wave76_wave75_{field}_mismatch")

    lane_sources: dict[str, int | None] = {}
    command_sources: dict[str, int] = {}
    for rel in SOURCE_INPUTS:
        doc = docs.get(Path(rel).stem, {})
        if not doc:
            continue
        lane_sources[Path(rel).stem] = _lane_count(doc)
        commands = _commands(doc)
        if commands:
            command_sources[Path(rel).stem] = len(commands)
    known_lanes = {name: value for name, value in lane_sources.items() if value is not None}
    if len(known_lanes) != len(SOURCE_INPUTS):
        blockers.append("lane_count_missing_from_prior_artifact")
    if any(value != REQUIRED_LANE_COUNT for value in known_lanes.values()):
        blockers.append("lane_count_mismatch")

    package, package_blockers = package_expectations(root)
    blockers.extend(package_blockers)
    pack_result = run_pack(root) if include_pack else None
    if pack_result:
        if pack_result.get("returncode") != 0 or not pack_result.get("json_parseable"):
            blockers.append("npm_pack_dry_run_failed")
        for item in pack_result.get("required_included", []):
            if not item.get("included"):
                blockers.append(f"npm_pack_missing_required: {item.get('path')}")

    seal_basis = json.dumps({"certificate_id": certificate_id, "source_receipt_id": source_receipt_id, "lane_count": lane_count, "command_count": command_count, "rehearsed_step_count": rehearsed_step_count}, sort_keys=True)
    seal_id = "wave77-seal-" + hashlib.sha256(seal_basis.encode("utf-8")).hexdigest()[:16]
    return {
        "kind": "agentpress_agent_facing_acceptance_rehearsal_seal",
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "ok" if not blockers else "blocked",
        "local_only": True,
        "seal_id": seal_id,
        "sealed_by_evidence": True,
        "certificate_id": certificate_id,
        "source_receipt_id": source_receipt_id,
        "lane_count": lane_count if lane_count == REQUIRED_LANE_COUNT else None,
        "required_lane_count": REQUIRED_LANE_COUNT,
        "command_count": command_count,
        "transfer_step_count": transfer_step_count,
        "rehearsed_step_count": rehearsed_step_count,
        "rehearsed_lane_count": rehearsed_lane_count,
        "cross_checks": cross_checks,
        "lane_sources": lane_sources,
        "command_source_counts": command_sources,
        "prior_artifacts": inputs,
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack_result,
        "public_action_gate": GATE_CLOSED,
        "public_actions_taken": [],
        "external_actions": [],
        "blockers": blockers,
    }


def write_markdown(receipt: dict[str, Any], path: Path) -> None:
    lines = [
        "# AgentPress agent-facing acceptance rehearsal seal (wave77)",
        "",
        f"- Status: `{receipt['status']}`",
        f"- Generated at: `{receipt['generated_at']}`",
        f"- Seal: `{receipt.get('seal_id')}`",
        f"- Certificate: `{receipt.get('certificate_id')}`",
        f"- Source receipt: `{receipt.get('source_receipt_id')}`",
        f"- Lane count: `{receipt.get('lane_count')}/{receipt.get('required_lane_count')}`",
        f"- Command count: `{receipt.get('command_count')}`",
        f"- Transfer/rehearsed steps: `{receipt.get('transfer_step_count')}/{receipt.get('rehearsed_step_count')}`",
        f"- Rehearsed lanes: `{receipt.get('rehearsed_lane_count')}`",
        "- Public action gate: `closed_until_jake_explicit_approval`",
        "- Public publish/push/deploy/outreach/payment/secret access: `not executed`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Cross-checks",
    ]
    for name, check in receipt.get("cross_checks", {}).items():
        lines.append(f"- `{name}` ok={check.get('ok')}")
    lines.extend(["", "## Package inclusion checks"])
    for item in receipt.get("package_json_inclusion_expectations", {}).get("required", []):
        lines.append(f"- `{item.get('path')}` exists={item.get('exists_local')} package_files={item.get('listed_in_package_files')}")
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
    receipt = build_rehearsal_seal(root, include_pack=False)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(receipt, root / args.markdown_out)
    if args.include_pack_check:
        receipt = build_rehearsal_seal(root, include_pack=True)
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_markdown(receipt, root / args.markdown_out)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
