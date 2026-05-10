#!/usr/bin/env python3
"""Build wave71 local-only operator capsule from wave70 replay matrix."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MATRIX = "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json"
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_replay_operator_capsule.py"
TEST_PATH = "tests/test_agent_facing_acceptance_replay_operator_capsule.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-replay-operator-capsule"
REQUIRED_LANES = [
    "glm_gorilla_bootstrap_conveyor",
    "launchpad",
    "comms_hub",
    "marketplace",
    "safety_guardrails",
    "acceptance_harness",
]
FORBIDDEN_FRAGMENTS = [
    "git push",
    "npm publish",
    "npm dist-tag",
    "wrangler pages deploy",
    "vercel --prod",
    "gh release",
    "sendgrid",
    "discord webhook",
    "slack api",
    "payment",
    "secret access",
]
PACKAGE_REQUIRED = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"json_error: {exc}"
    if not isinstance(data, dict):
        return None, "json_root_not_object"
    return data, None


def fragment_hits(values: list[str]) -> list[str]:
    text = "\n".join(values).lower()
    return sorted({frag for frag in FORBIDDEN_FRAGMENTS if frag in text})


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
    for rel in PACKAGE_REQUIRED:
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
        result.update({"stdout": proc.stdout, "stderr": proc.stderr})
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
    result["required_included"] = [{"path": rel, "included": rel in names} for rel in PACKAGE_REQUIRED]
    return result


def build_capsule(root: Path, *, include_pack: bool = False) -> dict[str, Any]:
    matrix, err = load_json(root / MATRIX)
    blockers: list[str] = []
    if err or matrix is None:
        matrix = {}
        blockers.append(f"wave70_matrix_{err}: {MATRIX}")
    elif matrix.get("status") != "ok":
        blockers.append(f"wave70_matrix_status_not_ok: {matrix.get('status')!r}")

    if matrix.get("public_actions_taken") not in ([], None):
        blockers.append("wave70_matrix_records_public_actions_taken")
    if matrix.get("external_actions") not in ([], None):
        blockers.append("wave70_matrix_records_external_actions")

    lanes = matrix.get("lanes", []) if isinstance(matrix.get("lanes"), list) else []
    lane_by_id = {lane.get("id"): lane for lane in lanes if isinstance(lane, dict)}
    summaries = []
    for lane_id in REQUIRED_LANES:
        lane = lane_by_id.get(lane_id)
        if not lane:
            blockers.append(f"missing_required_lane: {lane_id}")
            continue
        if lane.get("passed") is not True:
            blockers.append(f"lane_not_passed: {lane_id}")
        if lane.get("public_actions_taken") not in ([], None):
            blockers.append(f"lane_records_public_actions_taken: {lane_id}")
        if lane.get("external_actions") not in ([], None):
            blockers.append(f"lane_records_external_actions: {lane_id}")
        steps = [str(step) for step in lane.get("replay_steps", [])]
        hits = fragment_hits(steps)
        if hits:
            blockers.append(f"lane_contains_forbidden_fragments: {lane_id}: {hits}")
        summaries.append({
            "id": lane_id,
            "label": lane.get("label"),
            "passed": lane.get("passed") is True,
            "required_sources": lane.get("required_sources", []),
            "replay_step_count": len(steps),
        })

    commands = matrix.get("exact_local_verification_commands", [])
    if not isinstance(commands, list) or not commands:
        blockers.append("wave70_matrix_missing_exact_local_verification_commands")
        commands = []

    package, package_blockers = package_expectations(root)
    blockers.extend(package_blockers)

    next_agent_instructions = [
        "Run npm run rc:agent-facing-acceptance-harness-replay-matrix --silent and inspect the wave70 matrix.",
        "Run npm run rc:agent-facing-acceptance-replay-operator-capsule --silent and inspect this capsule.",
        "Confirm all six lanes are passed and public_actions_taken/external_actions are empty before any operator handoff.",
        "Do not publish, push, deploy, send outreach, take payment actions, or read secrets until Jake explicitly approves public cutover.",
    ]

    pack = run_pack(root) if include_pack else None
    if pack:
        if pack.get("returncode") != 0 or not pack.get("json_parseable"):
            blockers.append("npm_pack_dry_run_failed")
        for item in pack.get("required_included", []):
            if not item.get("included"):
                blockers.append(f"npm_pack_missing_required: {item.get('path')}")

    return {
        "kind": "agentpress_agent_facing_acceptance_replay_operator_capsule",
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "ok" if not blockers else "blocked",
        "local_only": True,
        "source_matrix": MATRIX,
        "required_lane_ids": REQUIRED_LANES,
        "lane_summaries": summaries,
        "lane_count": len(summaries),
        "exact_local_verification_commands": commands + [
            "npm run rc:agent-facing-acceptance-replay-operator-capsule --silent",
            "python3 -m py_compile scripts/agent_facing_acceptance_replay_operator_capsule.py",
            "pytest -q tests/test_agent_facing_acceptance_replay_operator_capsule.py",
            "python3 -m json.tool agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json",
            "npm pack --dry-run --json",
        ],
        "next_agent_copy_paste_instructions": next_agent_instructions,
        "public_action_gate": {
            "state": "closed_until_jake_explicit_approval",
            "public_publish_push_deploy_outreach_payment_secret_access": "not_executed",
            "allowed_now": "local rehearsal and evidence inspection only",
        },
        "public_actions_taken": [],
        "external_actions": [],
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "blockers": blockers,
    }


def write_markdown(capsule: dict[str, Any], path: Path) -> None:
    lines = [
        "# AgentPress agent-facing acceptance replay operator capsule (wave71)",
        "",
        f"- Status: `{capsule['status']}`",
        f"- Generated at: `{capsule['generated_at']}`",
        "- Public publish/push/deploy/outreach/payment/secret access: `not executed`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Lane summary",
    ]
    for lane in capsule["lane_summaries"]:
        lines.extend([
            f"- `{lane['id']}` ({lane.get('label')}): passed=`{lane['passed']}`, sources=`{', '.join(lane.get('required_sources', []))}`",
        ])
    lines.extend(["", "## Next-agent copy/paste instructions"])
    for idx, instruction in enumerate(capsule["next_agent_copy_paste_instructions"], start=1):
        lines.append(f"{idx}. {instruction}")
    lines.extend(["", "## Verification commands"])
    for command in capsule["exact_local_verification_commands"]:
        lines.append(f"- `{command}`")
    lines.extend(["", "## Blockers"])
    if capsule["blockers"]:
        lines.extend(f"- {blocker}" for blocker in capsule["blockers"])
    else:
        lines.append("- None")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    # Two-pass write: generated evidence must exist before npm pack can verify inclusion.
    capsule = build_capsule(root, include_pack=False)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(capsule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(capsule, root / args.markdown_out)
    if args.include_pack_check:
        capsule = build_capsule(root, include_pack=True)
        out.write_text(json.dumps(capsule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_markdown(capsule, root / args.markdown_out)
    if args.json:
        print(json.dumps(capsule, indent=2, sort_keys=True))
    return 0 if capsule["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
