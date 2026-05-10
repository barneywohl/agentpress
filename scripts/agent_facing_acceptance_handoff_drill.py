#!/usr/bin/env python3
"""Build wave72 local-only next-agent handoff drill from wave71 operator capsule."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CAPSULE = "agentpress/evidence/agent-facing-acceptance-replay-operator-capsule-wave71.json"
DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_handoff_drill.py"
TEST_PATH = "tests/test_agent_facing_acceptance_handoff_drill.py"
SCRIPT_NAME = "rc:agent-facing-acceptance-handoff-drill"
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


def readiness_id(capsule: dict[str, Any], commands: list[str], generated_at: str) -> str:
    payload = json.dumps(
        {
            "capsule_kind": capsule.get("kind"),
            "capsule_generated_at": capsule.get("generated_at"),
            "lane_ids": [lane.get("id") for lane in capsule.get("lane_summaries", []) if isinstance(lane, dict)],
            "commands": commands,
            "generated_at": generated_at,
        },
        sort_keys=True,
    ).encode("utf-8")
    return "wave72-readiness-" + hashlib.sha256(payload).hexdigest()[:16]


def build_drill(root: Path, *, include_pack: bool = False) -> dict[str, Any]:
    capsule, err = load_json(root / CAPSULE)
    blockers: list[str] = []
    generated_at = utc_now()
    if err or capsule is None:
        capsule = {}
        blockers.append(f"wave71_capsule_{err}: {CAPSULE}")
    else:
        if capsule.get("status") != "ok":
            blockers.append(f"wave71_capsule_status_not_ok: {capsule.get('status')!r}")
        if capsule.get("blockers") not in ([], None):
            blockers.append("wave71_capsule_has_blockers")
        if capsule.get("public_actions_taken") not in ([], None):
            blockers.append("wave71_capsule_records_public_actions_taken")
        if capsule.get("external_actions") not in ([], None):
            blockers.append("wave71_capsule_records_external_actions")

    lanes = capsule.get("lane_summaries", []) if isinstance(capsule.get("lane_summaries"), list) else []
    lane_by_id = {lane.get("id"): lane for lane in lanes if isinstance(lane, dict)}
    replayed_lanes = []
    for lane_id in REQUIRED_LANES:
        lane = lane_by_id.get(lane_id)
        if not lane:
            blockers.append(f"missing_required_lane_summary: {lane_id}")
            continue
        if lane.get("passed") is not True:
            blockers.append(f"lane_summary_not_passed: {lane_id}")
        if not lane.get("label"):
            blockers.append(f"lane_summary_missing_label: {lane_id}")
        if not lane.get("required_sources"):
            blockers.append(f"lane_summary_missing_required_sources: {lane_id}")
        replayed_lanes.append(
            {
                "id": lane_id,
                "label": lane.get("label"),
                "passed": lane.get("passed") is True,
                "required_sources": lane.get("required_sources", []),
                "fresh_agent_understanding": "lane is locally replayable from prior evidence; no public action required",
            }
        )

    commands = capsule.get("exact_local_verification_commands", [])
    if not isinstance(commands, list) or not commands:
        blockers.append("wave71_capsule_missing_exact_local_verification_commands")
        commands = []
    commands = [str(command) for command in commands]
    # Only executable/local verification commands are scanned for forbidden action fragments.
    # Wave71's prose correctly says "do not ... take payment actions"; that warning should not block the drill.
    hits = fragment_hits(commands)
    if hits:
        blockers.append(f"wave71_capsule_contains_forbidden_fragments: {hits}")

    local_commands = commands + [
        "npm run rc:agent-facing-acceptance-handoff-drill --silent",
        "python3 -m py_compile scripts/agent_facing_acceptance_handoff_drill.py",
        "pytest -q tests/test_agent_facing_acceptance_handoff_drill.py",
        "python3 -m json.tool agentpress/evidence/agent-facing-acceptance-handoff-drill-wave72.json",
        "npm pack --dry-run --json",
    ]
    receipt = {
        "receipt_id": readiness_id(capsule, local_commands, generated_at),
        "fresh_agent_role": "next_agent_acceptance_replay_operator",
        "source_capsule": CAPSULE,
        "understood_lane_count": len(replayed_lanes),
        "required_lane_count": len(REQUIRED_LANES),
        "all_required_lanes_understood": len(replayed_lanes) == len(REQUIRED_LANES) and not any(not lane["passed"] for lane in replayed_lanes),
        "exact_local_commands": local_commands,
        "public_action_gate_state": "closed_until_jake_explicit_approval",
        "signed_local_only_statement": "I can replay and explain all six acceptance lanes locally; I will not publish, push, deploy, send outreach, take payment action, or access secrets without explicit Jake approval.",
    }
    if not receipt["all_required_lanes_understood"]:
        blockers.append("readiness_receipt_not_all_required_lanes_understood")

    package, package_blockers = package_expectations(root)
    blockers.extend(package_blockers)

    pack = run_pack(root) if include_pack else None
    if pack:
        if pack.get("returncode") != 0 or not pack.get("json_parseable"):
            blockers.append("npm_pack_dry_run_failed")
        for item in pack.get("required_included", []):
            if not item.get("included"):
                blockers.append(f"npm_pack_missing_required: {item.get('path')}")

    return {
        "kind": "agentpress_agent_facing_acceptance_handoff_drill",
        "schema_version": 1,
        "generated_at": generated_at,
        "status": "ok" if not blockers else "blocked",
        "local_only": True,
        "source_capsule": CAPSULE,
        "required_lane_ids": REQUIRED_LANES,
        "replayed_lane_summaries": replayed_lanes,
        "readiness_receipt": receipt,
        "public_action_gate": {
            "state": "closed_until_jake_explicit_approval",
            "public_publish_push_deploy_outreach_payment_secret_access": "not_executed",
            "allowed_now": "local drill, evidence inspection, and package dry-run only",
        },
        "public_actions_taken": [],
        "external_actions": [],
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "blockers": blockers,
    }


def write_markdown(drill: dict[str, Any], path: Path) -> None:
    receipt = drill["readiness_receipt"]
    lines = [
        "# AgentPress agent-facing acceptance handoff drill (wave72)",
        "",
        f"- Status: `{drill['status']}`",
        f"- Generated at: `{drill['generated_at']}`",
        f"- Readiness receipt: `{receipt['receipt_id']}`",
        "- Public publish/push/deploy/outreach/payment/secret access: `not executed`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Fresh-agent lane understanding",
    ]
    for lane in drill["replayed_lane_summaries"]:
        lines.append(f"- `{lane['id']}` ({lane.get('label')}): passed=`{lane['passed']}`, sources=`{', '.join(lane.get('required_sources', []))}`")
    lines.extend(["", "## Readiness receipt local commands"])
    for command in receipt["exact_local_commands"]:
        lines.append(f"- `{command}`")
    lines.extend(["", "## Signed local-only statement", "", receipt["signed_local_only_statement"], "", "## Blockers"])
    if drill["blockers"]:
        lines.extend(f"- {blocker}" for blocker in drill["blockers"])
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
    drill = build_drill(root, include_pack=False)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(drill, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(drill, root / args.markdown_out)
    if args.include_pack_check:
        drill = build_drill(root, include_pack=True)
        out.write_text(json.dumps(drill, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_markdown(drill, root / args.markdown_out)
    if args.json:
        print(json.dumps(drill, indent=2, sort_keys=True))
    return 0 if drill["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
