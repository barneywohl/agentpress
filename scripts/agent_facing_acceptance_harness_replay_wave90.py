#!/usr/bin/env python3
"""Replay a recipient AgentPress acceptance packet and emit pass/fail evidence (wave90)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_PACKET = "agentpress/evidence/agent-facing-acceptance-replay-drill-recipient-packet-wave86.json"
SOURCE_PACKET_MD = SOURCE_PACKET.replace(".json", ".md")
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_harness_replay_wave90.py"
TEST_PATH = "tests/test_agent_facing_acceptance_harness_replay_wave90.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-harness-replay-wave90"
GATE_CLOSED = "closed_until_jake_explicit_approval"
FORBIDDEN_RE = re.compile(r"\b(npm\s+publish|git\s+push|deploy|curl\b|wget\b|payment|wallet|secret|token|outreach|email|send)\b", re.I)
REQUIRED_PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD, SOURCE_PACKET, SOURCE_PACKET_MD]


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


def run_command(root: Path, command: str) -> dict[str, Any]:
    argv = command_to_npm_run(command)
    if argv is None:
        return {"command": command, "returncode": 127, "error": "unsupported_command_shape", "local_only": True, "public_action_free": False}
    proc = subprocess.run(argv, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=180)
    return {
        "command": command,
        "argv": argv,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-1600:],
        "stderr_tail": proc.stderr[-1600:],
        "local_only": True,
        "public_action_free": True,
    }


def package_expectations(root: Path) -> tuple[dict[str, Any], list[str]]:
    package, err = load_json(root / "package.json")
    if err or package is None:
        return {"script": "", "required": []}, [f"package_json_{err}"]
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    files = package.get("files") if isinstance(package.get("files"), list) else []
    blockers: list[str] = []
    if SCRIPT_NAME not in scripts:
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
    return {"script": scripts.get(SCRIPT_NAME, ""), "required": required}, blockers


def run_pack(root: Path) -> dict[str, Any]:
    proc = subprocess.run(["npm", "pack", "--dry-run", "--json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
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
    for rel in REQUIRED_PACKAGE_FILES:
        result["required_included"].append({"path": rel, "included": rel in names})
    return result


def verify_expected_outputs(root: Path, paths: list[Any]) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    if len(paths) < 2:
        blockers.append("expected_outputs_lt_2")
    for raw in paths:
        rel = str(raw)
        path = root / rel
        row: dict[str, Any] = {"path": rel, "exists": path.exists()}
        if not path.exists():
            blockers.append(f"expected_output_missing: {rel}")
        elif rel.endswith(".json"):
            data, err = load_json(path)
            row["json_parseable"] = err is None
            if err:
                blockers.append(f"expected_output_json_{err}: {rel}")
            else:
                row["status"] = data.get("status")
                row["public_actions_taken"] = data.get("public_actions_taken")
                row["external_actions"] = data.get("external_actions")
                if data.get("status") != "ok":
                    blockers.append(f"expected_output_status_not_ok: {rel}")
                if data.get("public_actions_taken") not in ([], None) or data.get("external_actions") not in ([], None):
                    blockers.append(f"expected_output_public_external_contamination: {rel}")
        checks.append(row)
    return checks, blockers


def build_harness(root: Path, *, include_pack: bool = False, replay: bool = True) -> dict[str, Any]:
    blockers: list[str] = []
    source, err = load_json(root / SOURCE_PACKET)
    if err or source is None:
        source = {}
        blockers.append(f"source_packet_{err}: {SOURCE_PACKET}")
    if source.get("status") != "ok":
        blockers.append(f"source_packet_status_not_ok: {source.get('status')!r}")
    if source.get("blockers") not in ([], None):
        blockers.append("source_packet_has_blockers")
    if source.get("public_actions_taken") not in ([], None) or source.get("external_actions") not in ([], None):
        blockers.append("source_packet_public_external_contamination")
    if source.get("public_action_gate") != GATE_CLOSED:
        blockers.append("source_packet_gate_not_closed")

    packet = source.get("recipient_packet") if isinstance(source.get("recipient_packet"), dict) else {}
    commands = packet.get("safe_paste_commands") if isinstance(packet.get("safe_paste_commands"), list) else []
    command = str(commands[0]) if len(commands) == 1 else ""
    if packet.get("recommended_safe_paste_command_count") != 1 or len(commands) != 1:
        blockers.append("safe_paste_command_count_not_one")
    hits = forbidden_hits([command, "\n".join(str(x) for x in packet.get("operator_instructions", []))])
    if hits:
        blockers.append(f"forbidden_operator_or_command_text_detected: {hits}")

    replay_result = run_command(root, command) if replay and command else {"skipped": True, "command": command, "returncode": 0}
    if replay_result.get("returncode") != 0:
        blockers.append("recipient_packet_replay_failed")

    output_checks, output_blockers = verify_expected_outputs(root, packet.get("expected_outputs") if isinstance(packet.get("expected_outputs"), list) else [])
    blockers.extend(output_blockers)
    pkg, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required: {row.get('path')}")

    evidence_id = "wave90-harness-" + hashlib.sha256(json.dumps({"source": source.get("recipient_packet", {}).get("packet_id"), "command": command}, sort_keys=True).encode()).hexdigest()[:16]
    return {
        "kind": "agentpress_agent_facing_acceptance_harness_replay",
        "schema_version": 1,
        "generated_at": utc_now(),
        "evidence_id": evidence_id,
        "status": "ok" if not blockers else "blocked",
        "source_packet": SOURCE_PACKET,
        "safe_paste_command": command,
        "replay_result": replay_result,
        "expected_output_checks": output_checks,
        "package_json_inclusion_expectations": pkg,
        "npm_pack_dry_run": pack,
        "painpoint_solved": "A recipient can replay the handoff/proof packet with one local CLI and get machine-readable pass/fail evidence instead of manually interpreting scattered receipts.",
        "public_action_gate": GATE_CLOSED,
        "public_actions_taken": [],
        "external_actions": [],
        "operator_text_forbidden_hits": hits,
        "blockers": blockers,
    }


def markdown(doc: dict[str, Any]) -> str:
    lines = [
        "# Agent-facing acceptance harness replay (wave90)",
        "",
        f"- Status: `{doc['status']}`",
        f"- Evidence ID: `{doc['evidence_id']}`",
        f"- Safe paste command: `{doc['safe_paste_command']}`",
        f"- Replay return code: `{doc['replay_result'].get('returncode')}`",
        f"- Public action gate: `{doc['public_action_gate']}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Painpoint solved",
        doc["painpoint_solved"],
        "",
        "## Expected output checks",
    ]
    lines.extend([f"- `{row['path']}` exists={row.get('exists')} status={row.get('status', 'n/a')}" for row in doc.get("expected_output_checks", [])])
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
    parser.add_argument("--skip-replay", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    doc = build_harness(root, include_pack=False, replay=not args.skip_replay)
    write_outputs(root, doc, args.out, args.markdown_out)
    if args.include_pack_check:
        doc = build_harness(root, include_pack=True, replay=not args.skip_replay)
        write_outputs(root, doc, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    return 0 if doc["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
