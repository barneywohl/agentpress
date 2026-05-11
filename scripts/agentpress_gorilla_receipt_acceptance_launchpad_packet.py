#!/usr/bin/env python3
"""Build a local-only launchpad acceptance packet from Gorilla receipt verification."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_VERIFIER = "agentpress/evidence/agentpress-gorilla-evidence-receipt-verifier-wave101.json"
DEFAULT_CAPSULE = "agentpress/evidence/agentpress-gorilla-drill-evidence-capsule-wave100.json"
DEFAULT_DRILL = "agentpress/evidence/agentpress-gorilla-launchpad-first-run-drill-wave99.json"
DEFAULT_OUT = "agentpress/evidence/agentpress-gorilla-receipt-acceptance-launchpad-packet-wave102.json"
DEFAULT_MD = "agentpress/evidence/agentpress-gorilla-receipt-acceptance-launchpad-packet-wave102.md"
SCRIPT_PATH = "scripts/agentpress_gorilla_receipt_acceptance_launchpad_packet.py"
TEST_PATH = "tests/test_agentpress_gorilla_receipt_acceptance_launchpad_packet.py"
SCRIPT_NAME = "rc:agentpress-gorilla-receipt-acceptance-launchpad-packet"
PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD, DEFAULT_VERIFIER, DEFAULT_CAPSULE, DEFAULT_DRILL]
GENERATED = {DEFAULT_OUT, DEFAULT_MD}
PUBLIC_ACTIONS = re.compile(r"\b(push|publish|deploy|payment|wallet|external[-_ ]?send|outreach|email|curl\s+https?://|wget\s+https?://)\b", re.I)
SECRET_OR_EXTERNAL = re.compile(r"(https?://|secret|token|password|api[_-]?key)", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # noqa: BLE001
        return None, f"json_error:{exc}"


def local_path_ok(path: str) -> bool:
    if not path or SECRET_OR_EXTERNAL.search(path):
        return False
    p = Path(path)
    return not p.is_absolute() and ".." not in p.parts


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


def first_safe_command(drill: dict[str, Any]) -> str:
    for step in drill.get("first_run_drill", {}).get("steps", []):
        if not isinstance(step, dict):
            continue
        cmd = str(step.get("command", "")).strip()
        if step.get("safe_local_only") is True and cmd and not SECRET_OR_EXTERNAL.search(cmd) and not PUBLIC_ACTIONS.search(cmd):
            return cmd
    return "echo 'AgentPress Gorilla receipt acceptance launchpad packet: local-only first command'"


def build_acceptance_packet(root: Path, *, verifier_rel: str = DEFAULT_VERIFIER, capsule_rel: str = DEFAULT_CAPSULE, drill_rel: str = DEFAULT_DRILL, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    verifier, verifier_err = load_json(root / verifier_rel)
    capsule, capsule_err = load_json(root / capsule_rel)
    drill, drill_err = load_json(root / drill_rel)
    if verifier_err or not isinstance(verifier, dict):
        verifier = {}
        blockers.append(f"verifier_{verifier_err}:{verifier_rel}")
    if capsule_err or not isinstance(capsule, dict):
        capsule = {}
        blockers.append(f"capsule_{capsule_err}:{capsule_rel}")
    if drill_err or not isinstance(drill, dict):
        drill = {}
        blockers.append(f"drill_{drill_err}:{drill_rel}")

    if verifier.get("status") != "ok" or verifier.get("acceptance_summary", {}).get("all_steps_verified") is not True:
        blockers.append("source_verifier_not_fully_accepted")
    if verifier.get("public_push_publish_deploy") is not False or verifier.get("jake_explicit_approval_required_for_public_actions") is not True:
        blockers.append("source_public_gate_not_preserved")
    if capsule.get("status") != "ok" or drill.get("status") != "ok":
        blockers.append("source_capsule_or_drill_not_ok")

    cmd = first_safe_command(drill)
    if PUBLIC_ACTIONS.search(cmd) or SECRET_OR_EXTERNAL.search(cmd):
        blockers.append("first_command_not_local_safe")

    verified_steps = verifier.get("verified_steps") if isinstance(verifier.get("verified_steps"), list) else []
    criteria = [
        "source verifier status is ok",
        "all Gorilla drill step receipts are accepted",
        "receipt command hashes match the wave100 capsule",
        "first command is local-only and does not request secrets",
        "stop before push/publish/deploy/payment/external-send unless Jake explicitly approves",
    ]
    failure_stops = [
        "any nonzero command exit",
        "missing or nonlocal generated artifact path",
        "command hash mismatch versus capsule",
        "public action, payment, external send, URL fetch, or secret/token request",
        "package registry proof missing script/test/evidence/source files",
    ]
    local_artifacts = [DEFAULT_OUT, DEFAULT_MD, verifier_rel, capsule_rel, drill_rel]
    for artifact in local_artifacts:
        if not local_path_ok(artifact):
            blockers.append(f"artifact_path_not_local:{artifact}")

    package, package_blockers = package_check(root)
    blockers.extend(package_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required:{row.get('path')}")

    packet = {
        "schema_version": "2026-05-11.agentpress-gorilla-receipt-acceptance-launchpad-packet.v1",
        "generated_utc": utc_now(),
        "packet_id": "wave102-gorilla-receipt-acceptance-launchpad-packet",
        "status": "ok" if not blockers else "blocked",
        "source_inputs": [verifier_rel, capsule_rel, drill_rel],
        "public_push_publish_deploy": False,
        "external_actions": [],
        "payment_actions_taken": [],
        "secret_material_included": False,
        "jake_explicit_approval_required_for_public_actions": True,
        "agent_facing_value": "A recipient agent now gets one safe first command plus explicit receipt-acceptance criteria and failure-stop rules before accepting the Gorilla launchpad handoff.",
        "launchpad": {
            "first_command": cmd,
            "first_command_expected_result": "stdout captured locally with exit_code=0; no public action, external send, payment, URL fetch, or secret request",
            "acceptance_criteria": criteria,
            "failure_stop_rules": failure_stops,
            "recipient_proof_fields": ["command", "exit_code", "stdout_tail", "stderr_tail", "generated_local_artifact_paths", "operator_note"],
            "local_artifacts_to_attach": local_artifacts,
        },
        "receipt_acceptance": {
            "accepted_receipts": verifier.get("acceptance_summary", {}).get("accepted_receipts", 0),
            "total_receipts": verifier.get("acceptance_summary", {}).get("total_receipts", 0),
            "all_steps_verified": verifier.get("acceptance_summary", {}).get("all_steps_verified") is True,
            "verified_step_count": len(verified_steps),
        },
        "package": package,
        "pack_check": pack,
        "blockers": blockers,
    }
    return packet


def write_markdown(path: Path, data: dict[str, Any]) -> None:
    launch = data["launchpad"]
    criteria = "\n".join(f"- {item}" for item in launch["acceptance_criteria"])
    stops = "\n".join(f"- {item}" for item in launch["failure_stop_rules"])
    artifacts = "\n".join(f"- `{item}`" for item in launch["local_artifacts_to_attach"])
    path.write_text(
        "# AgentPress Gorilla receipt acceptance launchpad packet\n\n"
        f"- Status: `{data['status']}`\n"
        f"- Packet: `{data['packet_id']}`\n"
        f"- Public publish/push/deploy: `{data['public_push_publish_deploy']}`; Jake approval required: `{data['jake_explicit_approval_required_for_public_actions']}`\n"
        f"- First command: `{launch['first_command']}`\n\n"
        "## Receipt acceptance criteria\n"
        f"{criteria}\n\n"
        "## Failure-stop rules\n"
        f"{stops}\n\n"
        "## Local artifacts to attach\n"
        f"{artifacts}\n\n"
        "## Blockers\n"
        + ("\n".join(f"- {b}" for b in data["blockers"]) if data["blockers"] else "- none")
        + "\n",
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
    data = build_acceptance_packet(root, include_pack=args.include_pack_check)
    out = root / args.out if not Path(args.out).is_absolute() else Path(args.out)
    md = root / args.markdown_out if not Path(args.markdown_out).is_absolute() else Path(args.markdown_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    md.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(md, data)
    if args.json:
        print(json.dumps({"status": data["status"], "out": str(out), "markdown_out": str(md), "blockers": data["blockers"]}, sort_keys=True))
    return 0 if data["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
