#!/usr/bin/env python3
"""Build a local-only wave86 recipient packet from the wave85 replay drill receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WAVE85 = "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.json"
WAVE85_MD = WAVE85.replace(".json", ".md")
WAVE84 = "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.json"
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-replay-drill-recipient-packet-wave86.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-replay-drill-recipient-packet-wave86.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_replay_drill_recipient_packet.py"
TEST_PATH = "tests/test_agent_facing_acceptance_replay_drill_recipient_packet.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-replay-drill-recipient-packet"
GATE_CLOSED = "closed_until_jake_explicit_approval"
REQUIRED_PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]
SOURCE_PACKAGE_FILES = [
    WAVE85,
    WAVE85_MD,
    WAVE84,
    WAVE84.replace(".json", ".md"),
    "scripts/agent_facing_acceptance_handoff_capsule_replay_drill.py",
    "tests/test_agent_facing_acceptance_handoff_capsule_replay_drill.py",
]
REQUIRED_STOP_GO_FRAGMENTS = [
    "wave85 status is ok",
    "blockers is empty",
    "selected_command_replay_returncode is 0",
    "command_chain_verified is true",
    "expected_output_count is at least 4",
    "no missing criteria",
    "public_action_gate is closed_until_jake_explicit_approval",
    "public_actions_taken and external_actions are empty",
]
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


def forbidden_hits(values: list[str]) -> list[str]:
    hits: set[str] = set()
    for value in values:
        for match in FORBIDDEN_RE.finditer(value or ""):
            hits.add(match.group(0).lower())
    return sorted(hits)


def command_to_npm_run(command: str) -> list[str] | None:
    parts = command.strip().split()
    if len(parts) >= 3 and parts[0] == "npm" and parts[1] == "run":
        return ["npm", "run", parts[2], *parts[3:]]
    return None


def run_selected_command(root: Path, command: str) -> dict[str, Any]:
    argv = command_to_npm_run(command)
    if argv is None:
        return {"command": command, "returncode": 127, "error": "unsupported_command_shape", "local_only": True, "public_action_free": False}
    proc = subprocess.run(argv, cwd=root, text=True, capture_output=True, check=False, timeout=120)
    return {
        "command": command,
        "argv": argv,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-1200:],
        "stderr_tail": proc.stderr[-1200:],
        "local_only": True,
        "public_action_free": True,
    }


def stop_go_coverage(packet: dict[str, Any]) -> dict[str, Any]:
    text = "\n".join(str(x) for x in packet.get("go_if", []) + packet.get("stop_if", []))
    lower = text.lower()
    represented = [item for item in REQUIRED_STOP_GO_FRAGMENTS if item.lower() in lower]
    missing = [item for item in REQUIRED_STOP_GO_FRAGMENTS if item.lower() not in lower]
    return {"represented": represented, "missing": missing, "criteria_text": text}


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
    for rel in REQUIRED_PACKAGE_FILES:
        row = {"path": rel, "exists_local": (root / rel).exists(), "listed_in_package_files": rel in files}
        required.append(row)
        if not row["exists_local"] and rel not in generated:
            blockers.append(f"package_required_missing_local: {rel}")
        if not row["listed_in_package_files"]:
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
    for rel in REQUIRED_PACKAGE_FILES + SOURCE_PACKAGE_FILES:
        result["required_included"].append({"path": rel, "included": rel in names})
    return result


def build_packet(root: Path, *, include_pack: bool = False, run_command: bool = True) -> dict[str, Any]:
    generated_at = utc_now()
    blockers: list[str] = []
    wave85, err = load_json(root / WAVE85)
    if err or wave85 is None:
        wave85 = {}
        blockers.append(f"wave85_source_{err}: {WAVE85}")
    if wave85.get("status") != "ok":
        blockers.append(f"wave85_status_not_ok: {wave85.get('status')!r}")
    if wave85.get("blockers") not in ([], None):
        blockers.append("wave85_has_blockers")
    if wave85.get("public_actions_taken") not in ([], None):
        blockers.append("wave85_public_actions_contaminated")
    if wave85.get("external_actions") not in ([], None):
        blockers.append("wave85_external_actions_contaminated")
    if wave85.get("public_action_gate") != GATE_CLOSED:
        blockers.append("wave85_public_action_gate_not_closed")

    receipt = wave85.get("replay_drill_receipt") if isinstance(wave85.get("replay_drill_receipt"), dict) else {}
    command = str(receipt.get("selected_safe_paste_command") or "")
    command_count = int(receipt.get("recommended_safe_paste_command_count") or 0)
    if command_count != 1 or not command:
        blockers.append("safe_paste_command_count_not_one")
    if receipt.get("selected_command_replay_returncode") != 0:
        blockers.append("wave85_selected_command_replay_returncode_not_zero")
    if receipt.get("command_chain_verified") is not True:
        blockers.append("wave85_command_chain_not_verified")
    if int(receipt.get("expected_output_count") or 0) < 4:
        blockers.append("wave85_expected_output_count_lt_4")
    coverage = receipt.get("stop_go_coverage") if isinstance(receipt.get("stop_go_coverage"), dict) else {}
    if coverage.get("missing") not in ([], None):
        blockers.append("wave85_missing_stop_go_coverage")

    packet = {
        "packet_id": "wave86-recipient-" + hashlib.sha256(json.dumps({"source": receipt.get("receipt_id"), "command": command}, sort_keys=True).encode()).hexdigest()[:16],
        "source_wave85_receipt_id": receipt.get("receipt_id"),
        "fresh_agent_role": "You are a fresh local agent verifying AgentPress agent-facing acceptance evidence.",
        "safe_paste_commands": [command] if command else [],
        "recommended_safe_paste_command_count": 1 if command else 0,
        "operator_instructions": [
            "Stay local-only in this repository.",
            "Run exactly the single safe paste command listed in this packet.",
            "Inspect the generated JSON and Markdown evidence files.",
            "If any blocker appears, stop and record the blocker locally.",
            "Do not take any public-write or account-touching action before Jake explicit approval.",
        ],
        "go_if": [
            "wave85 status is ok",
            "blockers is empty",
            "selected_command_replay_returncode is 0",
            "command_chain_verified is true",
            "expected_output_count is at least 4",
            "no missing criteria",
            "public_action_gate is closed_until_jake_explicit_approval",
            "public_actions_taken and external_actions are empty",
        ],
        "stop_if": [
            "wave85 status is not ok",
            "blockers is not empty",
            "selected_command_replay_returncode is not 0",
            "command_chain_verified is not true",
            "expected_output_count is below 4",
            "missing criteria are present",
            "public_actions_taken or external_actions are not empty",
        ],
        "expected_outputs": [
            "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json",
            "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md",
            WAVE85,
            WAVE85_MD,
        ],
        "public_action_gate": GATE_CLOSED,
    }
    packet_coverage = stop_go_coverage(packet)
    for missing in packet_coverage["missing"]:
        blockers.append(f"packet_stop_go_criterion_missing: {missing}")

    operator_text = "\n".join(packet["operator_instructions"])
    hits = forbidden_hits([command, operator_text])
    if hits:
        blockers.append(f"forbidden_operator_or_command_text_detected: {hits}")

    selected_run = run_selected_command(root, command) if run_command and command else {"skipped": True, "command": command, "returncode": 0}
    if selected_run.get("returncode") != 0:
        blockers.append("selected_command_replay_failed")

    pkg, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required: {row.get('path')}")

    return {
        "kind": "agentpress_agent_facing_acceptance_replay_drill_recipient_packet",
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "ok" if not blockers else "blocked",
        "local_only": True,
        "source_replay_drill_receipt": WAVE85,
        "recipient_packet": packet,
        "packet_stop_go_coverage": packet_coverage,
        "operator_text_forbidden_hits": hits,
        "selected_command_run": selected_run,
        "package_json_inclusion_expectations": pkg,
        "npm_pack_dry_run": pack,
        "public_action_gate": GATE_CLOSED,
        "public_actions_taken": [],
        "external_actions": [],
        "blockers": blockers,
    }


def markdown(doc: dict[str, Any]) -> str:
    packet = doc["recipient_packet"]
    lines = [
        "# Agent-facing acceptance replay drill recipient packet (wave86)",
        "",
        f"- Status: `{doc['status']}`",
        f"- Generated at: `{doc['generated_at']}`",
        f"- Packet: `{packet['packet_id']}`",
        f"- Source wave85 receipt: `{packet.get('source_wave85_receipt_id')}`",
        f"- Safe paste command count: `{packet['recommended_safe_paste_command_count']}`",
        f"- Safe paste command: `{packet['safe_paste_commands'][0] if packet['safe_paste_commands'] else ''}`",
        f"- Replay return code: `{doc['selected_command_run'].get('returncode')}`",
        f"- Public action gate: `{doc['public_action_gate']}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Fresh-agent instructions",
    ]
    lines.extend([f"- {item}" for item in packet["operator_instructions"]])
    lines.extend(["", "## Go criteria"])
    lines.extend([f"- {item}" for item in packet["go_if"]])
    lines.extend(["", "## Stop criteria"])
    lines.extend([f"- {item}" for item in packet["stop_if"]])
    lines.extend(["", "## Blockers"])
    lines.extend([f"- {b}" for b in doc.get("blockers", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, doc: dict[str, Any], out_rel: str, md_rel: str) -> None:
    out = root / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = root / md_rel
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(markdown(doc), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--skip-command-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    doc = build_packet(root, include_pack=False, run_command=not args.skip_command_run)
    write_outputs(root, doc, args.out, args.markdown_out)
    if args.include_pack_check:
        doc = build_packet(root, include_pack=True, run_command=not args.skip_command_run)
        write_outputs(root, doc, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    return 0 if doc["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
