#!/usr/bin/env python3
"""Build the wave70 local-only agent-facing acceptance harness replay matrix.

This script consumes prior RC/adoption evidence and emits a reviewable matrix that
proves the agent-facing lanes can be rehearsed end-to-end without public actions.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUT = "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json"
DEFAULT_MD = "agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.md"
SCRIPT_PATH = "scripts/agent_facing_acceptance_harness_replay_matrix.py"
TEST_PATH = "tests/test_agent_facing_acceptance_harness_replay_matrix.py"

SOURCES = {
    "post_approval_cutover_rehearsal": "agentpress/evidence/rc-adoption-post-approval-cutover-rehearsal-wave69.json",
    "final_acceptance_snapshot": "agentpress/evidence/rc-final-acceptance-snapshot-wave49.json",
    "public_action_guardrail_audit": "agentpress/evidence/rc-public-action-guardrail-audit-wave52.json",
    "launch_signal_simulator": "agentpress/evidence/rc-launch-signal-simulator-wave55.json",
    "route_run_receipt_collector": "agentpress/evidence/rc-adoption-route-run-receipt-collector-wave65.json",
}

LANES = [
    {
        "id": "glm_gorilla_bootstrap_conveyor",
        "label": "GLM/gorilla bootstrap conveyor",
        "sources": ["final_acceptance_snapshot", "route_run_receipt_collector"],
        "replay_steps": [
            "Load final acceptance snapshot and route-run receipt collector evidence.",
            "Confirm agent-facing next step exists and is local-only.",
            "Rehearse bootstrap handoff as data only; do not execute public command fragments.",
        ],
    },
    {
        "id": "launchpad",
        "label": "Launchpad",
        "sources": ["launch_signal_simulator", "final_acceptance_snapshot"],
        "replay_steps": [
            "Load simulated launch signals and final acceptance checklist.",
            "Confirm launch readiness remains simulated/local until Jake approval.",
            "Replay operator capture checklist as non-sending local review steps.",
        ],
    },
    {
        "id": "comms_hub",
        "label": "Comms hub",
        "sources": ["route_run_receipt_collector", "public_action_guardrail_audit"],
        "replay_steps": [
            "Load route-run receipt and guardrail audit.",
            "Confirm any send/outreach/push category remains gated.",
            "Produce only local copy/paste rehearsal data, with no outbound message.",
        ],
    },
    {
        "id": "marketplace",
        "label": "Marketplace",
        "sources": ["route_run_receipt_collector", "final_acceptance_snapshot"],
        "replay_steps": [
            "Load route claim/receipt path and package inclusion snapshot.",
            "Confirm package/evidence handoff can be inspected by an agent.",
            "Rehearse marketplace adoption route locally without publish/latest promotion.",
        ],
    },
    {
        "id": "safety_guardrails",
        "label": "Safety guardrails",
        "sources": ["public_action_guardrail_audit", "post_approval_cutover_rehearsal"],
        "replay_steps": [
            "Load public action audit and post-approval rehearsal evidence.",
            "Confirm public_publish_push gate is closed in rehearsal outputs.",
            "Scan replay steps for forbidden public command fragments and keep execution false.",
        ],
    },
    {
        "id": "acceptance_harness",
        "label": "Acceptance harness",
        "sources": ["final_acceptance_snapshot", "post_approval_cutover_rehearsal"],
        "replay_steps": [
            "Load final acceptance and wave69 rehearsal evidence.",
            "Confirm status ok/blockers [] across required sources.",
            "Emit this matrix JSON/Markdown as the next agent-facing acceptance harness artifact.",
        ],
    },
]

FORBIDDEN_FRAGMENTS = [
    "git push",
    "npm publish",
    "npm dist-tag",
    "wrangler pages deploy",
    "vercel --prod",
    "gh release",
    "curl http",
    "curl -x post",
    "sendgrid",
    "slack api",
    "discord webhook",
    "nexio",
]

PACKAGE_REQUIRED = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"json_error: {exc}"
    if not isinstance(payload, dict):
        return None, "json_root_not_object"
    return payload, None


def source_status(root: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    records: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    for key, rel in SOURCES.items():
        payload, error = load_json(root / rel)
        record = {
            "key": key,
            "path": rel,
            "exists": error is None,
            "error": error,
            "kind": payload.get("kind") if payload else None,
            "status": payload.get("status") if payload else None,
            "blockers": payload.get("blockers") if payload else None,
            "local_only": payload.get("local_only") if payload else None,
            "public_actions_taken": payload.get("public_actions_taken") if payload else None,
            "external_actions": payload.get("external_actions") if payload else None,
        }
        if error:
            blockers.append(f"source_{key}_{error}: {rel}")
        elif payload:
            if payload.get("status") != "ok":
                blockers.append(f"source_{key}_status_not_ok: {payload.get('status')!r}")
            child_blockers = payload.get("blockers", [])
            if not isinstance(child_blockers, list):
                blockers.append(f"source_{key}_blockers_not_list")
            elif child_blockers:
                blockers.append(f"source_{key}_blockers_not_empty: {child_blockers!r}")
            if payload.get("local_only") is not True:
                blockers.append(f"source_{key}_not_local_only")
            if payload.get("public_actions_taken") not in ([], None):
                blockers.append(f"source_{key}_records_public_actions_taken")
            if payload.get("external_actions") not in ([], None):
                blockers.append(f"source_{key}_records_external_actions")
        records[key] = record
    return records, blockers


def fragment_hits(texts: list[str]) -> list[str]:
    joined = "\n".join(texts).lower()
    return sorted({frag for frag in FORBIDDEN_FRAGMENTS if frag in joined})


def build_lanes(sources: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    lanes: list[dict[str, Any]] = []
    blockers: list[str] = []
    seen_ids: set[str] = set()
    for lane in LANES:
        lane_sources = lane["sources"]
        missing_sources = [key for key in lane_sources if key not in sources or not sources[key]["exists"]]
        source_problems = [key for key in lane_sources if key in sources and sources[key].get("status") != "ok"]
        hits = fragment_hits(lane["replay_steps"])
        passed = not missing_sources and not source_problems and not hits
        if lane["id"] in seen_ids:
            blockers.append(f"duplicate_lane_id: {lane['id']}")
        seen_ids.add(lane["id"])
        if missing_sources:
            blockers.append(f"lane_{lane['id']}_missing_sources: {missing_sources}")
        if source_problems:
            blockers.append(f"lane_{lane['id']}_source_status_not_ok: {source_problems}")
        if hits:
            blockers.append(f"lane_{lane['id']}_contains_forbidden_fragments: {hits}")
        lanes.append(
            {
                "id": lane["id"],
                "label": lane["label"],
                "required_sources": lane_sources,
                "replay_steps": lane["replay_steps"],
                "missing_sources": missing_sources,
                "source_status_problems": source_problems,
                "forbidden_fragments_seen": hits,
                "commands_executed": False,
                "public_actions_taken": [],
                "external_actions": [],
                "passed": passed,
            }
        )
    required = {lane["id"] for lane in LANES}
    covered = {lane["id"] for lane in lanes}
    missing_lanes = sorted(required - covered)
    if missing_lanes:
        blockers.append(f"missing_required_lanes: {missing_lanes}")
    return lanes, blockers


def inspect_package_json(root: Path) -> tuple[dict[str, Any], list[str]]:
    payload, error = load_json(root / "package.json")
    if error or payload is None:
        return {"script": "", "required": []}, [f"package_json_{error}"]
    scripts = payload.get("scripts") if isinstance(payload.get("scripts"), dict) else {}
    files = payload.get("files") if isinstance(payload.get("files"), list) else []
    script = scripts.get("rc:agent-facing-acceptance-harness-replay-matrix", "")
    blockers: list[str] = []
    if not script:
        blockers.append("package_json_missing_script_rc_agent_facing_acceptance_harness_replay_matrix")
    required = []
    generated_outputs = {DEFAULT_OUT, DEFAULT_MD}
    for rel in PACKAGE_REQUIRED:
        item = {"path": rel, "exists_local": (root / rel).exists(), "listed_in_package_files": rel in files}
        required.append(item)
        # DEFAULT_OUT/DEFAULT_MD are created by this command, so they may be absent
        # during the first pre-write package.json inspection. npm pack inclusion is
        # checked after generation by the npm script's second run / --include-pack-check.
        if not item["exists_local"] and rel not in generated_outputs:
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


def build_matrix(root: Path, *, include_pack: bool = False) -> dict[str, Any]:
    sources, blockers = source_status(root)
    lanes, lane_blockers = build_lanes(sources)
    blockers.extend(lane_blockers)
    package, package_blockers = inspect_package_json(root)
    blockers.extend(package_blockers)
    pack = run_pack(root) if include_pack else None
    if pack is not None:
        if pack.get("returncode") != 0:
            blockers.append("npm_pack_dry_run_failed")
        if not pack.get("json_parseable"):
            blockers.append("npm_pack_dry_run_json_not_parseable")
        for item in pack.get("required_included", []):
            if not item.get("included"):
                blockers.append(f"npm_pack_missing_required: {item.get('path')}")
    status = "ok" if not blockers else "blocked"
    return {
        "kind": "agentpress_agent_facing_acceptance_harness_replay_matrix",
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": status,
        "blockers": blockers,
        "local_only": True,
        "public_actions_taken": [],
        "external_actions": [],
        "source_evidence": sources,
        "lanes": lanes,
        "coverage": {
            "required_lane_ids": [lane["id"] for lane in LANES],
            "covered_lane_ids": [lane["id"] for lane in lanes if lane["passed"]],
            "all_required_lanes_present": all(lane["passed"] for lane in lanes),
        },
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "exact_local_verification_commands": [
            "npm run rc:agent-facing-acceptance-harness-replay-matrix --silent",
            "python3 -m py_compile scripts/agent_facing_acceptance_harness_replay_matrix.py",
            "pytest -q tests/test_agent_facing_acceptance_harness_replay_matrix.py",
            "python3 -m json.tool agentpress/evidence/agent-facing-acceptance-harness-replay-matrix-wave70.json",
            "npm pack --dry-run --json",
        ],
    }


def render_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# AgentPress agent-facing acceptance harness replay matrix (wave70)",
        "",
        f"- Status: `{data['status']}`",
        f"- Generated at: `{data['generated_at']}`",
        "- Public publish/push/deploy/outreach/payment/secret access: `not executed`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "",
        "## Lanes",
    ]
    for lane in data["lanes"]:
        lines.extend([
            "",
            f"### {lane['label']} (`{lane['id']}`)",
            f"- Passed: `{lane['passed']}`",
            f"- Required sources: `{', '.join(lane['required_sources'])}`",
            "- Replay steps:",
        ])
        lines.extend([f"  {idx}. {step}" for idx, step in enumerate(lane["replay_steps"], 1)])
    lines.extend(["", "## Blockers"])
    if data["blockers"]:
        lines.extend([f"- `{blocker}`" for blocker in data["blockers"]])
    else:
        lines.append("- None")
    lines.extend(["", "## Verification commands"])
    lines.extend([f"- `{cmd}`" for cmd in data["exact_local_verification_commands"]])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    data = build_matrix(root, include_pack=args.include_pack_check)
    out = root / args.out
    md = root / args.markdown_out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md.write_text(render_markdown(data), encoding="utf-8")
    if args.json:
        print(json.dumps({"status": data["status"], "out": args.out, "markdown_out": args.markdown_out, "blockers": data["blockers"]}, indent=2, sort_keys=True))
    return 0 if data["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
