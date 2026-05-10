#!/usr/bin/env python3
"""Build a local-only acceptance harness from the GLM Gorilla bootstrap conveyor manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = "agentpress/gorilla/glm-bootstrap-conveyor-wave87.json"
DEFAULT_OUT = "agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96.json"
DEFAULT_MD = "agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96.md"
DEFAULT_REPLAY = "agentpress/evidence/agentpress-gorilla-manifest-acceptance-harness-wave96-replay.sh"
SCRIPT_PATH = "scripts/agentpress_gorilla_manifest_acceptance_harness.py"
TEST_PATH = "tests/test_agentpress_gorilla_manifest_acceptance_harness.py"
SCRIPT_NAME = "rc:agentpress-gorilla-manifest-acceptance-harness"
PACKAGE_FILES = [SCRIPT_PATH, TEST_PATH, DEFAULT_OUT, DEFAULT_MD, DEFAULT_REPLAY, DEFAULT_MANIFEST]
GENERATED_ARTIFACTS = {DEFAULT_OUT, DEFAULT_MD, DEFAULT_REPLAY}
LOCAL_PREFIXES = ("python3 scripts/agentpress.py ", "npm run ", "node bin/agentpress.js ")
FORBIDDEN_RE = re.compile(
    r"\b(git\s+push|npm\s+publish|deploy|payment|wallet|secret|token|outreach|email|sendgrid|external-message|external\s+message|curl\s+http|wget\s+http|sudo|rm\s+-rf)\b",
    re.I,
)


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
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    proc = subprocess.run(
        ["npm", "pack", "--dry-run", "--json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )
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


def normalize_manifest_steps(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    blockers: list[str] = []
    steps: list[dict[str, Any]] = []
    raw_steps = manifest.get("bootstrap_steps") if isinstance(manifest.get("bootstrap_steps"), list) else []
    if not raw_steps:
        blockers.append("manifest_missing_bootstrap_steps")
    for idx, row in enumerate(raw_steps, start=1):
        if not isinstance(row, dict):
            blockers.append(f"manifest_step_not_object:{idx}")
            continue
        command = str(row.get("command", ""))
        has_command = bool(command.strip())
        safe = command_is_local_only(command) if has_command else True
        if has_command and not safe:
            blockers.append(f"manifest_step_unsafe_or_nonlocal:{idx}")
        steps.append(
            {
                "step": idx,
                "name": row.get("name", f"step_{idx}"),
                "command": command if has_command else None,
                "execution_mode": "manual-local-only" if has_command else "inspection-only",
                "safe_local_only": safe,
                "acceptance_observation": "command-ready" if has_command and safe else ("inspection-ready" if not has_command else "blocked"),
            }
        )
    return steps, blockers


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if manifest.get("status") not in {"ready", "ok"}:
        blockers.append("manifest_status_not_ready")
    first = str(manifest.get("first_useful_command", ""))
    proof = str(manifest.get("proof_command", ""))
    if not command_is_local_only(first):
        blockers.append("manifest_first_useful_command_unsafe_or_missing")
    if not command_is_local_only(proof):
        blockers.append("manifest_proof_command_unsafe_or_missing")
    safety = manifest.get("safety") if isinstance(manifest.get("safety"), dict) else {}
    expected_false = ["external_writes", "payments_attempted", "public_push_publish_deploy"]
    for key in expected_false:
        if safety.get(key) is not False:
            blockers.append(f"manifest_safety_not_false:{key}")
    if safety.get("requires_human_approval_before_external_action") is not True:
        blockers.append("manifest_missing_human_approval_gate")
    return blockers


def build_harness(root: Path, *, manifest_rel: str = DEFAULT_MANIFEST, include_pack: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    manifest, err = load_json(root / manifest_rel)
    if err or manifest is None:
        manifest = {}
        blockers.append(f"manifest_{err}:{manifest_rel}")
    else:
        blockers.extend(validate_manifest(manifest))
    steps, step_blockers = normalize_manifest_steps(manifest)
    blockers.extend(step_blockers)
    package, pkg_blockers = package_expectations(root)
    blockers.extend(pkg_blockers)
    pack = run_pack(root) if include_pack else {"skipped": True}
    if include_pack:
        if pack.get("returncode") != 0 or pack.get("json_parseable") is not True:
            blockers.append("npm_pack_dry_run_failed")
        for row in pack.get("required_included", []):
            if not row.get("included"):
                blockers.append(f"npm_pack_missing_required:{row.get('path')}")
    manifest_hash = sha256_file(root / manifest_rel) if (root / manifest_rel).exists() else "missing"
    harness = {
        "harness_id": "wave96-gorilla-manifest-acceptance-" + manifest_hash[:12],
        "source_manifest": manifest_rel,
        "source_manifest_sha256": manifest_hash,
        "painpoint_solved": "Turns the Gorilla bootstrap conveyor manifest into a single recipient-facing local acceptance harness with exact commands, safety checks, and expected proof artifacts.",
        "operator_runbook": [
            "Inspect this harness before running commands.",
            "Run only commands marked safe_local_only=true in a private local checkout.",
            "Capture resulting JSON/markdown evidence locally.",
            "Stop and ask Jake before any public push, publish, deploy, outreach, wallet, payment, or external-send action.",
        ],
        "acceptance_steps": steps,
        "expected_artifacts": [
            manifest_rel,
            "agentpress/gorilla/utility-pack",
            "agentpress/gorilla/glm-bootstrap-conveyor-wave87-proof",
            DEFAULT_OUT,
            DEFAULT_MD,
            DEFAULT_REPLAY,
        ],
        "local_replay_script": DEFAULT_REPLAY,
        "local_only_assertions": [
            "first useful command is local AgentPress CLI only",
            "proof command is local AgentPress CLI only",
            "manifest safety flags deny external writes, payments, and public push/publish/deploy",
            "Jake explicit approval remains required before any public or external action",
        ],
        "public_publish_push_gate": "Jake explicit approval required; no public action performed.",
    }
    if not steps:
        blockers.append("harness_missing_acceptance_steps")
    return {
        "kind": "agentpress_gorilla_manifest_acceptance_harness",
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": "ok" if not blockers else "blocked",
        "source_manifest": manifest_rel,
        "acceptance_harness": harness,
        "public_actions_taken": [],
        "external_actions": [],
        "payment_actions_taken": [],
        "secret_material_included": False,
        "package_json_inclusion_expectations": package,
        "npm_pack_dry_run": pack,
        "blockers": blockers,
    }


def markdown(doc: dict[str, Any]) -> str:
    harness = doc["acceptance_harness"]
    lines = [
        "# AgentPress Gorilla manifest acceptance harness (wave96)",
        "",
        f"- Status: `{doc['status']}`",
        f"- Harness ID: `{harness['harness_id']}`",
        f"- Source manifest: `{doc['source_manifest']}`",
        "- Public actions taken: `[]`",
        "- External actions: `[]`",
        "- Payment actions taken: `[]`",
        "",
        "## Painpoint solved",
        "",
        harness["painpoint_solved"],
        "",
        "## Acceptance steps",
    ]
    for row in harness.get("acceptance_steps", []):
        command = row.get("command") or "(inspect only)"
        lines.append(f"- {row.get('step')}. `{row.get('name')}` — `{command}` — `{row.get('acceptance_observation')}`")
    lines.extend(["", "## Safety gate", "", harness.get("public_publish_push_gate", ""), "", "## Blockers"])
    lines.extend([f"- {b}" for b in doc.get("blockers", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def replay_script(doc: dict[str, Any]) -> str:
    harness = doc["acceptance_harness"]
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated by scripts/agentpress_gorilla_manifest_acceptance_harness.py",
        "# Local-only replay helper: runs only commands that passed the manifest safety allowlist.",
        "# Jake explicit approval remains required before any public push/publish/deploy, outreach, wallet, payment, or external-send action.",
        f"# Harness ID: {harness['harness_id']}",
        "",
        "echo 'AgentPress Gorilla manifest acceptance replay (local-only)'",
        "echo 'Stop before any public action; Jake approval required.'",
        "",
    ]
    command_count = 0
    for row in harness.get("acceptance_steps", []):
        command = row.get("command")
        if not command or row.get("safe_local_only") is not True:
            lines.append(f"echo {shlex.quote('inspect step ' + str(row.get('step')) + ': ' + str(row.get('name')))}")
            continue
        command_count += 1
        lines.append(f"echo {shlex.quote('running step ' + str(row.get('step')) + ': ' + str(row.get('name')))}")
        lines.append(command)
        lines.append("")
    lines.append(f"echo {shlex.quote('Replay complete; local commands run: ' + str(command_count))}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, doc: dict[str, Any], out_rel: str, md_rel: str, replay_rel: str | None = None) -> None:
    (root / out_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / out_rel).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / md_rel).write_text(markdown(doc), encoding="utf-8")
    if replay_rel:
        replay_path = root / replay_rel
        replay_path.write_text(replay_script(doc), encoding="utf-8")
        replay_path.chmod(0o755)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--markdown-out", default=DEFAULT_MD)
    parser.add_argument("--replay-script", default=DEFAULT_REPLAY)
    parser.add_argument("--include-pack-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    doc = build_harness(root, manifest_rel=args.manifest, include_pack=False)
    write_outputs(root, doc, args.out, args.markdown_out, args.replay_script)
    if args.include_pack_check:
        doc = build_harness(root, manifest_rel=args.manifest, include_pack=True)
        write_outputs(root, doc, args.out, args.markdown_out, args.replay_script)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    return 0 if doc["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
