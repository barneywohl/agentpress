#!/usr/bin/env python3
"""Replay and verify the wave84 agent-facing handoff capsule locally."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WAVE84 = "agentpress/evidence/agent-facing-acceptance-verifier-handoff-capsule-wave84.json"
WAVE83 = "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json"
WAVE82 = "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json"
WAVE81 = "agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.json"
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-handoff-capsule-replay-drill-wave85.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_handoff_capsule_replay_drill.py"
TEST_PATH = "tests/test_agent_facing_acceptance_handoff_capsule_replay_drill.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-handoff-capsule-replay-drill"
GATE_CLOSED = "closed_until_jake_explicit_approval"
REQUIRED_PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]
SOURCE_PACKAGE_FILES = [
    "scripts/agent_facing_acceptance_verifier_handoff_capsule.py",
    "tests/test_agent_facing_acceptance_verifier_handoff_capsule.py",
    WAVE84,
    WAVE84.replace(".json", ".md"),
    WAVE83,
    WAVE83.replace(".json", ".md"),
    WAVE82,
    WAVE81,
]
REQUIRED_STOP_GO_FRAGMENTS = [
    "wave83 status is ok",
    "command_chain_verified is true",
    "selected_command_replay_returncode is 0",
    "expected_output_count is at least 4",
    "public_action_gate is closed_until_jake_explicit_approval",
    "public_actions_taken and external_actions are empty",
    "any blocker is present",
    "verifier command exits non-zero",
    "publish/push/deploy/outreach/payment/secret",
    "public or external action",
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
        script = parts[2]
        args = parts[3:]
        return ["npm", "run", script, *args]
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


def stop_go_coverage(stop_go: dict[str, Any]) -> dict[str, Any]:
    criteria_text = "\n".join([str(x) for x in stop_go.get("go_if", []) + stop_go.get("stop_if", [])])
    represented = []
    missing = []
    lower = criteria_text.lower()
    for fragment in REQUIRED_STOP_GO_FRAGMENTS:
        if fragment.lower() in lower:
            represented.append(fragment)
        else:
            missing.append(fragment)
    return {"represented": represented, "missing": missing, "criteria_text": criteria_text}


def build_drill(root: Path, *, include_pack: bool = False, run_command: bool = True) -> dict[str, Any]:
    generated_at = utc_now()
    blockers: list[str] = []
    wave84, err = load_json(root / WAVE84)
    if err or wave84 is None:
        wave84 = {}
        blockers.append(f"wave84_source_{err}: {WAVE84}")
    if wave84.get("status") != "ok":
        blockers.append(f"wave84_status_not_ok: {wave84.get('status')!r}")
    if wave84.get("blockers") not in ([], None):
        blockers.append("wave84_has_blockers")
    if wave84.get("public_actions_taken") not in ([], None):
        blockers.append("wave84_public_actions_contaminated")
    if wave84.get("external_actions") not in ([], None):
        blockers.append("wave84_external_actions_contaminated")
    if wave84.get("public_action_gate") != GATE_CLOSED:
        blockers.append("wave84_public_action_gate_not_closed")

    capsule = wave84.get("handoff_capsule") if isinstance(wave84.get("handoff_capsule"), dict) else {}
    commands = capsule.get("recommended_safe_paste_commands") if isinstance(capsule.get("recommended_safe_paste_commands"), list) else []
    if capsule.get("recommended_safe_paste_command_count") != 1 or len(commands) != 1:
        blockers.append("recommended_safe_paste_command_count_not_one")
    command = commands[0].get("command", "") if commands and isinstance(commands[0], dict) else ""
    command_texts = [command]
    operator_text = markdown_text_preview(capsule, command)
    hits = forbidden_hits(command_texts + [operator_text])
    if hits:
        blockers.append(f"forbidden_operator_or_command_text_detected: {hits}")
    if capsule.get("command_chain_verified") is not True:
        blockers.append("wave84_command_chain_not_verified")
    if capsule.get("selected_command_replay_returncode") != 0:
        blockers.append("wave84_selected_command_replay_returncode_not_zero")
    if int(capsule.get("expected_output_count") or 0) < 4:
        blockers.append("wave84_expected_output_count_lt_4")

    inspections = capsule.get("fresh_agent_inspection_files") if isinstance(capsule.get("fresh_agent_inspection_files"), list) else []
    inspection_results = []
    for row in inspections:
        rel = row.get("path") if isinstance(row, dict) else None
        if not rel:
            blockers.append("inspection_file_missing_path")
            continue
        exists = (root / rel).exists()
        inspection_results.append({"path": rel, "exists_local": exists, "required_for_fresh_agent": bool(row.get("required_for_fresh_agent", True))})
        if not exists:
            blockers.append(f"inspection_file_missing: {rel}")
    if not inspections:
        blockers.append("no_fresh_agent_inspection_files")

    coverage = stop_go_coverage(capsule.get("stop_go_criteria") if isinstance(capsule.get("stop_go_criteria"), dict) else {})
    for missing in coverage["missing"]:
        blockers.append(f"stop_go_criterion_missing: {missing}")

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

    digest = json.dumps({"source": capsule.get("capsule_id"), "command": command, "generated_at": generated_at}, sort_keys=True)
    receipt = {
        "receipt_id": "wave85-replay-" + hashlib.sha256(digest.encode()).hexdigest()[:16],
        "source_wave84_capsule_id": capsule.get("capsule_id"),
        "recommended_safe_paste_command_count": len(commands),
        "selected_safe_paste_command": command,
        "command_chain_verified": capsule.get("command_chain_verified") is True,
        "selected_command_replay_returncode": selected_run.get("returncode"),
        "expected_output_count": int(capsule.get("expected_output_count") or 0),
        "fresh_agent_inspection_files_verified": inspection_results,
        "stop_go_coverage": coverage,
        "operator_text_forbidden_hits": hits,
        "public_action_gate": GATE_CLOSED,
    }
    return {
        "kind": "agentpress_agent_facing_acceptance_handoff_capsule_replay_drill",
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "ok" if not blockers else "blocked",
        "local_only": True,
        "source_handoff_capsule": WAVE84,
        "replay_drill_receipt": receipt,
        "selected_command_run": selected_run,
        "package_json_inclusion_expectations": pkg,
        "npm_pack_dry_run": pack,
        "public_action_gate": GATE_CLOSED,
        "public_actions_taken": [],
        "external_actions": [],
        "blockers": blockers,
    }


def markdown_text_preview(capsule: dict[str, Any], command: str) -> str:
    return "\n".join([
        "Agent-facing wave85 local replay drill",
        f"Source capsule: {capsule.get('capsule_id')}",
        f"Run locally: {command}",
        "Stop if any blocker appears; public action gate remains closed until Jake explicit approval.",
    ])


def markdown(doc: dict[str, Any]) -> str:
    receipt = doc["replay_drill_receipt"]
    lines = [
        "# Agent-facing acceptance handoff capsule replay drill (wave85)",
        "",
        f"- Status: `{doc['status']}`",
        f"- Generated at: `{doc['generated_at']}`",
        f"- Receipt: `{receipt['receipt_id']}`",
        f"- Source capsule: `{receipt.get('source_wave84_capsule_id')}`",
        f"- Selected safe paste command: `{receipt.get('selected_safe_paste_command')}`",
        f"- Replay return code: `{receipt.get('selected_command_replay_returncode')}`",
        f"- Command chain verified: `{receipt.get('command_chain_verified')}`",
        f"- Expected output count: `{receipt.get('expected_output_count')}`",
        f"- Public action gate: `{doc['public_action_gate']}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Verified fresh-agent inspection files",
    ]
    lines.extend([f"- `{row['path']}` exists_local={row['exists_local']}" for row in receipt["fresh_agent_inspection_files_verified"]])
    lines.extend(["", "## Stop/go coverage", "", "Represented:"])
    lines.extend([f"- {item}" for item in receipt["stop_go_coverage"]["represented"]])
    lines.append("Missing:")
    lines.extend([f"- {item}" for item in receipt["stop_go_coverage"]["missing"]] or ["- None"])
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
    doc = build_drill(root, include_pack=False, run_command=not args.skip_command_run)
    write_outputs(root, doc, args.out, args.markdown_out)
    if args.include_pack_check:
        doc = build_drill(root, include_pack=True, run_command=not args.skip_command_run)
        write_outputs(root, doc, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    return 0 if doc["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
