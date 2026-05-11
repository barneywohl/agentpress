#!/usr/bin/env python3
"""Build a local-only verifier packet for Gorilla launchpad operator acknowledgements."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_RUNBOOK = "agentpress/evidence/agentpress-gorilla-launchpad-acceptance-runbook-wave103.json"
DEFAULT_OUT = "agentpress/evidence/agentpress-gorilla-operator-acknowledgement-verifier-wave104.json"
DEFAULT_MD = "agentpress/evidence/agentpress-gorilla-operator-acknowledgement-verifier-wave104.md"
SCRIPT_PATH = "scripts/agentpress_gorilla_operator_acknowledgement_verifier.py"
TEST_PATH = "tests/test_agentpress_gorilla_operator_acknowledgement_verifier.py"
SCRIPT_NAME = "rc:agentpress-gorilla-operator-acknowledgement-verifier"
PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD, DEFAULT_RUNBOOK]
GENERATED = {DEFAULT_OUT, DEFAULT_MD}
PUBLIC_OR_EXTERNAL = re.compile(r"\b(push|publish|deploy|payment|wallet|external[-_ ]?send|outreach|email|curl\s+https?://|wget\s+https?://)\b|https?://", re.I)
SECRET_MARKERS = re.compile(r"(secret|token|password|api[_-]?key)", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # noqa: BLE001
        return None, f"json_error:{exc}"


def local_relative_path(value: str) -> bool:
    if not value or PUBLIC_OR_EXTERNAL.search(value) or SECRET_MARKERS.search(value):
        return False
    p = Path(value)
    return not p.is_absolute() and ".." not in p.parts


def safe_text(value: Any) -> bool:
    return not PUBLIC_OR_EXTERNAL.search(str(value)) and not SECRET_MARKERS.search(str(value))


def field_defaults(fields: list[dict[str, Any]]) -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    for field in fields:
        name = str(field.get("name", ""))
        typ = str(field.get("type", ""))
        if typ.startswith("array"):
            defaults[name] = []
        elif typ == "boolean":
            defaults[name] = False
        elif typ == "integer":
            defaults[name] = None
        else:
            defaults[name] = None
    return defaults


def example_acknowledgement(runbook: dict[str, Any]) -> dict[str, Any]:
    ack = field_defaults(runbook.get("operator_acknowledgement_fields", []))
    ack.update(
        {
            "operator_agent_id": "local-recipient-agent",
            "operator_acknowledged_first_command": True,
            "first_command_exit_code": 0,
            "first_command_stdout_tail": "local-only gorilla launchpad drill completed",
            "first_command_stderr_tail": "",
            "criteria_checked": list(runbook.get("acceptance_criteria", [])),
            "generated_local_artifacts": ["agentpress/evidence/local-recipient-acknowledgement.json"],
            "stop_reason_if_blocked": "",
            "operator_note": "sample local acknowledgement; no public action taken",
        }
    )
    return ack


def validate_acknowledgement(ack: dict[str, Any], runbook: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    fields = runbook.get("operator_acknowledgement_fields", [])
    required = [str(field.get("name")) for field in fields if field.get("required")]
    for name in required:
        if name not in ack or ack[name] in (None, "", []):
            blockers.append(f"ack_missing_required:{name}")
    if ack.get("operator_acknowledged_first_command") is not True:
        blockers.append("ack_first_command_not_acknowledged")
    if ack.get("first_command_exit_code") != 0:
        blockers.append("ack_first_command_exit_code_not_zero")
    criteria = set(runbook.get("acceptance_criteria", []))
    checked = set(ack.get("criteria_checked", [])) if isinstance(ack.get("criteria_checked"), list) else set()
    for criterion in sorted(criteria - checked):
        blockers.append(f"ack_criterion_unchecked:{criterion[:80]}")
    artifacts = ack.get("generated_local_artifacts", [])
    if not isinstance(artifacts, list) or not artifacts:
        blockers.append("ack_no_generated_local_artifacts")
    else:
        for artifact in artifacts:
            if not isinstance(artifact, str) or not local_relative_path(artifact):
                blockers.append(f"ack_artifact_not_local_relative:{artifact}")
    # Criteria and stop reasons intentionally mirror runbook safety language, which may
    # mention forbidden public actions as things to avoid. Only freeform operator text
    # fields and artifact paths are scanned for accidental URLs/secrets/public-action intent.
    for key in ["operator_agent_id", "first_command_stdout_tail", "first_command_stderr_tail", "operator_note"]:
        if key in ack and not safe_text(ack[key]):
            blockers.append(f"ack_value_not_local_safe:{key}")
    if blockers and not ack.get("stop_reason_if_blocked"):
        blockers.append("ack_blocked_without_stop_reason")
    return blockers


def package_check(root: Path) -> tuple[dict[str, Any], list[str]]:
    pkg, err = load_json(root / "package.json")
    if err or not isinstance(pkg, dict):
        return {"script": "", "required": []}, [f"package_json_{err}"]
    scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
    files = pkg.get("files") if isinstance(pkg.get("files"), list) else []
    blockers: list[str] = []
    if SCRIPT_NAME not in scripts:
        blockers.append(f"package_json_missing_script:{SCRIPT_NAME}")
    required = []
    for rel in PACKAGE_FILES:
        row = {"path": rel, "exists_local": (root / rel).exists(), "listed_in_package_files": rel in files}
        required.append(row)
        if rel not in GENERATED and not row["exists_local"]:
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


def build_verifier(root: Path, *, runbook_rel: str = DEFAULT_RUNBOOK, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    runbook, err = load_json(root / runbook_rel)
    if err or not isinstance(runbook, dict):
        runbook = {}
        blockers.append(f"runbook_{err}:{runbook_rel}")
    if runbook.get("status") != "ok":
        blockers.append("source_runbook_not_ok")
    if runbook.get("public_push_publish_deploy") is not False or runbook.get("jake_explicit_approval_required_for_public_actions") is not True:
        blockers.append("source_public_gate_not_preserved")
    if not local_relative_path(runbook_rel):
        blockers.append(f"runbook_path_not_local:{runbook_rel}")

    sample_ack = example_acknowledgement(runbook)
    sample_blockers = validate_acknowledgement(sample_ack, runbook)
    if sample_blockers:
        blockers.extend(f"sample_{item}" for item in sample_blockers)

    verifier_steps = [
        {"step": 1, "name": "load-runbook", "instruction": "Load the wave103 runbook and preserve its local-only safety boundary."},
        {"step": 2, "name": "validate-required-fields", "instruction": "Reject acknowledgements missing required operator fields."},
        {"step": 3, "name": "validate-first-command", "instruction": "Require operator_acknowledged_first_command=true and first_command_exit_code=0."},
        {"step": 4, "name": "validate-criteria-coverage", "instruction": "Require every runbook acceptance criterion in criteria_checked."},
        {"step": 5, "name": "validate-local-artifacts", "instruction": "Require generated artifacts to be relative local paths with no URL, secret marker, or parent traversal."},
    ]
    package, package_blockers = package_check(root)
    blockers.extend(package_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required:{row.get('path')}")

    return {
        "schema_version": "2026-05-11.agentpress-gorilla-operator-acknowledgement-verifier.v1",
        "generated_utc": utc_now(),
        "verifier_id": "wave104-gorilla-operator-acknowledgement-verifier",
        "status": "ok" if not blockers else "blocked",
        "source_inputs": [runbook_rel],
        "public_push_publish_deploy": False,
        "external_actions": [],
        "payment_actions_taken": [],
        "secret_material_included": False,
        "jake_explicit_approval_required_for_public_actions": True,
        "agent_facing_value": "A recipient agent can machine-check its Gorilla launchpad operator acknowledgement before handoff, catching missing criteria, unsafe artifacts, or accidental public-action text locally.",
        "verifier_steps": verifier_steps,
        "required_acknowledgement_fields": runbook.get("operator_acknowledgement_fields", []),
        "sample_operator_acknowledgement": sample_ack,
        "sample_validation_blockers": sample_blockers,
        "failure_stop_rules": [
            "Stop if any required acknowledgement field is missing.",
            "Stop if the first command was not acknowledged with exit code 0.",
            "Stop if any acceptance criterion is unchecked.",
            "Stop if any generated artifact path is absolute, remote, parent-traversing, or secret-labeled.",
            "Stop before any public push, publish, deploy, payment, external send, URL fetch, or secret request without Jake approval.",
        ],
        "handoff_ready_artifacts": [DEFAULT_OUT, DEFAULT_MD, runbook_rel],
        "package": package,
        "pack_check": pack,
        "blockers": blockers,
    }


def write_markdown(path: Path, data: dict[str, Any]) -> None:
    steps = "\n".join(f"{step['step']}. **{step['name']}** — {step['instruction']}" for step in data["verifier_steps"])
    fields = "\n".join(f"- `{field.get('name')}` ({field.get('type')}, required={field.get('required')})" for field in data["required_acknowledgement_fields"])
    stops = "\n".join(f"- {item}" for item in data["failure_stop_rules"])
    blockers = "\n".join(f"- {item}" for item in data["blockers"]) if data["blockers"] else "- none"
    artifacts = "\n".join(f"- `{item}`" for item in data["handoff_ready_artifacts"])
    path.write_text(
        "# AgentPress Gorilla operator acknowledgement verifier\n\n"
        f"- Status: `{data['status']}`\n"
        f"- Verifier: `{data['verifier_id']}`\n"
        f"- Public push/publish/deploy: `{data['public_push_publish_deploy']}`; Jake approval required: `{data['jake_explicit_approval_required_for_public_actions']}`\n\n"
        "## Verifier steps\n"
        f"{steps}\n\n"
        "## Required acknowledgement fields\n"
        f"{fields}\n\n"
        "## Failure-stop rules\n"
        f"{stops}\n\n"
        "## Handoff-ready artifacts\n"
        f"{artifacts}\n\n"
        "## Blockers\n"
        f"{blockers}\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    out = root / args.out if not Path(args.out).is_absolute() else Path(args.out)
    md = root / args.markdown_out if not Path(args.markdown_out).is_absolute() else Path(args.markdown_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    md.parent.mkdir(parents=True, exist_ok=True)
    data = build_verifier(root, include_pack=False)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(md, data)
    if args.include_pack_check:
        data = build_verifier(root, include_pack=True)
        out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_markdown(md, data)
    if args.json:
        print(json.dumps({"status": data["status"], "out": str(out), "markdown_out": str(md), "blockers": data["blockers"]}, sort_keys=True))
    return 0 if data["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
