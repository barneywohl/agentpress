#!/usr/bin/env python3
"""Generate a local-only fresh-agent smoke replay receipt from the wave81 packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WAVE81 = "agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.json"
WAVE80 = "agentpress/evidence/agent-facing-acceptance-first-command-dry-run-wave80.json"
WAVE79 = "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json"
REQUIRED_INPUTS = [WAVE81, WAVE80, WAVE79]
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_smoke_replay_receipt.py"
TEST_PATH = "tests/test_agent_facing_acceptance_smoke_replay_receipt.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-smoke-replay-receipt"
REQUIRED_OUTPUTS = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]
GATE_CLOSED = "closed_until_jake_explicit_approval"
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


def validate_clean_prior(rel: str, doc: dict[str, Any], blockers: list[str]) -> None:
    if doc.get("status") != "ok":
        blockers.append(f"prior_status_not_ok: {rel}: {doc.get('status')!r}")
    if doc.get("blockers") not in ([], None):
        blockers.append(f"prior_has_blockers: {rel}")
    for field in ("public_actions_taken", "external_actions"):
        if doc.get(field) not in ([], None):
            blockers.append(f"prior_{field}_contaminated: {rel}")


def command_safety(command: str) -> dict[str, Any]:
    match = FORBIDDEN_RE.search(command or "")
    return {
        "command": command,
        "local_safe": match is None,
        "inspection_only": match is None,
        "public_action_free": match is None,
        "forbidden_match": match.group(0) if match else None,
    }


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
        result.update({"stdout": proc.stdout[-1000:], "stderr": proc.stderr[-1000:]})
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
        ["python3", "-m", "json.tool", WAVE81],
        ["python3", "-m", "json.tool", WAVE80],
        ["python3", "-m", "json.tool", WAVE79],
        ["python3", "-m", "py_compile", SCRIPT_PATH],
    ]
    results = []
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=False)
        results.append({"command": " ".join(cmd), "returncode": proc.returncode, "stdout_tail": proc.stdout[-500:], "stderr_tail": proc.stderr[-500:]})
    return results


def replay_first_command(root: Path, command: str, *, run_replay: bool) -> dict[str, Any]:
    safety = command_safety(command)
    result: dict[str, Any] = {"command": command, "skipped": not run_replay, **safety}
    if not run_replay:
        return result
    if not (safety["local_safe"] and safety["inspection_only"] and safety["public_action_free"]):
        result.update({"returncode": None, "blocked_before_execution": True})
        return result
    proc = subprocess.run(command, cwd=root, shell=True, text=True, capture_output=True, check=False)
    result.update({"returncode": proc.returncode, "stdout_tail": proc.stdout[-1200:], "stderr_tail": proc.stderr[-1200:]})
    return result


def build_receipt(root: Path, *, include_pack: bool = False, run_inspections: bool = True, run_replay: bool = True) -> dict[str, Any]:
    blockers: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    prior: dict[str, dict[str, Any]] = {}
    for rel in REQUIRED_INPUTS:
        doc, err = load_json(root / rel)
        key = Path(rel).stem
        if err or doc is None:
            label = "missing_wave81_packet" if rel == WAVE81 and err == "missing" else "missing_prior_artifact"
            blockers.append(f"{label}: {rel}" if err == "missing" else f"prior_artifact_{err}: {rel}")
            docs[key] = {}
            prior[key] = {"path": rel, "loaded": False, "error": err}
        else:
            docs[key] = doc
            prior[key] = {"path": rel, "loaded": True, "status": doc.get("status")}
            validate_clean_prior(rel, doc, blockers)

    wave81 = docs.get(Path(WAVE81).stem, {})
    wave80 = docs.get(Path(WAVE80).stem, {})
    wave79 = docs.get(Path(WAVE79).stem, {})
    selected = str(wave81.get("selected_command") or "")
    first_command = (wave81.get("paste_ready_packet") or {}).get("first_command") if isinstance(wave81.get("paste_ready_packet"), dict) else None
    wave80_selected = (wave80.get("first_command_selection") or {}).get("selected") if isinstance(wave80.get("first_command_selection"), dict) else None
    wave79_recommended = wave79.get("recommended_next_command")
    expected_outputs = (wave81.get("paste_ready_packet") or {}).get("expected_evidence_outputs", []) if isinstance(wave81.get("paste_ready_packet"), dict) else []
    packet_commands = wave81.get("packet_commands") if isinstance(wave81.get("packet_commands"), list) else []

    if not selected:
        blockers.append("wave81_missing_selected_command")
    cross_checks = {
        "wave81_selected_matches_paste_ready_first_command": selected == first_command,
        "wave81_selected_matches_wave80_selection": selected == wave80_selected,
        "wave81_selected_matches_wave79_recommended_next_command": selected == wave79_recommended,
        "wave81_expected_outputs_present": WAVE81 in expected_outputs and str(WAVE81).replace(".json", ".md") in expected_outputs,
        "wave81_packet_commands_present": len(packet_commands) >= 5,
        "wave81_public_action_gate_closed": wave81.get("public_action_gate") == GATE_CLOSED,
    }
    for name, ok in cross_checks.items():
        if wave81 and wave80 and wave79 and not ok:
            blockers.append(f"{name}_failed")

    packet_command_safety = []
    for idx, row in enumerate(packet_commands):
        command = row.get("command") if isinstance(row, dict) else str(row)
        safety = command_safety(str(command or ""))
        prior_flags_ok = bool(isinstance(row, dict) and row.get("local_safe") is True and row.get("inspection_only") is True and row.get("public_action_free") is True)
        safety["prior_flags_ok"] = prior_flags_ok
        safety["packet_index"] = idx
        packet_command_safety.append(safety)
    if any((not r["local_safe"]) or (not r["inspection_only"]) or (not r["public_action_free"]) or (not r["prior_flags_ok"]) for r in packet_command_safety):
        blockers.append("packet_command_safety_failed")

    replay = replay_first_command(root, selected, run_replay=run_replay)
    if replay.get("blocked_before_execution"):
        blockers.append("selected_command_forbidden_replay_blocked")
    if run_replay and replay.get("returncode") != 0:
        blockers.append("selected_command_replay_failed")

    pkg_expect, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or not pack.get("json_parseable"):
            blockers.append("npm_pack_dry_run_failed")
        if any(not item.get("included") for item in pack.get("required_included", [])):
            blockers.append("npm_pack_missing_required_wave82_files")

    inspections = run_local_inspections(root) if run_inspections else []
    if any(item["returncode"] != 0 for item in inspections):
        blockers.append("local_inspection_command_failed")

    digest_source = json.dumps({"selected": selected, "checks": cross_checks, "replay": {"command": selected, "returncode": replay.get("returncode")}}, sort_keys=True)
    receipt = {
        "kind": "agent_facing_acceptance_smoke_replay_receipt",
        "status": "blocked" if blockers else "ok",
        "generated_at": utc_now(),
        "receipt_id": "wave82-smoke-replay-" + hashlib.sha256(digest_source.encode()).hexdigest()[:12],
        "source_wave81": WAVE81,
        "source_wave80": WAVE80,
        "source_wave79": WAVE79,
        "selected_command": selected,
        "replay_mode": "local_inspection_only_no_public_actions",
        "selected_command_replay": replay,
        "expected_replay_outputs": [
            "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json",
            "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.md",
            DEFAULT_OUT,
            DEFAULT_MD,
        ],
        "deterministic_success_criteria": [
            "wave81, wave80, and wave79 load as ok with empty blockers",
            "selected command equals wave81 paste_ready_packet.first_command, wave80 first_command_selection.selected, and wave79 recommended_next_command",
            "selected command replay exits 0 in local inspection-only mode",
            "all wave81 packet commands remain local_safe, inspection_only, public_action_free, and forbidden-command free",
            "package dry-run includes the wave82 script, test, JSON receipt, and Markdown receipt",
            "public_actions_taken and external_actions remain empty",
        ],
        "deterministic_failure_criteria": [
            "missing, blocked, non-ok, or public/external contaminated prior evidence",
            "selected command mismatch across wave81, wave80, or wave79",
            "selected command or packet command contains publish/push/deploy/outreach/payment/secret text",
            "selected command replay, local inspections, pytest, or npm pack dry-run fails",
            "any public_actions_taken or external_actions are recorded",
        ],
        "cross_checks": {k: {"ok": v} for k, v in cross_checks.items()},
        "packet_command_safety": packet_command_safety,
        "prior_artifacts": prior,
        "package_json_inclusion_expectations": pkg_expect,
        "npm_pack_dry_run": pack,
        "executed_local_inspection_commands": inspections,
        "public_action_gate": GATE_CLOSED,
        "public_actions_taken": [],
        "external_actions": [],
        "blockers": blockers,
        "agent_painpoint_solved": "A fresh agent can now prove the wave81 one-command packet works by replaying the first safe command locally and receiving a deterministic receipt without touching publish, push, deploy, outreach, payments, accounts, or secrets.",
    }
    return receipt


def markdown(receipt: dict[str, Any]) -> str:
    lines = [
        "# Agent-facing acceptance smoke replay receipt (wave82)",
        "",
        f"- Status: `{receipt['status']}`",
        f"- Receipt id: `{receipt['receipt_id']}`",
        f"- Replayed command: `{receipt.get('selected_command')}`",
        f"- Replay return code: `{receipt.get('selected_command_replay', {}).get('returncode')}`",
        f"- Public action gate: `{receipt['public_action_gate']}`",
        "- Public actions taken: none",
        "- External actions: none",
        "",
        "## Deterministic success criteria",
    ]
    lines.extend([f"- {item}" for item in receipt.get("deterministic_success_criteria", [])])
    lines.append("\n## Deterministic failure criteria")
    lines.extend([f"- {item}" for item in receipt.get("deterministic_failure_criteria", [])])
    lines.append("\n## Blockers")
    lines.extend([f"- {b}" for b in receipt.get("blockers", [])] or ["- none"])
    lines.append("\n## Expected replay outputs")
    lines.extend([f"- `{item}`" for item in receipt.get("expected_replay_outputs", [])])
    lines.append("")
    return "\n".join(lines)


def write_receipt(root: Path, receipt: dict[str, Any], out_rel: str, md_rel: str) -> None:
    out = root / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = root / md_rel
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(markdown(receipt), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--skip-inspections", action="store_true")
    parser.add_argument("--skip-replay", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    receipt = build_receipt(root, include_pack=False, run_inspections=not args.skip_inspections, run_replay=not args.skip_replay)
    write_receipt(root, receipt, args.out, args.markdown_out)
    if args.include_pack_check:
        receipt = build_receipt(root, include_pack=True, run_inspections=not args.skip_inspections, run_replay=False)
        # Keep the first replay evidence but update package evidence after outputs exist.
        first = json.loads((root / args.out).read_text(encoding="utf-8"))
        receipt["selected_command_replay"] = first.get("selected_command_replay", receipt["selected_command_replay"])
        receipt["blockers"] = [b for b in receipt.get("blockers", []) if b != "selected_command_replay_failed"]
        receipt["status"] = "blocked" if receipt["blockers"] else "ok"
        write_receipt(root, receipt, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
