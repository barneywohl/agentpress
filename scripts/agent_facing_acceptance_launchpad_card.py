#!/usr/bin/env python3
"""Generate a local-only launchpad card from the wave78 acceptance quickstart trail."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WAVE78 = "agentpress/evidence/agent-facing-acceptance-seal-verifier-quickstart-wave78.json"
WAVE77 = "agentpress/evidence/agent-facing-acceptance-rehearsal-seal-wave77.json"
WAVE76 = "agentpress/evidence/agent-facing-acceptance-recipient-rehearsal-wave76.json"
WAVE75 = "agentpress/evidence/agent-facing-acceptance-transfer-checklist-wave75.json"
WAVE74 = "agentpress/evidence/agent-facing-acceptance-certificate-replay-drill-wave74.json"
WAVE73 = "agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.json"
WAVE72 = "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json"
WAVE71 = "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json"
WAVE70 = "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json"
REQUIRED_INPUTS = [WAVE78, WAVE77, WAVE76, WAVE75, WAVE74, WAVE73, WAVE72, WAVE71, WAVE70]
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_launchpad_card.py"
TEST_PATH = "tests/test_agent_facing_acceptance_launchpad_card.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-launchpad-card"
REQUIRED_OUTPUTS = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]
REQUIRED_LANE_COUNT = 6
MIN_COMMANDS = 5
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
    return (data, None) if isinstance(data, dict) else (None, "json_root_not_object")


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
    for key in ("lane_count", "rehearsed_lane_count", "transfer_step_count"):
        if isinstance(doc.get(key), int):
            return doc[key]
    operator = doc.get("operator_certificate")
    if isinstance(operator, dict) and isinstance(operator.get("lane_count"), int):
        return operator["lane_count"]
    receipt = doc.get("readiness_receipt")
    if isinstance(receipt, dict) and isinstance(receipt.get("understood_lane_count"), int):
        return receipt["understood_lane_count"]
    lanes = doc.get("lanes")
    if isinstance(lanes, list):
        return len(lanes)
    coverage = doc.get("coverage")
    if isinstance(coverage, dict) and isinstance(coverage.get("covered_lane_ids"), list):
        return len(coverage["covered_lane_ids"])
    return None


def _commands(doc: dict[str, Any]) -> list[Any]:
    commands: list[Any] = []
    for key in ("fresh_agent_verification_commands", "exact_local_verification_commands", "verified_command_fragments"):
        if isinstance(doc.get(key), list):
            commands.extend(doc[key])
    receipt = doc.get("readiness_receipt")
    if isinstance(receipt, dict) and isinstance(receipt.get("exact_local_commands"), list):
        commands.extend(receipt["exact_local_commands"])
    return commands


def _validate_common(rel: str, doc: dict[str, Any], blockers: list[str]) -> None:
    if doc.get("status") != "ok":
        blockers.append(f"prior_artifact_status_not_ok: {rel}: {doc.get('status')!r}")
    if doc.get("blockers") not in ([], None):
        blockers.append(f"prior_artifact_has_blockers: {rel}")
    for field in ("public_actions_taken", "external_actions"):
        if doc.get(field) not in ([], None):
            blockers.append(f"prior_artifact_{field}_contaminated: {rel}")
    gate = _gate_state(doc)
    if gate is not None and gate != GATE_CLOSED:
        blockers.append(f"prior_artifact_public_gate_open: {rel}: {gate!r}")


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


def _ordered_commands(quickstart: dict[str, Any]) -> list[dict[str, Any]]:
    source = quickstart.get("fresh_agent_verification_commands")
    commands = [c for c in source if isinstance(c, dict)] if isinstance(source, list) else []
    normalized = []
    for idx, command in enumerate(commands, start=1):
        normalized.append({
            "order": int(command.get("order") or idx),
            "command": command.get("command"),
            "purpose": command.get("purpose"),
            "expected": command.get("expected"),
        })
    normalized.sort(key=lambda item: item["order"])
    return normalized


def build_launchpad_card(root: Path, *, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    prior: dict[str, dict[str, Any]] = {}
    for rel in REQUIRED_INPUTS:
        doc, err = load_json(root / rel)
        key = Path(rel).stem
        if err or doc is None:
            label = "missing_wave78_quickstart" if rel == WAVE78 and err == "missing" else "missing_prior_artifact"
            blockers.append(f"{label}: {rel}" if err == "missing" else f"prior_artifact_{err}: {rel}")
            docs[key] = {}
            prior[key] = {"path": rel, "loaded": False, "error": err}
        else:
            docs[key] = doc
            prior[key] = {"path": rel, "loaded": True, "status": doc.get("status")}
            _validate_common(rel, doc, blockers)

    wave78 = docs.get(Path(WAVE78).stem, {})
    wave77 = docs.get(Path(WAVE77).stem, {})
    quickstart_id = wave78.get("quickstart_id")
    seal_id = wave78.get("seal_id")
    certificate_id = wave78.get("certificate_id")
    source_receipt_id = wave78.get("source_receipt_id")
    lane_count = wave78.get("lane_count")
    rehearsed_lane_count = wave78.get("rehearsed_lane_count")
    artifact_count = len(wave78.get("artifact_inventory", [])) if isinstance(wave78.get("artifact_inventory"), list) else 0
    commands = _ordered_commands(wave78)

    if wave78:
        if not isinstance(quickstart_id, str) or not quickstart_id.startswith("wave78-quickstart-"):
            blockers.append("quickstart_id_missing_or_invalid")
        if not isinstance(seal_id, str) or not seal_id.startswith("wave77-seal-"):
            blockers.append("seal_id_missing_or_invalid")
        if not isinstance(certificate_id, str) or not certificate_id.startswith("wave73-certificate-"):
            blockers.append("certificate_id_missing_or_invalid")
        if not isinstance(source_receipt_id, str) or not source_receipt_id.startswith("wave72-readiness-"):
            blockers.append("source_receipt_id_missing_or_invalid")
        if lane_count != REQUIRED_LANE_COUNT:
            blockers.append("wave78_lane_count_mismatch")
        if rehearsed_lane_count != REQUIRED_LANE_COUNT:
            blockers.append("wave78_rehearsed_lane_count_mismatch")
        if artifact_count < 8:
            blockers.append("wave78_artifact_inventory_incomplete")
        if len(commands) < MIN_COMMANDS:
            blockers.append("wave78_fewer_than_5_ordered_verification_commands")
        if [c["order"] for c in commands] != sorted(c["order"] for c in commands):
            blockers.append("wave78_verification_commands_not_ordered")
        pkg = wave78.get("package_json_inclusion_expectations")
        required = pkg.get("required", []) if isinstance(pkg, dict) else []
        if not required or any(not item.get("listed_in_package_files") for item in required if isinstance(item, dict)):
            blockers.append("wave78_package_incomplete")
        pack = wave78.get("npm_pack_dry_run")
        included = pack.get("required_included", []) if isinstance(pack, dict) else []
        if not included or any(not item.get("included") for item in included if isinstance(item, dict)):
            blockers.append("wave78_npm_pack_incomplete")

    cross_checks: dict[str, Any] = {}
    for field in ("seal_id", "certificate_id", "source_receipt_id", "lane_count", "rehearsed_lane_count"):
        expected = wave77.get(field) if field != "rehearsed_lane_count" else wave77.get("rehearsed_lane_count")
        actual = wave78.get(field)
        ok = (expected == actual) if field in wave77 or field == "rehearsed_lane_count" else bool(actual)
        cross_checks[f"wave78_matches_wave77_{field}"] = {"ok": ok, "wave78": actual, "wave77": expected}
        if not ok:
            blockers.append(f"quickstart_seal_{field}_mismatch")

    artifact_inventory = []
    for rel in REQUIRED_INPUTS:
        doc = docs.get(Path(rel).stem, {})
        artifact_inventory.append({
            "path": rel,
            "loaded": bool(doc),
            "status": doc.get("status") if doc else None,
            "lane_count": _lane_count(doc) if doc else None,
            "command_count": len(_commands(doc)) if doc else 0,
            "public_action_gate": _gate_state(doc) if doc else None,
        })
    if any(item["loaded"] and item["lane_count"] not in (None, REQUIRED_LANE_COUNT) for item in artifact_inventory):
        blockers.append("prior_artifact_lane_count_mismatch")

    package, package_blockers = package_expectations(root)
    blockers.extend(package_blockers)
    pack_result = run_pack(root) if include_pack else None
    if pack_result:
        if pack_result.get("returncode") != 0 or not pack_result.get("json_parseable"):
            blockers.append("npm_pack_dry_run_failed")
        for item in pack_result.get("required_included", []):
            if not item.get("included"):
                blockers.append(f"npm_pack_missing_required: {item.get('path')}")

    card_basis = json.dumps({"quickstart_id": quickstart_id, "seal_id": seal_id, "certificate_id": certificate_id, "source_receipt_id": source_receipt_id, "commands": commands}, sort_keys=True)
    recommended = f"npm run {SCRIPT_NAME}"
    alternative_commands = [item["command"] for item in commands if isinstance(item.get("command"), str)]
    alternative_commands.extend([
        "python3 -m json.tool agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json >/tmp/agentpress-wave79-json.tool.out",
        f"python3 -m pytest {TEST_PATH} -q",
        "npm pack --dry-run --json",
    ])
    # Preserve order while deduplicating.
    alternative_commands = list(dict.fromkeys(alternative_commands))

    return {
        "kind": "agentpress_agent_facing_acceptance_launchpad_card",
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "ok" if not blockers else "blocked",
        "local_only": True,
        "launchpad_card_id": "wave79-card-" + hashlib.sha256(card_basis.encode("utf-8")).hexdigest()[:16],
        "quickstart_id": quickstart_id,
        "seal_id": seal_id,
        "certificate_id": certificate_id,
        "source_receipt_id": source_receipt_id,
        "lane_count": lane_count if lane_count == REQUIRED_LANE_COUNT else None,
        "rehearsed_lane_count": rehearsed_lane_count,
        "required_lane_count": REQUIRED_LANE_COUNT,
        "artifact_inventory_count": artifact_count,
        "ordered_verification_commands": commands,
        "ordered_verification_command_count": len(commands),
        "recommended_next_command": recommended,
        "alternative_commands": alternative_commands,
        "artifact_inventory": artifact_inventory,
        "cross_checks": cross_checks,
        "prior_artifacts": prior,
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack_result,
        "public_action_gate": GATE_CLOSED,
        "public_publish_push_gate": "Jake explicit approval required; no public action assigned",
        "public_actions_taken": [],
        "external_actions": [],
        "blockers": blockers,
    }


def write_markdown(receipt: dict[str, Any], path: Path) -> None:
    lines = [
        "# AgentPress agent-facing acceptance launchpad card (wave79)",
        "",
        f"- Status: `{receipt['status']}`",
        f"- Generated at: `{receipt['generated_at']}`",
        f"- Launchpad card: `{receipt.get('launchpad_card_id')}`",
        f"- Recommended next command: `{receipt.get('recommended_next_command')}`",
        f"- Quickstart: `{receipt.get('quickstart_id')}`",
        f"- Seal: `{receipt.get('seal_id')}`",
        f"- Certificate: `{receipt.get('certificate_id')}`",
        f"- Source receipt: `{receipt.get('source_receipt_id')}`",
        f"- Lane count: `{receipt.get('lane_count')}/{receipt.get('required_lane_count')}`",
        f"- Ordered verification commands: `{receipt.get('ordered_verification_command_count')}`",
        "- Public action gate: `closed_until_jake_explicit_approval`",
        "- Public publish/push/deploy/outreach/payment/secret access: `not executed`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Recommended alternatives",
    ]
    for command in receipt.get("alternative_commands", []):
        lines.append(f"- `{command}`")
    lines.extend(["", "## Ordered verification commands"])
    for command in receipt.get("ordered_verification_commands", []):
        lines.append(f"{command.get('order')}. `{command.get('command')}` — {command.get('purpose')} Expected: {command.get('expected')}")
    lines.extend(["", "## Artifact inventory"])
    for item in receipt.get("artifact_inventory", []):
        lines.append(f"- `{item.get('path')}` loaded={item.get('loaded')} status={item.get('status')} lanes={item.get('lane_count')} gate={item.get('public_action_gate')}")
    lines.extend(["", "## Cross-checks"])
    for name, check in receipt.get("cross_checks", {}).items():
        lines.append(f"- `{name}` ok={check.get('ok')}")
    lines.extend(["", "## Package inclusion checks"])
    for item in receipt.get("package_json_inclusion_expectations", {}).get("required", []):
        lines.append(f"- `{item.get('path')}` exists={item.get('exists_local')} package_files={item.get('listed_in_package_files')}")
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
    receipt = build_launchpad_card(root, include_pack=False)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(receipt, root / args.markdown_out)
    if args.include_pack_check:
        receipt = build_launchpad_card(root, include_pack=True)
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_markdown(receipt, root / args.markdown_out)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
