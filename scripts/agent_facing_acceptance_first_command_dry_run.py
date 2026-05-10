#!/usr/bin/env python3
"""Generate a local-only first-command dry-run proof from the wave79 launchpad card."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WAVE79 = "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json"
WAVE78 = "agentpress/evidence/agent-facing-acceptance-seal-verifier-quickstart-wave78.json"
WAVE77 = "agentpress/evidence/agent-facing-acceptance-rehearsal-seal-wave77.json"
WAVE76 = "agentpress/evidence/agent-facing-acceptance-recipient-rehearsal-wave76.json"
WAVE75 = "agentpress/evidence/agent-facing-acceptance-transfer-checklist-wave75.json"
WAVE74 = "agentpress/evidence/agent-facing-acceptance-certificate-replay-drill-wave74.json"
WAVE73 = "agentpress/evidence/agent-facing-acceptance-receipt-verifier-wave73.json"
WAVE72 = "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json"
WAVE71 = "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json"
WAVE70 = "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json"
REQUIRED_INPUTS = [WAVE79, WAVE78, WAVE77, WAVE76, WAVE75, WAVE74, WAVE73, WAVE72, WAVE71, WAVE70]
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-first-command-dry-run-wave80.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-first-command-dry-run-wave80.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_first_command_dry_run.py"
TEST_PATH = "tests/test_agent_facing_acceptance_first_command_dry_run.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-first-command-dry-run"
REQUIRED_OUTPUTS = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]
GATE_CLOSED = "closed_until_jake_explicit_approval"
REQUIRED_LANE_COUNT = 6
MIN_COMMANDS = 5
FORBIDDEN_RE = re.compile(r"\b(npm\s+publish|git\s+push|deploy|curl\b|wget\b|payment|wallet|secret|token|outreach|email|send)\b", re.I)


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


def gate_state(doc: dict[str, Any]) -> str | None:
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


def lane_count(doc: dict[str, Any]) -> int | None:
    for key in ("lane_count", "rehearsed_lane_count", "artifact_inventory_count", "ordered_verification_command_count"):
        if isinstance(doc.get(key), int) and key in ("lane_count", "rehearsed_lane_count"):
            return doc[key]
    operator = doc.get("operator_certificate")
    if isinstance(operator, dict) and isinstance(operator.get("lane_count"), int):
        return operator["lane_count"]
    lanes = doc.get("lanes")
    if isinstance(lanes, list):
        return len(lanes)
    coverage = doc.get("coverage")
    if isinstance(coverage, dict) and isinstance(coverage.get("covered_lane_ids"), list):
        return len(coverage["covered_lane_ids"])
    return None


def validate_prior(rel: str, doc: dict[str, Any], blockers: list[str]) -> None:
    if doc.get("status") != "ok":
        blockers.append(f"prior_artifact_status_not_ok: {rel}: {doc.get('status')!r}")
    if doc.get("blockers") not in ([], None):
        blockers.append(f"prior_artifact_has_blockers: {rel}")
    for field in ("public_actions_taken", "external_actions"):
        if doc.get(field) not in ([], None):
            blockers.append(f"prior_artifact_{field}_contaminated: {rel}")
    gate = gate_state(doc)
    if gate is not None and gate != GATE_CLOSED:
        blockers.append(f"prior_artifact_public_gate_open: {rel}: {gate!r}")


def command_text(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("command") or "")
    return ""


def command_rows(wave79: dict[str, Any]) -> list[dict[str, Any]]:
    commands = []
    recommended = wave79.get("recommended_next_command")
    if isinstance(recommended, str):
        commands.append({"role": "recommended_next_command", "command": recommended})
    for idx, item in enumerate(wave79.get("alternative_commands", []) if isinstance(wave79.get("alternative_commands"), list) else [], start=1):
        commands.append({"role": f"alternative_command_{idx}", "command": command_text(item)})
    for idx, item in enumerate(wave79.get("ordered_verification_commands", []) if isinstance(wave79.get("ordered_verification_commands"), list) else [], start=1):
        commands.append({"role": f"ordered_verification_command_{idx}", "command": command_text(item)})
    rows = []
    for row in commands:
        text = row["command"]
        forbidden = bool(FORBIDDEN_RE.search(text))
        rows.append({
            **row,
            "local_safe": not forbidden,
            "inspection_only": not forbidden,
            "public_action_free": not forbidden,
            "forbidden_match": FORBIDDEN_RE.search(text).group(0) if forbidden else None,
            "executed": False,
            "execution_note": "selected and rehearsed only; wave80 executes separate JSON/compile local inspections, not arbitrary publish/deploy/outreach commands",
        })
    return rows


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


def run_local_inspections(root: Path) -> list[dict[str, Any]]:
    commands = [
        ["python3", "-m", "json.tool", WAVE79],
        ["python3", "-m", "py_compile", SCRIPT_PATH],
    ]
    results = []
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=False)
        results.append({"command": " ".join(cmd), "returncode": proc.returncode, "stdout_tail": proc.stdout[-500:], "stderr_tail": proc.stderr[-500:]})
    return results


def build_first_command_dry_run(root: Path, *, include_pack: bool = False, run_inspections: bool = True) -> dict[str, Any]:
    blockers: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    prior = {}
    for rel in REQUIRED_INPUTS:
        doc, err = load_json(root / rel)
        key = Path(rel).stem
        if err or doc is None:
            label = "missing_wave79_launchpad_card" if rel == WAVE79 and err == "missing" else "missing_prior_artifact"
            blockers.append(f"{label}: {rel}" if err == "missing" else f"prior_artifact_{err}: {rel}")
            docs[key] = {}
            prior[key] = {"path": rel, "loaded": False, "error": err}
        else:
            docs[key] = doc
            prior[key] = {"path": rel, "loaded": True, "status": doc.get("status")}
            validate_prior(rel, doc, blockers)

    wave79 = docs.get(Path(WAVE79).stem, {})
    wave78 = docs.get(Path(WAVE78).stem, {})
    if wave79:
        if not isinstance(wave79.get("launchpad_card_id"), str) or not wave79["launchpad_card_id"].startswith("wave79-card-"):
            blockers.append("launchpad_card_id_missing_or_invalid")
        for key, prefix in (("quickstart_id", "wave78-quickstart-"), ("seal_id", "wave77-seal-"), ("certificate_id", "wave73-certificate-"), ("source_receipt_id", "wave72-readiness-")):
            if not isinstance(wave79.get(key), str) or not wave79[key].startswith(prefix):
                blockers.append(f"{key}_missing_or_invalid")
        if wave79.get("lane_count") != REQUIRED_LANE_COUNT:
            blockers.append("wave79_lane_count_mismatch")
        if wave79.get("rehearsed_lane_count") != REQUIRED_LANE_COUNT:
            blockers.append("wave79_rehearsed_lane_count_mismatch")
        if int(wave79.get("artifact_inventory_count") or 0) < 8:
            blockers.append("wave79_artifact_inventory_incomplete")
        if int(wave79.get("ordered_verification_command_count") or 0) < MIN_COMMANDS:
            blockers.append("wave79_ordered_command_count_regression")
        if not isinstance(wave79.get("recommended_next_command"), str) or not wave79.get("recommended_next_command"):
            blockers.append("wave79_missing_recommended_next_command")
        if len(wave79.get("alternative_commands", []) if isinstance(wave79.get("alternative_commands"), list) else []) < MIN_COMMANDS:
            blockers.append("wave79_fewer_than_5_alternative_commands")
        pkg = wave79.get("package_json_inclusion_expectations")
        required = pkg.get("required", []) if isinstance(pkg, dict) else []
        if not required or any(not item.get("listed_in_package_files") for item in required if isinstance(item, dict)):
            blockers.append("wave79_package_incomplete")

    cross_checks = {
        "wave79_matches_wave78_quickstart_id": wave79.get("quickstart_id") == wave78.get("quickstart_id"),
        "wave79_matches_wave78_seal_id": wave79.get("seal_id") == wave78.get("seal_id"),
        "wave79_matches_wave78_certificate_id": wave79.get("certificate_id") == wave78.get("certificate_id"),
        "wave79_matches_wave78_source_receipt_id": wave79.get("source_receipt_id") == wave78.get("source_receipt_id"),
        "wave79_matches_wave78_lane_count": wave79.get("lane_count") == wave78.get("lane_count"),
        "wave79_matches_wave78_rehearsed_lane_count": wave79.get("rehearsed_lane_count") == wave78.get("rehearsed_lane_count"),
    }
    for name, ok in cross_checks.items():
        if wave79 and wave78 and not ok:
            blockers.append(f"{name}_mismatch")

    rehearsed_commands = command_rows(wave79)
    if any(not row["local_safe"] or not row["inspection_only"] or not row["public_action_free"] for row in rehearsed_commands):
        blockers.append("forbidden_command_text_detected")

    pkg_expect, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or not pack.get("json_parseable"):
            blockers.append("npm_pack_dry_run_failed")
        if any(not item.get("included") for item in pack.get("required_included", [])):
            blockers.append("npm_pack_missing_required_wave80_files")

    inspections = run_local_inspections(root) if run_inspections else []
    if any(item["returncode"] != 0 for item in inspections):
        blockers.append("local_inspection_command_failed")

    digest_source = json.dumps({"launchpad": wave79.get("launchpad_card_id"), "commands": rehearsed_commands, "cross_checks": cross_checks}, sort_keys=True)
    receipt = {
        "kind": "agent_facing_acceptance_first_command_dry_run",
        "status": "blocked" if blockers else "ok",
        "generated_at": utc_now(),
        "dry_run_id": "wave80-first-command-" + hashlib.sha256(digest_source.encode()).hexdigest()[:12],
        "source_launchpad_card": WAVE79,
        "launchpad_card_id": wave79.get("launchpad_card_id"),
        "quickstart_id": wave79.get("quickstart_id"),
        "seal_id": wave79.get("seal_id"),
        "certificate_id": wave79.get("certificate_id"),
        "source_receipt_id": wave79.get("source_receipt_id"),
        "lane_count": wave79.get("lane_count"),
        "rehearsed_lane_count": wave79.get("rehearsed_lane_count"),
        "artifact_inventory_count": wave79.get("artifact_inventory_count"),
        "ordered_verification_command_count": wave79.get("ordered_verification_command_count"),
        "recommended_next_command": wave79.get("recommended_next_command"),
        "first_command_selection": {"selected": wave79.get("recommended_next_command"), "selection_reason": "launchpad recommended command is the first paste-ready local proof command"},
        "rehearsed_commands": rehearsed_commands,
        "rehearsed_command_count": len(rehearsed_commands),
        "cross_checks": {k: {"ok": v} for k, v in cross_checks.items()},
        "prior_artifacts": prior,
        "package_json_inclusion_expectations": pkg_expect,
        "npm_pack_dry_run": pack,
        "executed_local_inspection_commands": inspections,
        "public_action_gate": GATE_CLOSED,
        "public_actions_taken": [],
        "external_actions": [],
        "blockers": blockers,
        "agent_painpoint_solved": "A fresh agent no longer has to guess the first safe command after the launchpad card; wave80 selects it, checks the full proof trail, and rejects public/external command drift before any publish/push/deploy/outreach/payment action.",
    }
    return receipt


def markdown(receipt: dict[str, Any]) -> str:
    lines = [
        "# Agent-facing acceptance first-command dry run (wave80)",
        "",
        f"- Status: `{receipt['status']}`",
        f"- Dry run id: `{receipt['dry_run_id']}`",
        f"- First command: `{receipt.get('recommended_next_command')}`",
        f"- Rehearsed commands: {receipt.get('rehearsed_command_count')}",
        f"- Public action gate: `{receipt['public_action_gate']}`",
        "- Public actions taken: none",
        "- External actions: none",
        "",
        "## Blockers",
    ]
    lines.extend([f"- {b}" for b in receipt.get("blockers", [])] or ["- none"])
    lines.append("\n## Executed local inspections")
    for item in receipt.get("executed_local_inspection_commands", []):
        lines.append(f"- `{item['command']}` -> {item['returncode']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--skip-inspections", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    receipt = build_first_command_dry_run(root, include_pack=args.include_pack_check, run_inspections=not args.skip_inspections)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = root / args.markdown_out
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(markdown(receipt), encoding="utf-8")
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
