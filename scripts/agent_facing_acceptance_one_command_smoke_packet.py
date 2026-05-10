#!/usr/bin/env python3
"""Generate a local-only one-command smoke packet from wave80 and wave79 evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WAVE80 = "agentpress/evidence/agent-facing-acceptance-first-command-dry-run-wave80.json"
WAVE79 = "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json"
WAVE78 = "agentpress/evidence/agent-facing-acceptance-seal-verifier-quickstart-wave78.json"
WAVE77 = "agentpress/evidence/agent-facing-acceptance-rehearsal-seal-wave77.json"
WAVE76 = "agentpress/evidence/agent-facing-acceptance-recipient-rehearsal-wave76.json"
REQUIRED_INPUTS = [WAVE80, WAVE79, WAVE78, WAVE77, WAVE76]
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_one_command_smoke_packet.py"
TEST_PATH = "tests/test_agent_facing_acceptance_one_command_smoke_packet.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-one-command-smoke-packet"
REQUIRED_OUTPUTS = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]
GATE_CLOSED = "closed_until_jake_explicit_approval"
MIN_REHEARSED_COMMANDS = 5
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
        ["python3", "-m", "json.tool", WAVE80],
        ["python3", "-m", "json.tool", WAVE79],
        ["python3", "-m", "py_compile", SCRIPT_PATH],
    ]
    results = []
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=False)
        results.append({"command": " ".join(cmd), "returncode": proc.returncode, "stdout_tail": proc.stdout[-500:], "stderr_tail": proc.stderr[-500:]})
    return results


def command_safety(command: str) -> dict[str, Any]:
    match = FORBIDDEN_RE.search(command or "")
    return {
        "command": command,
        "local_safe": match is None,
        "inspection_only": match is None,
        "public_action_free": match is None,
        "forbidden_match": match.group(0) if match else None,
    }


def build_smoke_packet(root: Path, *, include_pack: bool = False, run_inspections: bool = True) -> dict[str, Any]:
    blockers: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    prior: dict[str, dict[str, Any]] = {}
    for rel in REQUIRED_INPUTS:
        doc, err = load_json(root / rel)
        key = Path(rel).stem
        if err or doc is None:
            label = "missing_wave80_first_command" if rel == WAVE80 and err == "missing" else "missing_prior_artifact"
            blockers.append(f"{label}: {rel}" if err == "missing" else f"prior_artifact_{err}: {rel}")
            docs[key] = {}
            prior[key] = {"path": rel, "loaded": False, "error": err}
        else:
            docs[key] = doc
            prior[key] = {"path": rel, "loaded": True, "status": doc.get("status")}
            validate_clean_prior(rel, doc, blockers)

    wave80 = docs.get(Path(WAVE80).stem, {})
    wave79 = docs.get(Path(WAVE79).stem, {})
    wave78 = docs.get(Path(WAVE78).stem, {})
    wave77 = docs.get(Path(WAVE77).stem, {})
    wave76 = docs.get(Path(WAVE76).stem, {})

    selection = wave80.get("first_command_selection") if isinstance(wave80.get("first_command_selection"), dict) else {}
    selected = selection.get("selected")
    recommended = wave79.get("recommended_next_command")
    if not selected:
        blockers.append("wave80_missing_first_command_selection_selected")
    if selected != recommended:
        blockers.append("selected_command_mismatch_wave79_recommended_next_command")
    if int(wave80.get("rehearsed_command_count") or 0) < MIN_REHEARSED_COMMANDS:
        blockers.append("wave80_rehearsed_command_count_regression")

    cross_checks = {
        "selected_matches_wave79_recommended_next_command": selected == recommended,
        "launchpad_card_id_consistent": wave80.get("launchpad_card_id") == wave79.get("launchpad_card_id"),
        "quickstart_id_consistent": wave80.get("quickstart_id") == wave79.get("quickstart_id") == wave78.get("quickstart_id"),
        "seal_id_consistent": wave80.get("seal_id") == wave79.get("seal_id") == wave78.get("seal_id") == wave77.get("seal_id"),
        "source_receipt_id_consistent": wave80.get("source_receipt_id") == wave79.get("source_receipt_id") == wave78.get("source_receipt_id"),
        "lane_count_consistent": wave80.get("lane_count") == wave79.get("lane_count") == wave78.get("lane_count") == wave76.get("lane_count"),
        "rehearsed_lane_count_consistent": wave80.get("rehearsed_lane_count") == wave79.get("rehearsed_lane_count") == wave78.get("rehearsed_lane_count"),
        "artifact_inventory_count_consistent": wave80.get("artifact_inventory_count") == wave79.get("artifact_inventory_count"),
        "command_count_not_regressed": int(wave80.get("rehearsed_command_count") or 0) >= MIN_REHEARSED_COMMANDS and int(wave80.get("ordered_verification_command_count") or 0) >= MIN_REHEARSED_COMMANDS,
    }
    for name, ok in cross_checks.items():
        if wave80 and wave79 and not ok:
            blockers.append(f"{name}_failed")

    packet_commands = [
        command_safety(str(selected or "")),
        command_safety(f"python3 -m json.tool {DEFAULT_OUT}"),
        command_safety(f"python3 -m py_compile {SCRIPT_PATH}"),
        command_safety(f"python3 -m pytest {TEST_PATH} -q"),
        command_safety("npm pack --dry-run --json"),
    ]
    if any(not row["local_safe"] or not row["inspection_only"] or not row["public_action_free"] for row in packet_commands):
        blockers.append("forbidden_command_text_detected")

    pkg_expect, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or not pack.get("json_parseable"):
            blockers.append("npm_pack_dry_run_failed")
        if any(not item.get("included") for item in pack.get("required_included", [])):
            blockers.append("npm_pack_missing_required_wave81_files")

    inspections = run_local_inspections(root) if run_inspections else []
    if any(item["returncode"] != 0 for item in inspections):
        blockers.append("local_inspection_command_failed")

    digest_source = json.dumps({"selected": selected, "checks": cross_checks, "commands": packet_commands}, sort_keys=True)
    packet = {
        "kind": "agent_facing_acceptance_one_command_smoke_packet",
        "status": "blocked" if blockers else "ok",
        "generated_at": utc_now(),
        "packet_id": "wave81-smoke-packet-" + hashlib.sha256(digest_source.encode()).hexdigest()[:12],
        "source_wave80": WAVE80,
        "source_wave79": WAVE79,
        "selected_command": selected,
        "paste_ready_packet": {
            "title": "Fresh-agent one-command smoke packet",
            "first_command": selected,
            "expected_evidence_outputs": [DEFAULT_OUT, DEFAULT_MD],
            "safety_preflight": [
                "Run only in a local checkout; do not publish, push, deploy, send outreach, access accounts/secrets, or spend money.",
                "Confirm public_action_gate is closed_until_jake_explicit_approval.",
                "Treat non-ok status or any blocker as stop-and-report, not as permission to improvise public actions.",
            ],
            "rollback_guidance": [
                "This packet writes only local evidence files; rollback is removing the generated wave81 JSON/Markdown files and reverting package/script/test edits.",
                "No external rollback should be required because public_actions_taken and external_actions must remain empty.",
            ],
            "success_criteria": [
                "npm script exits 0 locally.",
                "wave81 JSON status is ok with empty blockers.",
                "All packet commands are local_safe, inspection_only, and public_action_free.",
                "Cross-checks for selected command, IDs, lane counts, artifact inventory, and command counts are true.",
            ],
            "failure_criteria": [
                "Any missing/blocked/non-ok prior artifact.",
                "Selected command mismatch with wave79 recommended_next_command.",
                "Any forbidden public/external command text or non-empty public/external action list.",
                "Any missing required package artifact or failed local inspection.",
            ],
        },
        "packet_commands": packet_commands,
        "cross_checks": {k: {"ok": v} for k, v in cross_checks.items()},
        "prior_artifacts": prior,
        "package_json_inclusion_expectations": pkg_expect,
        "npm_pack_dry_run": pack,
        "executed_local_inspection_commands": inspections,
        "public_action_gate": GATE_CLOSED,
        "public_actions_taken": [],
        "external_actions": [],
        "blockers": blockers,
        "agent_painpoint_solved": "A fresh agent gets one local-safe paste command plus deterministic stop/go criteria, so acceptance smoke testing no longer depends on interpreting the whole proof trail under pressure.",
    }
    return packet


def markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Agent-facing acceptance one-command smoke packet (wave81)",
        "",
        f"- Status: `{packet['status']}`",
        f"- Packet id: `{packet['packet_id']}`",
        f"- First command: `{packet.get('selected_command')}`",
        f"- Public action gate: `{packet['public_action_gate']}`",
        "- Public actions taken: none",
        "- External actions: none",
        "",
        "## Paste-ready packet",
        f"1. Run: `{packet['paste_ready_packet'].get('first_command')}`",
        "2. Verify generated evidence outputs:",
    ]
    lines.extend([f"   - `{item}`" for item in packet["paste_ready_packet"].get("expected_evidence_outputs", [])])
    lines.append("3. Stop if any blocker appears; do not perform public actions without Jake's explicit approval.")
    lines.append("\n## Blockers")
    lines.extend([f"- {b}" for b in packet.get("blockers", [])] or ["- none"])
    lines.append("\n## Packet commands")
    for item in packet.get("packet_commands", []):
        lines.append(f"- `{item['command']}` — local_safe={item['local_safe']}, inspection_only={item['inspection_only']}, public_action_free={item['public_action_free']}")
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
    packet = build_smoke_packet(root, include_pack=args.include_pack_check, run_inspections=not args.skip_inspections)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = root / args.markdown_out
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(markdown(packet), encoding="utf-8")
    if args.json:
        print(json.dumps(packet, indent=2, sort_keys=True))
    return 0 if packet["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
