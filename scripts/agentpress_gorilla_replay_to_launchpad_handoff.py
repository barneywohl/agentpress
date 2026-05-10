#!/usr/bin/env python3
"""Build a launchpad-ready recipient handoff from the Gorilla replay receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_RECEIPT = "agentpress/evidence/agentpress-gorilla-replay-receipt-collector-wave97.json"
DEFAULT_RECEIPT_MD = "agentpress/evidence/agentpress-gorilla-replay-receipt-collector-wave97.md"
DEFAULT_OUT = "agentpress/evidence/agentpress-gorilla-replay-to-launchpad-handoff-wave98.json"
DEFAULT_MD = "agentpress/evidence/agentpress-gorilla-replay-to-launchpad-handoff-wave98.md"
SCRIPT_PATH = "scripts/agentpress_gorilla_replay_to_launchpad_handoff.py"
TEST_PATH = "tests/test_agentpress_gorilla_replay_to_launchpad_handoff.py"
SCRIPT_NAME = "rc:agentpress-gorilla-replay-to-launchpad-handoff"
PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD, DEFAULT_RECEIPT, DEFAULT_RECEIPT_MD]
GENERATED_ARTIFACTS = {DEFAULT_OUT, DEFAULT_MD}
FORBIDDEN_RE = re.compile(r"\b(git\s+push|npm\s+publish|deploy|payment|wallet|secret|token|outreach|email|sendgrid|external-message|external\s+message|curl\s+http|wget\s+http|sudo|rm\s+-rf)\b", re.I)
LOCAL_PREFIXES = ("python3 scripts/agentpress.py ", "npm run ", "node bin/agentpress.js ", "echo ")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"json_error:{exc}"
    return (data, None) if isinstance(data, dict) else (None, "json_root_not_object")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


def command_is_local_only(command: str) -> bool:
    text = " ".join(str(command).split())
    return bool(text) and text.startswith(LOCAL_PREFIXES) and not FORBIDDEN_RE.search(text)


def package_expectations(root: Path) -> tuple[dict[str, Any], list[str]]:
    pkg, err = load_json(root / "package.json")
    if err or pkg is None:
        return {"script": "", "required": []}, [f"package_json_{err}"]
    scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
    files = pkg.get("files") if isinstance(pkg.get("files"), list) else []
    blockers: list[str] = []
    if SCRIPT_NAME not in scripts:
        blockers.append(f"package_json_missing_script:{SCRIPT_NAME}")
    required: list[dict[str, Any]] = []
    for rel in PACKAGE_FILES:
        row = {"path": rel, "exists_local": (root / rel).exists(), "listed_in_package_files": rel in files}
        required.append(row)
        if rel not in GENERATED_ARTIFACTS and not row["exists_local"]:
            blockers.append(f"package_required_missing_local:{rel}")
        if not row["listed_in_package_files"]:
            blockers.append(f"package_json_files_missing:{rel}")
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
    names = {item.get("path") for item in (payload[0].get("files", []) if isinstance(payload, list) and payload else []) if isinstance(item, dict)}
    result["required_included"] = [{"path": rel, "included": rel in names} for rel in PACKAGE_FILES]
    return result


def normalize_replay_commands(receipt: dict[str, Any], blockers: list[str]) -> list[dict[str, Any]]:
    rows = receipt.get("replay_commands") if isinstance(receipt.get("replay_commands"), list) else []
    if not rows:
        blockers.append("receipt_missing_replay_commands")
        return []
    handoff_steps: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            blockers.append(f"receipt_replay_command_not_object:{idx}")
            continue
        command = str(row.get("command", ""))
        safe = command_is_local_only(command) and row.get("safe_local_only") is True and row.get("status") == "ready_to_run_locally"
        if not safe:
            blockers.append(f"receipt_replay_command_not_launchpad_safe:{idx}")
        handoff_steps.append({
            "step": idx,
            "command": command,
            "launchpad_surface": "cli-first-run-card",
            "safe_local_only": safe,
            "first_run_instruction": "Paste into a private checkout only after reading the safety gate." if safe else "Do not run; command is blocked by handoff validation.",
            "expected_local_check": "local artifact refresh or proof capture completes without external/public action" if safe else "blocked",
            "acceptance_evidence": "record stdout/stderr plus resulting local artifact path in the task proof bundle" if safe else "blocked",
        })
    return handoff_steps


def build_handoff(root: Path, *, receipt_rel: str = DEFAULT_RECEIPT, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    receipt, err = load_json(root / receipt_rel)
    if err or receipt is None:
        receipt = {}
        blockers.append(f"receipt_{err}:{receipt_rel}")
    if receipt.get("status") != "ok":
        blockers.append("receipt_status_not_ok")
    if receipt.get("blockers") != []:
        blockers.append("receipt_blockers_not_empty")
    for field in ("public_actions_taken", "external_actions", "payment_actions_taken"):
        if receipt.get(field) != []:
            blockers.append(f"receipt_{field}_not_empty")
    if receipt.get("secret_material_included") is not False:
        blockers.append("receipt_secret_material_not_false")
    handoff_steps = normalize_replay_commands(receipt, blockers)
    if not any(str(step.get("command", "")).startswith("python3 scripts/agentpress.py ") for step in handoff_steps):
        blockers.append("handoff_missing_agentpress_cli_first_run_command")
    package, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required:{row.get('path')}")
    receipt_hash = sha256_file(root / receipt_rel)
    launchpad_card = {
        "card_id": "wave98-gorilla-launchpad-handoff-" + receipt_hash[:12],
        "source_receipt": receipt_rel,
        "source_receipt_sha256": receipt_hash,
        "source_receipt_id": receipt.get("receipt_id", "missing"),
        "recipient_value": "Turns the Gorilla replay receipt into a single launchpad handoff card with safe first-run commands, local artifact checks, and acceptance evidence instructions.",
        "first_run_steps": handoff_steps,
        "local_artifact_checks": receipt.get("expected_local_artifacts_after_replay", []),
        "acceptance_harness_command": "npm run rc:agentpress-gorilla-replay-to-launchpad-handoff --silent",
        "operator_next_steps": [
            "Open this card before running Gorilla replay commands.",
            "Run only steps marked safe_local_only=true in a private local checkout.",
            "Attach stdout/stderr and local artifact paths to the task proof bundle.",
            "Stop before git push, npm publish, deploy, outreach, wallet, payment, secret, or external-send action unless Jake explicitly approves.",
        ],
        "readiness_assertions": [
            "wave97 receipt is ok and blocker-free",
            "all replay commands are local-only and launchpad-safe",
            "local artifact checks are explicit",
            "public publish/push/deploy remains gated by Jake explicit approval",
        ],
        "public_publish_push_gate": "Jake explicit approval required; no public action performed.",
    }
    if launchpad_card["source_receipt_id"] == "missing":
        blockers.append("handoff_missing_source_receipt_id")
    if not launchpad_card["local_artifact_checks"]:
        blockers.append("handoff_missing_local_artifact_checks")
    return {
        "kind": "agentpress_gorilla_replay_to_launchpad_handoff",
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "ok" if not blockers else "blocked",
        "source_receipt": receipt_rel,
        "launchpad_handoff_card": launchpad_card,
        "public_actions_taken": [],
        "external_actions": [],
        "payment_actions_taken": [],
        "secret_material_included": False,
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "blockers": blockers,
    }


def markdown(doc: dict[str, Any]) -> str:
    card = doc["launchpad_handoff_card"]
    lines = [
        "# AgentPress Gorilla replay to launchpad handoff (wave98)",
        "",
        f"- Status: `{doc['status']}`",
        f"- Card ID: `{card['card_id']}`",
        f"- Source receipt ID: `{card.get('source_receipt_id')}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "- Payment actions taken: `[]`",
        "",
        "## Recipient value",
        "",
        card["recipient_value"],
        "",
        "## First-run launchpad steps",
    ]
    for row in card.get("first_run_steps", []):
        lines.append(f"- {row['step']}. `{row['command']}` — safe_local_only={row['safe_local_only']} — {row['first_run_instruction']}")
    lines.extend(["", "## Local artifact checks"])
    lines.extend([f"- `{path}`" for path in card.get("local_artifact_checks", [])] or ["- None"])
    lines.extend(["", "## Acceptance harness", "", f"`{card['acceptance_harness_command']}`", "", "## Safety gate", "", card["public_publish_push_gate"], "", "## Blockers"])
    lines.extend([f"- {b}" for b in doc.get("blockers", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, doc: dict[str, Any], out_rel: str, md_rel: str) -> None:
    (root / out_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / out_rel).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / md_rel).write_text(markdown(doc), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--receipt", default=DEFAULT_RECEIPT)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    doc = build_handoff(root, receipt_rel=args.receipt, include_pack=False)
    write_outputs(root, doc, args.out, args.markdown_out)
    if args.include_pack_check:
        doc = build_handoff(root, receipt_rel=args.receipt, include_pack=True)
        write_outputs(root, doc, args.out, args.markdown_out)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    return 0 if doc["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
