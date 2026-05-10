#!/usr/bin/env python3
"""Build an agent-facing launchpad recovery card with safe local commands (wave91)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUT = "agentpress/evidence/agent-facing-launchpad-recovery-card-wave91.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-launchpad-recovery-card-wave91.md"
SCRIPT_PATH = "scripts/agent_facing_launchpad_recovery_card.py"
TEST_PATH = "tests/test_agent_facing_launchpad_recovery_card.py"
SCRIPT_NAME = "rc:agent-facing-launchpad-recovery-card"
WIZARD_PATH = "agentpress/onboarding/first-run-wizard.json"
HARNESS_REPLAY = "agentpress/evidence/agent-facing-acceptance-harness-replay-wave90.json"
GATE_CLOSED = "closed_until_jake_explicit_approval"
FORBIDDEN_RE = re.compile(r"\b(npm\s+publish|git\s+push|deploy|curl\b|wget\b|payment|wallet|secret|token|outreach|email|send)\b", re.I)
SAFE_COMMANDS = [
    "npm run doctor --silent",
    "npm run rc:agent-facing-acceptance-harness-replay-wave90 --silent",
    "python3 scripts/agentpress.py launchpad --json",
]
REQUIRED_PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]


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
    for rel in REQUIRED_PACKAGE_FILES:
        row = {"path": rel, "exists_local": (root / rel).exists(), "listed_in_package_files": rel in files}
        required.append(row)
        if not row["exists_local"] and rel not in {DEFAULT_OUT, DEFAULT_MD}:
            blockers.append(f"package_required_missing_local: {rel}")
        if not row["listed_in_package_files"]:
            blockers.append(f"package_json_files_missing: {rel}")
    return {"script": scripts.get(SCRIPT_NAME, ""), "required": required}, blockers


def run_pack(root: Path) -> dict[str, Any]:
    proc = subprocess.run(["npm", "pack", "--dry-run", "--json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=180)
    result: dict[str, Any] = {"command": "npm pack --dry-run --json", "returncode": proc.returncode, "json_parseable": False, "required_included": []}
    if proc.returncode != 0:
        result.update({"stdout_tail": proc.stdout[-1000:], "stderr_tail": proc.stderr[-1000:]})
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


def summarize_wizard(root: Path, blockers: list[str]) -> dict[str, Any]:
    wizard, err = load_json(root / WIZARD_PATH)
    if err or wizard is None:
        blockers.append(f"launchpad_wizard_{err}: {WIZARD_PATH}")
        return {"path": WIZARD_PATH, "status": "missing"}
    status = str(wizard.get("status", "present"))
    steps = wizard.get("steps") if isinstance(wizard.get("steps"), list) else []
    return {
        "path": WIZARD_PATH,
        "status": status,
        "step_count": len(steps),
        "has_copy_paste_command": any("command" in x for x in steps if isinstance(x, dict)),
    }


def summarize_harness(root: Path, blockers: list[str]) -> dict[str, Any]:
    harness, err = load_json(root / HARNESS_REPLAY)
    if err or harness is None:
        blockers.append(f"acceptance_harness_{err}: {HARNESS_REPLAY}")
        return {"path": HARNESS_REPLAY, "status": "missing"}
    if harness.get("status") != "ok":
        blockers.append(f"acceptance_harness_status_not_ok: {harness.get('status')!r}")
    return {
        "path": HARNESS_REPLAY,
        "status": harness.get("status"),
        "safe_paste_command": harness.get("safe_paste_command"),
        "public_action_gate": harness.get("public_action_gate"),
    }


def build_card(root: Path, *, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    command_hits = forbidden_hits(SAFE_COMMANDS)
    if command_hits:
        blockers.append(f"unsafe_recovery_command_text_detected: {command_hits}")

    package, package_blockers = package_expectations(root)
    blockers.extend(package_blockers)
    wizard = summarize_wizard(root, blockers)
    harness = summarize_harness(root, blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required: {row.get('path')}")

    card_id = "wave91-launchpad-" + hashlib.sha256(json.dumps({"commands": SAFE_COMMANDS, "harness": harness.get("status")}, sort_keys=True).encode()).hexdigest()[:16]
    return {
        "kind": "agentpress_agent_facing_launchpad_recovery_card",
        "schema_version": 1,
        "generated_at": utc_now(),
        "card_id": card_id,
        "status": "ok" if not blockers else "blocked",
        "launchpad_wizard": wizard,
        "acceptance_harness_replay": harness,
        "safe_recovery_commands": SAFE_COMMANDS,
        "agent_facing_outcome": "A fresh agent gets three local-only recovery commands that verify health, replay acceptance evidence, and reopen launchpad diagnostics without public writes.",
        "operator_decision_needed": "none_until_public_publish_or_push",
        "public_action_gate": GATE_CLOSED,
        "public_actions_taken": [],
        "external_actions": [],
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "blockers": blockers,
    }


def markdown(doc: dict[str, Any]) -> str:
    lines = [
        "# Agent-facing launchpad recovery card (wave91)",
        "",
        f"- Status: `{doc['status']}`",
        f"- Card ID: `{doc['card_id']}`",
        f"- Public action gate: `{doc['public_action_gate']}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Safe recovery commands",
    ]
    lines.extend([f"- `{cmd}`" for cmd in doc.get("safe_recovery_commands", [])])
    lines.extend(["", "## Agent-facing outcome", doc["agent_facing_outcome"], "", "## Blockers"])
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
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    doc = build_card(root, include_pack=False)
    write_outputs(root, doc, args.out, args.markdown_out)
    if args.include_pack_check:
        doc = build_card(root, include_pack=True)
        write_outputs(root, doc, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    return 0 if doc["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
