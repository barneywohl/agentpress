#!/usr/bin/env python3
"""Verify the wave82 fresh-agent smoke replay receipt and emit a wave83 certificate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WAVE82 = "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-wave82.json"
WAVE81 = "agentpress/evidence/agent-facing-acceptance-one-command-smoke-packet-wave81.json"
WAVE80 = "agentpress/evidence/agent-facing-acceptance-first-command-dry-run-wave80.json"
WAVE79 = "agentpress/evidence/agent-facing-acceptance-launchpad-card-wave79.json"
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-smoke-replay-receipt-verifier-wave83.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_smoke_replay_receipt_verifier.py"
TEST_PATH = "tests/test_agent_facing_acceptance_smoke_replay_receipt_verifier.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-smoke-replay-receipt-verifier"
GATE_CLOSED = "closed_until_jake_explicit_approval"
REQUIRED_PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]
WAVE82_PACK_REQUIRED = [
    "scripts/agent_facing_acceptance_smoke_replay_receipt.py",
    "tests/test_agent_facing_acceptance_smoke_replay_receipt.py",
    WAVE82,
    WAVE82.replace(".json", ".md"),
]
EXPECTED_WAVE82_OUTPUTS = [WAVE79, WAVE79.replace(".json", ".md"), WAVE82, WAVE82.replace(".json", ".md")]
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


def check_clean(doc: dict[str, Any], label: str, blockers: list[str]) -> None:
    if doc.get("status") != "ok":
        blockers.append(f"{label}_status_not_ok: {doc.get('status')!r}")
    if doc.get("blockers") not in ([], None):
        blockers.append(f"{label}_has_blockers")
    if doc.get("public_actions_taken") not in ([], None):
        blockers.append(f"{label}_public_actions_contaminated")
    if doc.get("external_actions") not in ([], None):
        blockers.append(f"{label}_external_actions_contaminated")


def forbidden_hits(values: list[str]) -> list[str]:
    hits: set[str] = set()
    for value in values:
        for match in FORBIDDEN_RE.finditer(value or ""):
            hits.add(match.group(0).lower())
    return sorted(hits)


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
    required = REQUIRED_PACKAGE_FILES + WAVE82_PACK_REQUIRED
    result["required_included"] = [{"path": rel, "included": rel in names} for rel in required]
    return result


def build_certificate(root: Path, *, include_pack: bool = False) -> dict[str, Any]:
    generated_at = utc_now()
    blockers: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    load_summary: dict[str, dict[str, Any]] = {}
    for label, rel in [("wave82", WAVE82), ("wave81", WAVE81), ("wave80", WAVE80), ("wave79", WAVE79)]:
        doc, err = load_json(root / rel)
        if err or doc is None:
            docs[label] = {}
            load_summary[label] = {"path": rel, "loaded": False, "error": err}
            blockers.append(f"{label}_source_{err}: {rel}")
        else:
            docs[label] = doc
            load_summary[label] = {"path": rel, "loaded": True, "status": doc.get("status")}
            check_clean(doc, label, blockers)

    wave82, wave81, wave80, wave79 = docs["wave82"], docs["wave81"], docs["wave80"], docs["wave79"]
    selected = str(wave82.get("selected_command") or "")
    wave81_selected = str(wave81.get("selected_command") or "")
    wave81_first = (wave81.get("paste_ready_packet") or {}).get("first_command") if isinstance(wave81.get("paste_ready_packet"), dict) else None
    wave80_selected = (wave80.get("first_command_selection") or {}).get("selected") if isinstance(wave80.get("first_command_selection"), dict) else None
    wave79_recommended = wave79.get("recommended_next_command")
    command_chain = [selected, wave81_selected, str(wave81_first or ""), str(wave80_selected or ""), str(wave79_recommended or "")]
    command_consistency = {
        "wave82_selected_matches_wave81_selected": bool(selected and selected == wave81_selected),
        "wave82_selected_matches_wave81_paste_ready_first_command": bool(selected and selected == wave81_first),
        "wave82_selected_matches_wave80_selected": bool(selected and selected == wave80_selected),
        "wave82_selected_matches_wave79_recommended": bool(selected and selected == wave79_recommended),
    }
    for name, ok in command_consistency.items():
        if not ok:
            blockers.append(f"command_consistency_failed: {name}")

    replay = wave82.get("selected_command_replay") if isinstance(wave82.get("selected_command_replay"), dict) else {}
    if replay.get("returncode") != 0:
        blockers.append("wave82_selected_command_replay_returncode_not_zero")
    if replay.get("command") != selected:
        blockers.append("wave82_selected_command_replay_command_mismatch")
    if replay.get("local_safe") is not True or replay.get("inspection_only") is not True or replay.get("public_action_free") is not True:
        blockers.append("wave82_selected_command_replay_safety_flags_not_true")

    expected_outputs = wave82.get("expected_replay_outputs") if isinstance(wave82.get("expected_replay_outputs"), list) else []
    output_checks = []
    for rel in EXPECTED_WAVE82_OUTPUTS:
        row = {"path": rel, "declared": rel in expected_outputs, "exists_local": (root / rel).exists()}
        output_checks.append(row)
        if not row["declared"]:
            blockers.append(f"wave82_expected_output_missing_declared: {rel}")
        if not row["exists_local"]:
            blockers.append(f"wave82_expected_output_missing_local: {rel}")

    safety_text = [selected]
    for item in wave82.get("packet_command_safety", []) if isinstance(wave82.get("packet_command_safety"), list) else []:
        if isinstance(item, dict):
            safety_text.append(str(item.get("command") or ""))
            if item.get("local_safe") is not True or item.get("inspection_only") is not True or item.get("public_action_free") is not True or item.get("forbidden_match") not in (None, ""):
                blockers.append("wave82_packet_command_safety_failed")
    hits = forbidden_hits(safety_text)
    if hits:
        blockers.append(f"forbidden_command_text_detected: {hits}")

    source_pack = wave82.get("npm_pack_dry_run") if isinstance(wave82.get("npm_pack_dry_run"), dict) else {}
    source_pack_checks = []
    if source_pack.get("returncode") != 0 or source_pack.get("json_parseable") is not True:
        blockers.append("wave82_source_pack_dry_run_not_successful")
    included_by_source = {row.get("path"): row.get("included") for row in source_pack.get("required_included", []) if isinstance(row, dict)}
    for rel in WAVE82_PACK_REQUIRED:
        row = {"path": rel, "source_pack_included": included_by_source.get(rel) is True}
        source_pack_checks.append(row)
        if not row["source_pack_included"]:
            blockers.append(f"wave82_source_pack_missing_required: {rel}")

    pkg, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required: {row.get('path')}")

    digest = json.dumps({"wave82": wave82.get("receipt_id"), "selected": selected, "generated_at": generated_at}, sort_keys=True)
    certificate = {
        "certificate_id": "wave83-verifier-" + hashlib.sha256(digest.encode()).hexdigest()[:16],
        "source_receipt_id": wave82.get("receipt_id"),
        "selected_command": selected,
        "selected_command_replay_returncode": replay.get("returncode"),
        "command_chain_verified": all(command_consistency.values()),
        "expected_output_count": sum(1 for row in output_checks if row["declared"] and row["exists_local"]),
        "public_action_gate": GATE_CLOSED,
        "operator_statement": "Wave82 smoke replay receipt, command chain, expected outputs, package inclusion, safety flags, and no-public-action boundary were verified locally only.",
    }
    return {
        "kind": "agentpress_agent_facing_acceptance_smoke_replay_receipt_verifier",
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "ok" if not blockers else "blocked",
        "local_only": True,
        "source_receipt": WAVE82,
        "operator_certificate": certificate,
        "loaded_sources": load_summary,
        "command_consistency": command_consistency,
        "expected_output_checks": output_checks,
        "source_wave82_package_checks": source_pack_checks,
        "package_json_inclusion_expectations": pkg,
        "npm_pack_dry_run": pack,
        "public_action_gate": GATE_CLOSED,
        "public_actions_taken": [],
        "external_actions": [],
        "blockers": blockers,
    }


def markdown(cert: dict[str, Any]) -> str:
    op = cert["operator_certificate"]
    lines = [
        "# Agent-facing acceptance smoke replay receipt verifier (wave83)",
        "",
        f"- Status: `{cert['status']}`",
        f"- Generated at: `{cert['generated_at']}`",
        f"- Certificate: `{op['certificate_id']}`",
        f"- Source receipt: `{op.get('source_receipt_id')}`",
        f"- Selected command: `{op.get('selected_command')}`",
        f"- Replay return code: `{op.get('selected_command_replay_returncode')}`",
        f"- Command chain verified: `{op.get('command_chain_verified')}`",
        f"- Expected outputs verified: `{op.get('expected_output_count')}`",
        f"- Public action gate: `{cert['public_action_gate']}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Blockers",
    ]
    lines.extend([f"- {b}" for b in cert.get("blockers", [])] or ["- None"])
    lines.extend(["", "## Operator statement", "", op["operator_statement"], ""])
    return "\n".join(lines)


def write_outputs(root: Path, cert: dict[str, Any], out_rel: str, md_rel: str) -> None:
    out = root / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cert, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = root / md_rel
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(markdown(cert), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    cert = build_certificate(root, include_pack=False)
    write_outputs(root, cert, args.out, args.markdown_out)
    if args.include_pack_check:
        cert = build_certificate(root, include_pack=True)
        write_outputs(root, cert, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(cert, indent=2, sort_keys=True))
    return 0 if cert["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
