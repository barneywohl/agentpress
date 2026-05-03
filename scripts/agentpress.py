#!/usr/bin/env python3
"""AgentPress static publication generator/validator/scorer.

Usage:
  python3 scripts/agentpress.py init out-dir --title "My Agent Benchmark"
  python3 scripts/agentpress.py validate out-dir
  python3 scripts/agentpress.py audit out-dir
  python3 scripts/agentpress.py verify out-dir --json
  python3 scripts/agentpress.py schema --json
  python3 scripts/agentpress.py fetch --base file:///path/to/agentpress/ --out fetched-agentpress
  python3 scripts/agentpress.py negative-fixtures --json
  python3 scripts/agentpress.py message create-request --capability validate_agentpress_bundle --task "Verify bundle" --requester-id my-agent --out request.json
  python3 scripts/agentpress.py bundle docs/ --out agentpress/examples/my-docs --title "My Docs" --force
  python3 scripts/agentpress.py package . --out dist/agentpress-offline.tar.gz
  python3 scripts/agentpress.py package-verify dist/agentpress-offline.tar.gz --json
  python3 scripts/agentpress.py tools-manifest
  python3 scripts/agentpress.py tools-manifest-check --json
  python3 scripts/agentpress.py team-pack --slug example-team --capability research:market-map --consent-source public_source --out /tmp/example-team.json
  python3 scripts/agentpress.py self-test --agent-id my-agent --out /tmp/agentpress-self-test.jsonl
  python3 scripts/agentpress.py index-search --json
  python3 scripts/agentpress.py search "message route capability" --json
  python3 scripts/agentpress.py score out-dir
  python3 scripts/agentpress.py build out-dir --out public-dir
"""
import argparse
import contextlib
import io
import hashlib
import html
import json
import pathlib
import re
import shutil
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

REQUIRED = [
    "README.md",
    "AGENT_ENTRYPOINT.md",
    "agent-task-card.json",
    "llms.txt",
    "sitemap.xml",
    "CITATION.cff",
    "disclaimer.md",
]

AGENTPRESS_REQUIRED = REQUIRED + [
    "source-map.json",
    "freshness.json",
    "allowed-actions.json",
    "citation-policy.md",
    ".well-known/ai-ingestion.json",
]

CANONICAL_BASE_URL = "https://barneywohl.github.io/agentpress/"
SCHEMA_REL_ROOT = "agentpress/schemas"
CONTRACT_SCHEMA_MAP = {
    "agent-task-card.json": "agent-task-card.schema.json",
    "source-map.json": "source-map.schema.json",
    "freshness.json": "freshness.schema.json",
    "allowed-actions.json": "allowed-actions.schema.json",
    ".well-known/ai-ingestion.json": "ai-ingestion.schema.json",
    "article-card.json": "article-card.schema.json",
}

FETCH_ASSETS = [
    "llms.txt",
    ".well-known/agentpress.json",
    ".well-known/ai-ingestion.json",
    "agentpress/agent-instructions.json",
    "agentpress/payments/payment-policy.json",
    "agentpress/payments/payment-capabilities.json",
    "agentpress/payments/x402-readiness.json",
    "agentpress/schemas/index.json",
    "agentpress/agentpress-registry.json",
    "agentpress/articles/article-index.json",
    "agentpress/hash-manifest.json",
    "openapi.yaml",
]

DEFAULT_SCHEMA = {
    "decision": "survive | delete | needs_more_diligence",
    "reasons": ["string"],
    "verified_sources": ["string"],
    "missing_checks": ["string"],
    "confidence": "low | medium | high",
    "disclaimer": "Public reference only. Follow the allowed-actions boundary and verify source claims before external use.",
}

SCORE_RUBRIC = [
    ("obvious_entrypoint", 15, lambda r: (r/"AGENT_ENTRYPOINT.md").exists() and "Primary task" in read_text(r/"AGENT_ENTRYPOINT.md")),
    ("machine_readable_task_card", 15, lambda r: _has_task_card(r)),
    ("source_citation_coverage", 20, lambda r: (r/"source-map.json").exists() and (r/"citation-policy.md").exists()),
    ("freshness_clarity", 10, lambda r: (r/"freshness.json").exists()),
    ("allowed_actions_safety", 10, lambda r: (r/"allowed-actions.json").exists()),
    ("eval_artifact", 10, lambda r: (r/"evals").exists() and any((r/"evals").glob("*.jsonl"))),
    ("human_landing_parity", 10, lambda r: (r/"README.md").exists()),
    ("ethical_telemetry_discovery", 5, lambda r: (r/".well-known/ai-ingestion.json").exists()),
    ("sitemap_registry_readiness", 5, lambda r: (r/"sitemap.xml").exists()),
]


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "agent-publication"


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def today() -> str:
    return date.today().isoformat()


def canonical_join(canonical: str, asset: str = "") -> str:
    if not canonical.endswith("/"):
        canonical += "/"
    return canonical + asset


def _task_card(title: str, canonical: str, task_type: str, primary_task: str) -> dict:
    return {
        "schema_version": "1.0",
        "name": title,
        "title": title,
        "task_type": task_type,
        "canonical_url": canonical,
        "target_agents": ["research agents", "RAG systems", "eval harnesses", "crawler/indexing agents"],
        "objective": primary_task,
        "input_contract": {"required": ["subject", "hypothesis"], "optional": ["source_url", "time_horizon", "context"]},
        "output_contract": {"required": list(DEFAULT_SCHEMA.keys()), "decision_values": ["survive", "delete", "needs_more_diligence"]},
        "primary_assets": ["AGENT_ENTRYPOINT.md", "README.md", "source-map.json", "citation-policy.md"],
        "source_requirements": ["Cite primary evidence where possible", "Mark missing checks explicitly", "Do not treat this artifact as authorization for external writes or production changes"],
        "scoring_rubric": {
            "source_grounding": 30,
            "task_completion": 25,
            "error_detection": 20,
            "clear_decision": 15,
            "uncertainty_and_disclaimer": 10,
        },
        "non_goals": ["investment recommendation", "uncited claims", "private data access"],
        "allowed_actions": ["read", "summarize", "cite", "transform", "benchmark", "create_pull_request"],
        "prohibited_actions": ["trading_recommendation", "deceptive_tracking", "bypass_paywall", "private_data_access"],
        "disclaimer": "Public reference only. Follow the allowed-actions boundary and verify source claims before external use.",
    }


def _source_map(title: str, canonical: str) -> dict:
    return {
        "schema_version": "0.1",
        "publication": title,
        "claims": [
            {
                "claim_id": "claim-001",
                "claim": "This publication is an agent-native research artifact with explicit task, citation, and safety boundaries.",
                "confidence": "high",
                "sources": [
                    {"title": "Agent entrypoint", "url_or_path": "AGENT_ENTRYPOINT.md", "retrieved_or_updated_at": today(), "evidence_type": "primary"},
                    {"title": "Task card", "url_or_path": "agent-task-card.json", "retrieved_or_updated_at": today(), "evidence_type": "primary"},
                ],
                "freshness_window_days": 30,
                "kill_criteria": ["Required files missing", "Sources cannot be cited", "Disclaimer removed"],
            }
        ],
        "canonical_url": canonical,
    }


def _freshness(title: str) -> dict:
    return {
        "schema_version": "0.1",
        "publication": title,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "last_reviewed_at": today(),
        "refresh_policy": "Refresh when source filings, claims, or task contracts change; otherwise re-audit monthly.",
        "stale_zones": ["market data", "filing status", "liquidity/depth", "company disclosures"],
        "default_freshness_window_days": 30,
    }


def _allowed_actions() -> dict:
    return {
        "schema_version": "0.1",
        "allowed": ["read", "summarize", "cite", "transform", "benchmark", "open_issue", "create_pr"],
        "requires_human_approval": ["external_post", "investment_recommendation", "private_data_access"],
        "prohibited": ["deceptive_tracking", "impersonation", "spam", "bypass_paywall", "trading_recommendation"],
    }


def _ai_ingestion(title: str, canonical: str) -> dict:
    return {
        "schema_version": "0.1",
        "name": title,
        "canonical_url": canonical,
        "entrypoint": canonical_join(canonical, "AGENT_ENTRYPOINT.md"),
        "llms_txt": canonical_join(canonical, "llms.txt"),
        "task_card": canonical_join(canonical, "agent-task-card.json"),
        "source_map": canonical_join(canonical, "source-map.json"),
        "allowed_actions": canonical_join(canonical, "allowed-actions.json"),
        "citation_policy": canonical_join(canonical, "citation-policy.md"),
        "disclaimer": "Public reference only. Follow the allowed-actions boundary and verify source claims before external use.",
    }


def init(args):
    out = pathlib.Path(args.out)
    title = args.title
    slug = slugify(title)
    canonical = args.canonical or f"https://example.com/{slug}/"
    summary = args.summary or "Agent-native publication with a human-readable brief, machine-readable task card, and crawler/RAG-friendly metadata."
    primary_task = args.primary_task or "Execute the task, verify claims against source evidence, and return the requested output schema without hiding uncertainty."
    agent_entry = f"""# {title} — Agent Entrypoint

{summary}

## Primary task

{primary_task}

## Input contract

Required: subject, hypothesis

Optional: source_url, time_horizon, context

## Expected output schema

```json
{json.dumps(DEFAULT_SCHEMA, indent=2)}
```

## Citation policy

Cite source evidence from `source-map.json` and canonical assets. Do not cite unsupported claims.

## Allowed actions

Read, summarize, cite, transform, benchmark, open an issue, or create a pull request. Do not recommend trades or access private data.

## Non-goals

- Do not hallucinate sources.
- Do not hide uncertainty.
- Do not turn reference guidance into external writes or production changes.

## Citation / disclaimer

Public reference only. Follow the allowed-actions boundary and verify source claims before external use. Canonical URL: {canonical}
"""
    write(out/"README.md", f"# {title}\n\n{summary}\n\nStart with [`AGENT_ENTRYPOINT.md`](./AGENT_ENTRYPOINT.md), then ingest [`agent-task-card.json`](./agent-task-card.json).\n")
    write(out/"AGENT_ENTRYPOINT.md", agent_entry)
    write(out/"agent-task-card.json", json.dumps(_task_card(title, canonical, args.task_type, primary_task), indent=2) + "\n")
    write(out/"source-map.json", json.dumps(_source_map(title, canonical), indent=2) + "\n")
    write(out/"freshness.json", json.dumps(_freshness(title), indent=2) + "\n")
    write(out/"allowed-actions.json", json.dumps(_allowed_actions(), indent=2) + "\n")
    write(out/".well-known/ai-ingestion.json", json.dumps(_ai_ingestion(title, canonical), indent=2) + "\n")
    write(out/"citation-policy.md", f"# Citation Policy\n\nCite `{canonical}` and the source evidence listed in `source-map.json`. Mark missing checks explicitly. Public reference only. Follow the allowed-actions boundary and verify source claims before external use.\n")
    write(out/"llms.txt", f"# {title}\n\nURL: {canonical}\nType: Agent-native publication\n\n## Summary\n\n{summary}\n\n## Primary task\n\n{primary_task}\n")
    write(out/"sitemap.xml", f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n  <url><loc>{canonical}</loc></url>\n  <url><loc>{canonical_join(canonical, 'AGENT_ENTRYPOINT.md')}</loc></url>\n  <url><loc>{canonical_join(canonical, 'agent-task-card.json')}</loc></url>\n  <url><loc>{canonical_join(canonical, 'source-map.json')}</loc></url>\n  <url><loc>{canonical_join(canonical, 'llms.txt')}</loc></url>\n</urlset>\n")
    write(out/"CITATION.cff", f"cff-version: 1.2.0\ntitle: \"{title}\"\nmessage: \"Cite this agent-native publication.\"\n")
    write(out/"disclaimer.md", "# Disclaimer\n\nPublic reference only. Follow the allowed-actions boundary and verify source claims before external use.\n")
    write(out/"evals"/"smoke.jsonl", json.dumps({"input": {"subject": title, "hypothesis": "publication is agent usable"}, "expected": {"decision": "survive", "requires_citations": True}}) + "\n")
    print(f"created {out}")


def _parse_json_files(root: pathlib.Path) -> list[str]:
    errors = []
    for p in root.rglob("*.json"):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"{p}: {e}")
    return errors


def _parse_xml_files(root: pathlib.Path) -> list[str]:
    errors = []
    for p in root.rglob("*.xml"):
        try:
            ET.parse(p)
        except Exception as e:
            errors.append(f"{p}: {e}")
    return errors


def schema_root() -> pathlib.Path:
    root = pathlib.Path(__file__).resolve().parents[1] / SCHEMA_REL_ROOT
    if root.exists():
        return root
    cwd_root = pathlib.Path.cwd() / SCHEMA_REL_ROOT
    return cwd_root


def schema_url(schema_name: str) -> str:
    return canonical_join(CANONICAL_BASE_URL, f"{SCHEMA_REL_ROOT}/{schema_name}")


def fetch_url(base: str, asset: str) -> str:
    if not base.endswith("/"):
        base += "/"
    parsed = urlparse(base)
    if parsed.scheme in {"http", "https", "file"}:
        return urljoin(base, asset)
    return (pathlib.Path(base).resolve() / asset).as_uri()


def _read_fetch_asset(base: str, asset: str, timeout: int) -> tuple[str, bytes]:
    url = fetch_url(base, asset)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https", "file"}:
        raise ValueError(f"unsupported fetch scheme for {asset}: {parsed.scheme or 'none'}")
    with urlopen(url, timeout=timeout) as response:
        return url, response.read()


def schema_rows() -> list[dict]:
    root = schema_root()
    rows = []
    for path in sorted(root.glob("*.schema.json")) if root.exists() else []:
        key = path.name.removesuffix(".schema.json").replace("-", "_")
        rows.append({"name": key, "file": path.name, "url": schema_url(path.name), "local_path": str(path)})
    return rows


def _schema_required_errors(payload: dict, schema_path: pathlib.Path, label: str) -> list[str]:
    if not schema_path.exists():
        return [f"missing schema for {label}: {schema_path}"]
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"invalid schema {schema_path}: {e}"]
    errors = []
    for key in schema.get("required", []):
        if key not in payload:
            errors.append(f"{label} missing schema-required field: {key}")
    properties = schema.get("properties", {})
    type_map = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}
    for key, spec in properties.items():
        if key not in payload:
            continue
        expected = spec.get("type") if isinstance(spec, dict) else None
        if isinstance(expected, list):
            allowed = tuple(type_map[t] for t in expected if t in type_map)
            if allowed and payload[key] is not None and not isinstance(payload[key], allowed):
                errors.append(f"{label}.{key} expected one of {expected}")
        elif expected in type_map and not isinstance(payload[key], type_map[expected]):
            errors.append(f"{label}.{key} expected {expected}")
    return errors


def _validate_contract_files(root: pathlib.Path) -> list[str]:
    root = root.resolve()
    schemas = schema_root()
    errors = []
    for rel, schema_name in CONTRACT_SCHEMA_MAP.items():
        path = root / rel
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"{path}: {e}")
            continue
        errors.extend(_schema_required_errors(payload, schemas / schema_name, rel))
    return errors


def _validate_eval_files(root: pathlib.Path) -> tuple[list[str], int]:
    errors = []
    count = 0
    eval_root = root / "evals"
    if not eval_root.exists():
        return errors, count
    for p in sorted(eval_root.glob("*.jsonl")):
        for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            count += 1
            try:
                row = json.loads(line)
            except Exception as e:
                errors.append(f"{p}:{lineno}: invalid jsonl: {e}")
                continue
            if not isinstance(row, dict):
                errors.append(f"{p}:{lineno}: eval row must be object")
                continue
            if "input" not in row or "expected" not in row:
                errors.append(f"{p}:{lineno}: eval row requires input and expected")
    return errors, count


def _has_task_card(root: pathlib.Path) -> bool:
    p = root/"agent-task-card.json"
    if not p.exists():
        return False
    try:
        card = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return False
    return all(k in card for k in ["task_type", "target_agents", "objective", "input_contract", "output_contract", "scoring_rubric", "disclaimer"])


def audit_root(root: pathlib.Path, strict: bool = True) -> tuple[int, list[str], list[str]]:
    required = AGENTPRESS_REQUIRED if strict else REQUIRED
    errors = [f"missing required file: {f}" for f in required if not (root/f).exists()]
    warnings = []
    errors.extend(_parse_json_files(root))
    errors.extend(_parse_xml_files(root))
    if not _has_task_card(root):
        errors.append("agent-task-card.json missing required fields")
    entry = read_text(root/"AGENT_ENTRYPOINT.md")
    for phrase in ["Primary task", "Input contract", "Expected output schema"]:
        if phrase not in entry:
            errors.append(f"AGENT_ENTRYPOINT.md missing {phrase}")
    combined = entry + "\n" + read_text(root/"disclaimer.md") + "\n" + read_text(root/"citation-policy.md")
    if not ("allowed-actions" in combined or "allowed actions" in combined or "allowed-action" in combined):
        errors.append("missing allowed-actions safety disclaimer")
    errors.extend(_validate_contract_files(root))
    eval_errors, eval_count = _validate_eval_files(root)
    errors.extend(eval_errors)
    if eval_count == 0:
        warnings.append("no evals/*.jsonl smoke test found")
    return (0 if not errors else 1), errors, warnings


def validate(args):
    root = pathlib.Path(args.out)
    code, errors, warnings = audit_root(root, strict=False)
    if getattr(args, "json", False):
        print(json.dumps({"status": "ok" if code == 0 else "fail", "path": str(root), "errors": errors, "warnings": warnings}, indent=2))
        return code
    if code:
        for e in errors:
            print(e)
        return 1
    for w in warnings:
        print(f"warning: {w}")
    print("agentpress validation ok")
    return 0


def audit(args):
    root = pathlib.Path(args.out)
    code, errors, warnings = audit_root(root, strict=True)
    if getattr(args, "json", False):
        print(json.dumps({"status": "ok" if code == 0 else "fail", "path": str(root), "errors": errors, "warnings": warnings}, indent=2))
        return code
    for e in errors:
        print(f"error: {e}")
    for w in warnings:
        print(f"warning: {w}")
    if code == 0:
        print("agentpress audit ok")
    return code


def schema_command(args):
    rows = schema_rows()
    if args.name:
        wanted = args.name.replace("-", "_").removesuffix("_schema_json")
        rows = [r for r in rows if r["name"] == wanted or r["file"] == args.name or r["file"] == f"{args.name}.schema.json"]
        if not rows:
            print(f"unknown schema: {args.name}", file=sys.stderr)
            return 1
    payload = {"schema_version": "2026-05-03.agentpress-cli-schema.v1", "canonical_base_url": CANONICAL_BASE_URL, "count": len(rows), "schemas": rows}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for row in rows:
            print(f"{row['name']}	{row['url']}	{row['local_path']}")
    return 0


def verify(args):
    root = pathlib.Path(args.out)
    code, errors, warnings = audit_root(root, strict=True)
    checked = sorted(rel for rel in CONTRACT_SCHEMA_MAP if (root / rel).exists())
    payload = {
        "status": "ok" if code == 0 else "fail",
        "path": str(root),
        "checked_contracts": checked,
        "schema_index": schema_url("index.json"),
        "errors": errors,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for e in errors:
            print(f"error: {e}")
        for w in warnings:
            print(f"warning: {w}")
        if code == 0:
            print(f"agentpress verify ok ({len(checked)} contracts checked)")
            print(f"schema index: {payload['schema_index']}")
    return code



def negative_fixtures(args):
    manifest_path = pathlib.Path(args.manifest)
    if not manifest_path.exists():
        print(f"missing negative fixture manifest: {manifest_path}", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = []
    failures = []
    for item in manifest.get("fixtures", []):
        fixture_path = pathlib.Path(item["path"])
        expected = item.get("expected_error_contains", "")
        code, errors, warnings = audit_root(fixture_path, strict=True)
        joined = "\n".join(errors + warnings)
        passed = code != 0 and (not expected or expected in joined)
        row = {
            "path": str(fixture_path),
            "expected_error_contains": expected,
            "verify_status": "fail" if code else "ok",
            "matched_expected_error": bool(expected and expected in joined),
            "errors": errors,
            "warnings": warnings,
            "result": "pass" if passed else "fail",
        }
        rows.append(row)
        if not passed:
            failures.append(row)
    payload = {
        "schema_version": "2026-05-03.agentpress-negative-fixtures-result.v1",
        "status": "ok" if not failures else "fail",
        "manifest": str(manifest_path),
        "count": len(rows),
        "passed": len(rows) - len(failures),
        "failed": len(failures),
        "failures": failures,
        "fixtures": rows,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"negative fixtures: {payload['passed']}/{payload['count']} passed")
        for row in failures:
            print(f"error: fixture did not fail as expected: {row['path']}")
    return 0 if not failures else 1

def fetch(args):
    dest = pathlib.Path(args.out)
    dest.mkdir(parents=True, exist_ok=True)
    assets = args.asset or FETCH_ASSETS
    rows = []
    errors = []
    for asset in assets:
        rel = asset.lstrip("/")
        try:
            url, data = _read_fetch_asset(args.base, rel, args.timeout)
        except Exception as e:
            errors.append({"path": rel, "error": str(e)})
            if not args.keep_going:
                break
            continue
        out_path = dest / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        rows.append({
            "path": rel,
            "url": url,
            "local_path": str(out_path),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    manifest = {
        "schema_version": "2026-05-03.agentpress-fetch.v1",
        "status": "ok" if not errors else "fail",
        "base": args.base,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "assets": rows,
        "errors": errors,
    }
    manifest_path = dest / ".agentpress-fetch-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(f"fetched {len(rows)} AgentPress assets into {dest}")
        print(f"manifest: {manifest_path}")
        for err in errors:
            print(f"error: {err['path']}: {err['error']}", file=sys.stderr)
    return 0 if not errors else 1


def score_value(root: pathlib.Path) -> tuple[int, dict]:
    detail = {}
    total = 0
    for name, points, check in SCORE_RUBRIC:
        ok = bool(check(root))
        detail[name] = points if ok else 0
        total += points if ok else 0
    return total, detail


def score(args):
    root = pathlib.Path(args.out)
    total, detail = score_value(root)
    print(json.dumps({"path": str(root), "score": total, "detail": detail, "badge": f"![AgentPress score](https://img.shields.io/badge/AgentPress-{total}%2F100-blue)"}, indent=2))
    return 0 if total >= 80 else 1


def build(args):
    src = pathlib.Path(args.out)
    dst = pathlib.Path(args.dest)
    code, errors, _warnings = audit_root(src, strict=False)
    if code:
        for e in errors:
            print(f"error: {e}")
        return 1
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    title = "AgentPress Publication"
    card_path = src/"agent-task-card.json"
    if card_path.exists():
        card = json.loads(card_path.read_text(encoding="utf-8"))
        title = card.get("title") or card.get("name") or title
    write(dst/"index.html", f"<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>{title}</title></head><body><main><h1>{title}</h1><p>AgentPress publication. Start with <a href=\"AGENT_ENTRYPOINT.md\">AGENT_ENTRYPOINT.md</a>.</p><ul><li><a href=\"agent-task-card.json\">Task card</a></li><li><a href=\"llms.txt\">llms.txt</a></li><li><a href=\"source-map.json\">Source map</a></li></ul></main></body></html>\n")
    print(f"built {dst}")
    return 0



def list_examples(args):
    root = pathlib.Path(args.root)
    examples = sorted(p for p in root.iterdir() if p.is_dir() and (p/"agent-task-card.json").exists()) if root.exists() else []
    if args.json:
        rows = []
        for ex in examples:
            total, detail = score_value(ex)
            rows.append({"slug": ex.name, "path": str(ex), "score": total, "detail": detail})
        print(json.dumps({"root": str(root), "count": len(rows), "examples": rows}, indent=2))
    else:
        print(f"AgentPress examples under {root} ({len(examples)})")
        for ex in examples:
            total, _detail = score_value(ex)
            print(f"- {ex.name}: {total}/100 ({ex})")
    return 0


def index_articles(args):
    """Build a machine-readable bundle index from AgentPress examples."""
    src_root = pathlib.Path(args.root)
    dest = pathlib.Path(args.out)
    base_url = args.base_url.rstrip("/")
    dest.mkdir(parents=True, exist_ok=True)
    articles = []
    claims = []
    sources = []
    freshness_rows = []
    eval_rows = []
    languages = {}
    examples = sorted(p for p in src_root.iterdir() if p.is_dir() and (p/"agent-task-card.json").exists()) if src_root.exists() else []
    for ex in examples:
        slug = ex.name
        card = json.loads((ex/"agent-task-card.json").read_text(encoding="utf-8"))
        source_map = json.loads((ex/"source-map.json").read_text(encoding="utf-8")) if (ex/"source-map.json").exists() else {"claims": []}
        fresh = json.loads((ex/"freshness.json").read_text(encoding="utf-8")) if (ex/"freshness.json").exists() else {}
        allowed = json.loads((ex/"allowed-actions.json").read_text(encoding="utf-8")) if (ex/"allowed-actions.json").exists() else {}
        title = card.get("title") or card.get("name") or slug.replace("-", " ").title()
        url = f"{base_url}/agentpress/examples/{slug}/"
        summary = card.get("objective") or title
        flagship_slugs = {"universal-agent-reachability", "agent-knowledge-sharing"}
        default_domains = ["agent_infrastructure", "agent_compatibility", "knowledge_sharing"] if slug in flagship_slugs else ["agent_infrastructure", "reference_example"]
        domains = card.get("domains") or default_domains
        task_type = str(card.get("task_type", "agent_native_publication"))
        task_types = sorted(set(["agent_native_article"] + (["benchmark"] if "benchmark" in task_type else []) + (["compatibility"] if "reachability" in task_type or "compatibility" in task_type else []) + (["knowledge_transfer"] if "knowledge" in task_type else [])))
        evals = [str(p.relative_to(ex)) for p in sorted((ex/"evals").glob("*.jsonl"))] if (ex/"evals").exists() else []
        article_card = {
            "schema_version": "0.1",
            "type": "agentpress_article",
            "title": title,
            "slug": slug,
            "canonical_url": url,
            "summary_for_agents": summary,
            "agent_fallback_summary": read_text(ex/"README.md").replace("\n", " ")[:500] or summary,
            "domains": domains,
            "task_types": task_types,
            "target_agent_families": card.get("target_agents") or ["browser_agent", "coding_agent", "rag_agent", "search_crawler"],
            "languages": card.get("languages") or (["en", "zh-CN", "es"] if slug == "agent-knowledge-sharing" else ["en"]),
            "regions": card.get("regions") or (["global", "restricted_networks"] if slug in flagship_slugs else ["global"]),
            "claims": [{"claim_id": c.get("claim_id"), "source_map_url": "source-map.json"} for c in source_map.get("claims", []) if c.get("claim_id")],
            "freshness": {"last_reviewed_at": fresh.get("last_reviewed_at") or str(fresh.get("generated_at", ""))[:10], "stale_zones": fresh.get("stale_zones", []), "freshness_window_days": fresh.get("default_freshness_window_days") or 30},
            "actions": {"allowed_actions_url": "allowed-actions.json", "allowed": allowed.get("allowed") or card.get("allowed_actions", []), "requires_human_approval": allowed.get("requires_human_approval", []), "prohibited": allowed.get("prohibited") or card.get("prohibited_actions", [])},
            "evals": evals,
            "related_articles": [],
            "machine_entrypoints": {"task_card": "agent-task-card.json", "source_map": "source-map.json", "llms_txt": "llms.txt", "ai_ingestion": ".well-known/ai-ingestion.json", "article_card": "article-card.json"},
            "disclaimer": card.get("disclaimer", "Public reference only. Follow the allowed-actions boundary and verify source claims before external use."),
        }
        write(ex/"article-card.json", json.dumps(article_card, indent=2, ensure_ascii=False) + "\n")
        row = {k: article_card[k] for k in ["title", "slug", "canonical_url", "summary_for_agents", "domains", "task_types", "target_agent_families", "languages", "regions"]}
        row.update({"article_card": url + "article-card.json", "task_card": url + "agent-task-card.json", "source_map": url + "source-map.json", "freshness": url + "freshness.json", "allowed_actions": url + "allowed-actions.json", "eval_count": len(evals)})
        articles.append(row)
        for lang in article_card["languages"]:
            languages.setdefault(lang, []).append(slug)
        for c in source_map.get("claims", []):
            cid = c.get("claim_id") or f"{slug}-claim"
            claims.append({"article_slug": slug, "article_url": url, "claim_id": cid, "claim": c.get("claim", ""), "confidence": c.get("confidence"), "sources": [s.get("url_or_path") for s in c.get("sources", [])], "freshness_window_days": c.get("freshness_window_days")})
            for src in c.get("sources", []):
                row_src = {"article_slug": slug, "claim_id": cid}; row_src.update(src); sources.append(row_src)
        freshness_rows.append({"article_slug": slug, "article_url": url, **article_card["freshness"]})
        for ev in evals:
            eval_rows.append({"article_slug": slug, "article_url": url, "eval": ev, "url": url + ev})
    generated_at = datetime.now(timezone.utc).isoformat()
    write(dest/"article-index.json", json.dumps({"schema_version": "0.1", "type": "agentpress_article_index", "generated_at": generated_at, "count": len(articles), "articles": articles}, indent=2, ensure_ascii=False) + "\n")
    write(dest/"article-index.jsonl", "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in articles))
    write(dest/"claim-index.jsonl", "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in claims))
    write(dest/"source-index.jsonl", "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in sources))
    write(dest/"freshness-index.jsonl", "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in freshness_rows))
    write(dest/"eval-index.jsonl", "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in eval_rows))
    write(dest/"collections.json", json.dumps({"schema_version": "0.1", "generated_at": generated_at, "collections": [{"slug": "flagship-agent-infrastructure", "title": "Flagship Agent Infrastructure", "article_slugs": [a["slug"] for a in articles if "agent_infrastructure" in a["domains"]]}, {"slug": "reference-examples", "title": "General Reference Examples", "article_slugs": [a["slug"] for a in articles if "reference_example" in a["domains"] or a["slug"] not in {"universal-agent-reachability", "agent-knowledge-sharing"}]}]}, indent=2, ensure_ascii=False) + "\n")
    topics = {}
    for a in articles:
        for key in a["domains"] + a["task_types"] + a["target_agent_families"]:
            topics.setdefault(slugify(str(key)), []).append(a["slug"])
    write(dest/"topics.json", json.dumps({"schema_version": "0.1", "generated_at": generated_at, "topics": topics}, indent=2, ensure_ascii=False) + "\n")
    write(dest/"language-index.json", json.dumps({"schema_version": "0.1", "generated_at": generated_at, "languages": languages}, indent=2, ensure_ascii=False) + "\n")
    write(dest/"README.md", f"# AgentPress Bundle Index\n\nGenerated index of agent-native bundles.\n\nCurrent bundle count: {len(articles)}.\n")
    print(f"indexed {len(articles)} AgentPress articles into {dest}")
    return 0


def build_all(args):
    src_root = pathlib.Path(args.root)
    dest_root = pathlib.Path(args.dest)
    examples = sorted(p for p in src_root.iterdir() if p.is_dir() and (p/"agent-task-card.json").exists()) if src_root.exists() else []
    if not examples:
        print(f"no AgentPress examples found under {src_root}", file=sys.stderr)
        return 1
    if dest_root.exists() and args.clean:
        shutil.rmtree(dest_root)
    dest_root.mkdir(parents=True, exist_ok=True)
    registry = []
    failures = []
    for ex in examples:
        code, errors, warnings = audit_root(ex, strict=True)
        if code:
            failures.append({"path": str(ex), "errors": errors, "warnings": warnings})
            continue
        out = dest_root / ex.name
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(ex, out)
        title = "AgentPress Publication"
        card_path = ex/"agent-task-card.json"
        if card_path.exists():
            card = json.loads(card_path.read_text(encoding="utf-8"))
            title = card.get("title") or card.get("name") or title
        write(out/"index.html", f'<!doctype html>\n<html><head><meta charset="utf-8"><title>{title}</title></head><body><main><h1>{title}</h1><p>AgentPress publication. Start with <a href="AGENT_ENTRYPOINT.md">AGENT_ENTRYPOINT.md</a>.</p><ul><li><a href="agent-task-card.json">Task card</a></li><li><a href="llms.txt">llms.txt</a></li><li><a href="source-map.json">Source map</a></li><li><a href=".well-known/ai-ingestion.json">AI ingestion manifest</a></li></ul></main></body></html>\n')
        total, detail = score_value(ex)
        registry.append({"slug": ex.name, "title": title, "source": str(ex), "built_path": str(out), "score": total, "detail": detail})
    if failures:
        print(json.dumps({"status": "failed", "failures": failures}, indent=2))
        return 1
    write(dest_root/"agentpress-registry.json", json.dumps({"schema_version": "0.1", "generated_at": datetime.now(timezone.utc).isoformat(), "count": len(registry), "publications": registry}, indent=2) + "\n")
    links = "\n".join(f'<li><a href="{r["slug"]}/">{r["slug"]}</a> — AgentPress score {r["score"]}/100</li>' for r in registry)
    write(dest_root/"index.html", f'<!doctype html>\n<html><head><meta charset="utf-8"><title>AgentPress Registry</title></head><body><main><h1>AgentPress Registry</h1><p>Machine-readable registry: <a href="agentpress-registry.json">agentpress-registry.json</a></p><ul>{links}</ul></main></body></html>\n')
    print(f"built {len(registry)} AgentPress examples into {dest_root}")
    return 0





def _iter_source_docs(source: pathlib.Path) -> list[pathlib.Path]:
    allowed = {".md", ".txt", ".yaml", ".yml", ".json", ".html"}
    return sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in allowed and ".git" not in p.parts and "__pycache__" not in p.parts)


def _read_excerpt(path: pathlib.Path, limit: int = 1600) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except TypeError:
        text = path.read_text(encoding="utf-8")
    return text.strip()[:limit]





def team_pack(args):
    capabilities=[]
    for raw in args.capability or []:
        if ":" in raw:
            kind, name = raw.split(":", 1)
        else:
            kind, name = "general", raw
        capabilities.append({"kind": kind.strip(), "name": name.strip(), "confidence": "declared", "evidence": "public_or_consented_source_required"})
    payload={
        "schema_version":"1.0",
        "pack_type":args.pack_type,
        "slug":slugify(args.slug),
        "display_name":args.display_name or args.slug,
        "canonical_url":args.canonical_url or f"https://barneywohl.github.io/agentpress/agentpress/team-packs/{slugify(args.slug)}.json",
        "consent_source":args.consent_source,
        "capabilities":capabilities,
        "availability":{"status":args.availability, "handoff_preference":"agent_message_request"},
        "public_sources":[{"title":x, "url_or_path":x, "evidence_type":"public_or_consented"} for x in _csv_list(args.public_sources)],
        "privacy":{"redaction_default":True, "private_fields_excluded":["personal_phone", "home_address", "private_email", "family_details", "sensitive_traits", "credentials", "private_notes"], "do_not_infer_sensitive_traits":True},
        "allowed_handoffs":_csv_list(args.allowed_handoffs, ["capability_match", "agent_message_request", "public_source_summary", "warm_intro_draft_with_human_review"]),
        "prohibited_uses":["doxxing", "private_data_extraction", "sensitive_trait_inference", "unsolicited_spam", "credential_access", "impersonation"],
        "last_reviewed_at":_utc_now()
    }
    errors=_schema_required_errors(payload, schema_root()/"team-capability-pack-v1.schema.json", "team_pack")
    if args.consent_source == "internal_private_do_not_publish" and not args.allow_private:
        errors.append("internal_private_do_not_publish requires --allow-private and must not be published")
    if not capabilities:
        errors.append("at least one --capability is required")
    if errors:
        print(json.dumps({"status":"fail", "errors":errors}, indent=2)); return 1
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status":"ok", "out":str(out), "slug":payload["slug"], "capability_count":len(capabilities)}, indent=2))
    return 0


def team_pack_validate(args):
    path=pathlib.Path(args.path); payload=json.loads(path.read_text(encoding="utf-8"))
    errors=_schema_required_errors(payload, schema_root()/"team-capability-pack-v1.schema.json", path.name)
    if payload.get("consent_source") == "internal_private_do_not_publish":
        errors.append("pack is marked internal_private_do_not_publish; do not publish")
    if not payload.get("privacy", {}).get("redaction_default"):
        errors.append("privacy.redaction_default must be true")
    result={"status":"ok" if not errors else "fail", "path":str(path), "errors":errors, "capabilities":payload.get("capabilities", [])}
    print(json.dumps(result, indent=2) if args.json else result["status"])
    return 0 if not errors else 1


def self_test(args):
    suite_path = pathlib.Path(args.suite)
    if not suite_path.exists():
        print(f"missing self-test suite: {suite_path}", file=sys.stderr); return 3
    if not re.match(r"^[A-Za-z0-9_.:-]{2,120}$", args.agent_id):
        print("invalid agent-id", file=sys.stderr); return 2
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    run_id = args.run_id or _short_id("run")
    out = pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    rows=[]
    tmp = pathlib.Path(args.workdir); tmp.mkdir(parents=True, exist_ok=True)
    def row(test_id, status, score, evidence=None, errors=None):
        rows.append({"schema_version":"1.0","run_id":run_id,"agent_id":args.agent_id,"test_id":test_id,"status":status,"score":score,"created_utc":_utc_now(),"evidence":evidence or {},"errors":errors or []})
    for test in suite.get("tests", []):
        tid=test.get("test_id", "unknown")
        try:
            kind=test.get("kind")
            if kind == "verify_bundle":
                bundle=pathlib.Path(test.get("bundle", args.bundle))
                code, errors, warnings = audit_root(bundle, strict=True)
                row(tid, "pass" if code == 0 else "fail", 100 if code == 0 else 0, {"bundle":str(bundle),"warnings":warnings}, errors)
            elif kind == "search":
                index=args.index
                if not pathlib.Path(index).exists():
                    build_args=argparse.Namespace(root=".", out=index, base_url=CANONICAL_BASE_URL, json=True)
                    build_search_index(build_args)
                search_args=argparse.Namespace(index=index, query=test.get("query", "agentpress"), limit=5, json=True)
                # inline score without printing duplicate by reading index directly
                idx=json.loads(pathlib.Path(index).read_text(encoding="utf-8")); terms=[t.lower() for t in re.findall(r"[a-zA-Z0-9_.-]+", search_args.query)]
                count=sum(1 for rec in idx.get("records", []) if any(t in rec.get("text", "") for t in terms))
                row(tid, "pass" if count else "fail", 100 if count else 0, {"query":search_args.query,"matches":count})
            elif kind == "message_thread":
                req=tmp/f"{run_id}-request.json"; res=tmp/f"{run_id}-response.json"; thr=tmp/f"{run_id}-thread.json"
                with contextlib.redirect_stdout(io.StringIO()):
                    message_create_request(argparse.Namespace(capability="validate_agentpress_bundle", task="Verify this bundle and report missing contracts", priority="P1", requester_id=args.agent_id, out=str(req), request_id=None, context_urls=None, required_sources=None, allowed_actions=None, requires_human_approval=None, prohibited_actions=None, output_schema=schema_url("agent-response-v1.schema.json"), deadline_utc=None))
                    message_create_response(argparse.Namespace(request=str(req), responder_id="agentpress-reference-agent", status="completed", out=str(res), response_id=None, confidence=0.9, result_inline='{"status":"ok"}', result_bundle=None, sources_used=None, missing_checks=None, actions_taken=None))
                    message_thread_create(argparse.Namespace(request=str(req), out=str(thr), thread_id=None))
                    message_thread_append(argparse.Namespace(thread=str(thr), message=str(res), out=str(thr)))
                payload=json.loads(thr.read_text(encoding="utf-8")); _, errors=_validate_message_payload(payload, "thread")
                row(tid, "pass" if not errors else "fail", 100 if not errors else 0, {"thread":str(thr),"message_count":len(payload.get("messages",[]))}, errors)
            elif kind == "bundle_generator":
                dest=tmp/f"{run_id}-generated-bundle"
                with contextlib.redirect_stdout(io.StringIO()):
                    code=bundle_from_source(argparse.Namespace(source=test.get("source","tests/fixtures/source-docs"), out=str(dest), title="Self Test Generated Bundle", canonical_url="https://example.com/self-test/", primary_task=None, dry_run=False, strict=False, force=True, max_stale_days=30))
                row(tid, "pass" if code == 0 else "fail", 100 if code == 0 else 0, {"generated_bundle":str(dest)})
            elif kind == "negative_fixtures":
                with contextlib.redirect_stdout(io.StringIO()):
                    code=negative_fixtures(argparse.Namespace(manifest="agentpress/fixtures/broken-bundles/expected-failures.json", json=True))
                row(tid, "pass" if code == 0 else "fail", 100 if code == 0 else 0, {"manifest":"agentpress/fixtures/broken-bundles/expected-failures.json"})
            else:
                row(tid, "skip", 0, errors=[f"unknown test kind: {kind}"])
        except Exception as e:
            row(tid, "fail", 0, errors=[str(e)])
    out.write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in rows), encoding="utf-8")
    passed=sum(1 for r in rows if r["status"]=="pass"); total=len(rows); score=round(sum(r.get("score",0) for r in rows)/total) if total else 0
    summary={"status":"ok" if passed==total else "fail", "run_id":run_id, "agent_id":args.agent_id, "passed":passed, "total":total, "score":score, "out":str(out)}
    print(json.dumps(summary, indent=2))
    return 0 if passed==total else 1


def build_search_index(args):
    root = pathlib.Path(args.root)
    out = pathlib.Path(args.out)
    base_url = args.base_url.rstrip("/") + "/"
    records = []
    def add(kind, title, path, text="", tags=None, url=None):
        rel = pathlib.Path(path).as_posix()
        records.append({
            "id": slugify(f"{kind}-{rel}"),
            "kind": kind,
            "title": title,
            "path": rel,
            "url": url or urljoin(base_url, rel),
            "tags": sorted(set(tags or [])),
            "text": " ".join(str(x) for x in [title, rel, text, " ".join(tags or [])] if x).lower()[:5000],
        })
    # Core commands/features
    add("cli_command", "Create AgentPress bundle from docs/API folder", "scripts/agentpress.py", "bundle source docs api generator valid verify", ["generate", "bundle", "docs", "api", "cli"])
    add("cli_command", "Agent message create/route/respond/thread/validate", "scripts/agentpress.py", "message create-request route create-response thread validate coordination", ["message", "route", "coordination", "cli"])
    add("cli_command", "Verify AgentPress bundle", "scripts/agentpress.py", "verify schema contract validation", ["verify", "validate", "schema", "cli"])
    add("cli_command", "Negative fail-closed fixture gate", "scripts/agentpress.py", "negative-fixtures adversarial broken bundles fail closed", ["security", "fail-closed", "test", "cli"])
    add("cli_command", "Install AgentPress from release index", "agentpress/install/install.py", "install release index offline package sha256 verify tarball curl bootstrap one-command", ["install", "release", "offline", "sha256", "cli"])
    add("cli_command", "CLI agent launch pack", "agentpress/CLI_AGENT_LAUNCH.md", "first agent install doctor compatibility matrix self-test landing receipt submission pack attract agents", ["cli", "launch", "install", "proof", "adoption"] )
    add("cli_command", "One-command AgentPress agent onboarding", "agentpress/onboarding/README.md", "adopt agent-onboard one command doctor self-test landing receipt payment status payment intent submission pack exponential adoption flywheel", ["onboard", "adoption", "self-test", "landing", "submission", "payment", "cli"])
    add("traffic", "Agent traffic acquisition pack", "agentpress/traffic/agent-traffic-acquisition.json", "crawler seeds agent sitemap directory submission first autonomous agents landing receipts proof traffic acquisition", ["traffic", "crawler", "directory", "adoption", "agent"] )
    add("traffic", "Agent routes manifest", "agentpress/routes/agent-routes.json", "machine routable agent runtime intent discover install verify prove submit coordinate", ["routes", "agent", "runtime", "intent", "traffic"] )
    add("cli_command", "Agent runtime route resolver", "scripts/agentpress.py", "agent-route runtime intent exact commands discover install verify prove submit coordinate", ["agent-route", "routes", "runtime", "intent", "cli"] )
    add("cli_command", "Agent traffic audit", "agentpress/traffic/agent-traffic-audit.json", "audit agent traffic surfaces crawler seeds routes cli launch proof conversion", ["audit", "traffic", "crawler", "proof", "cli"] )
    add("cli_command", "Submit AgentPress proof receipt", "agentpress/submissions/README.md", "submission-pack landing receipt github issue pull request adoption proof", ["submission", "landing", "proof", "github", "cli"])
    add("cli_command", "Compile AgentPress reputation index", "agentpress/reputation/README.md", "reputation-index trust tier self-test handoff receipt landing proof", ["reputation", "proof", "trust", "cli"])
    add("cli_command", "AgentPress runtime compatibility matrix", "agentpress/compatibility/README.md", "compatibility-matrix codex claude gemini glm browser rag install doctor self-test landing receipt submission proof", ["compatibility", "matrix", "runtime", "proof", "cli"])
    add("cli_command", "Read AgentPress release and contract feed", "agentpress/feeds/contract-feed.json", "changelog contract feed version changed release upgrade agents", ["changelog", "contract", "release", "feed"])
    # Registry examples
    reg = root/"agentpress/agentpress-registry.json"
    if reg.exists():
        data = json.loads(reg.read_text(encoding="utf-8"))
        for pub in data.get("publications", []):
            slug = pub.get("slug", "")
            add("bundle", pub.get("title") or slug, f"agentpress/examples/{slug}/AGENT_ENTRYPOINT.md", json.dumps(pub), ["bundle", "example", "score-"+str(pub.get("score", ""))])
    # Articles
    art = root/"agentpress/articles/article-index.json"
    if art.exists():
        data=json.loads(art.read_text(encoding="utf-8"))
        for a in data.get("articles", []):
            path = a.get("entrypoint") or a.get("path") or f"agentpress/examples/{a.get('slug','')}/AGENT_ENTRYPOINT.md"
            tags = ["article"] + a.get("domains", []) + a.get("task_types", []) + a.get("target_agent_families", [])
            add("article", a.get("title") or a.get("slug") or path, path, json.dumps(a), tags)
    # Schemas
    for schema in sorted((root/"agentpress/schemas").glob("*.schema.json")):
        try: data=json.loads(schema.read_text(encoding="utf-8"))
        except Exception: data={}
        add("schema", data.get("title") or schema.name, schema.relative_to(root), json.dumps(data)[:1200], ["schema", schema.stem.replace(".schema", "")])
    # Hub/capabilities
    cap = root/"agentpress/hub/routing/capability-index.json"
    if cap.exists():
        data=json.loads(cap.read_text(encoding="utf-8"))
        for capability, agents in data.get("capabilities", {}).items():
            add("capability", capability, "agentpress/hub/routing/capability-index.json", " ".join(agents), ["capability", capability])
    # Protocol/docs
    for rel in ["llms.txt", "README.md", "agentpress/AGENT_START_HERE.md", "agentpress/CLI_AGENT_LAUNCH.md", "agentpress/cli-launch.json", "agentpress/traffic/README.md", "agentpress/traffic/agent-traffic-acquisition.json", "agentpress/traffic/agent-traffic-audit.json", "agentpress/traffic/crawler-seeds.txt", "agentpress/routes/README.md", "agentpress/routes/agent-routes.json", "agentpress/directory-submission/agentpress-directory-pitch.json", "agent-sitemap.xml", "agentpress/hub/messages/README.md", "agentpress/protocols/mcp-manifest.json", "agentpress/mesh/README.md", "agentpress/mesh/known-agents.json", "agentpress/install/README.md", "agentpress/install/install.py", "agentpress/onboarding/README.md", "agentpress/onboarding/agent-onboard-example.json", "agentpress/specs/AGENTPRESS_EXPONENTIAL_AGENT_ADOPTION_SPEC_20260503.md", "agentpress/payments/README.md", "agentpress/payments/payment-policy.json", "agentpress/payments/payment-capabilities.json", "agentpress/payments/x402-readiness.json", "agentpress/specs/AGENTPAYMENTS_PLATFORM_SPEC_20260503.md", "agentpress/releases/README.md", "agentpress/releases/release-index.json", "agentpress/submissions/README.md", "agentpress/reputation/README.md", "agentpress/landing/README.md", "agentpress/directory-submission/README.md", "agentpress/directory-submission/submission.json", "agentpress/feeds/contract-feed.json", "agentpress/feeds/changelog.json", "openapi.yaml"]:
        path=root/rel
        if path.exists(): add("doc", path.name, rel, read_text(path)[:1500], ["doc", pathlib.Path(rel).stem])
    payload={"schema_version":"2026-05-03.agentpress-search.v1", "canonical_url": urljoin(base_url, out.as_posix()), "generated_at": _utc_now(), "record_count": len(records), "records": records}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    if args.json: print(json.dumps({"status":"ok", "out": str(out), "record_count": len(records)}, indent=2))
    else: print(f"indexed {len(records)} searchable AgentPress records into {out}")
    return 0


def search_index(args):
    index_path = pathlib.Path(args.index)
    if not index_path.exists():
        print(f"missing search index: {index_path}; run index-search", file=sys.stderr); return 1
    idx=json.loads(index_path.read_text(encoding="utf-8"))
    terms=[t.lower() for t in re.findall(r"[a-zA-Z0-9_.-]+", args.query)]
    rows=[]
    for rec in idx.get("records", []):
        hay=rec.get("text", "")
        score=sum(hay.count(t) for t in terms) + sum(3 for t in terms if t in [x.lower() for x in rec.get("tags", [])])
        if score:
            r={k:rec[k] for k in ["kind","title","path","url","tags"] if k in rec}
            r["score"]=score
            rows.append(r)
    rows=sorted(rows, key=lambda r:(-r["score"], r["kind"], r["title"]))[:args.limit]
    payload={"status":"ok" if rows else "no_results", "query": args.query, "count": len(rows), "results": rows}
    print(json.dumps(payload, indent=2) if args.json else "\n".join(f"{r['score']} {r['kind']} {r['path']}" for r in rows))
    return 0 if rows else 1


def bundle_from_source(args):
    source = pathlib.Path(args.source)
    out = pathlib.Path(args.out)
    if not source.exists() or not source.is_dir():
        print(f"missing source directory: {source}", file=sys.stderr); return 1
    docs = _iter_source_docs(source)
    if not docs:
        print(f"no supported docs found under {source}", file=sys.stderr); return 1
    title = args.title or source.name.replace("-", " ").replace("_", " ").title()
    canonical = args.canonical_url or f"https://example.invalid/{slugify(title)}/"
    primary = next((p for p in docs if p.name.lower() == "readme.md"), docs[0])
    rel_docs = [p.relative_to(source).as_posix() for p in docs]
    openapi = next((p for p in docs if p.name.lower() in {"openapi.yaml", "openapi.yml", "swagger.yaml", "swagger.yml"}), None)
    task_type = "api_docs_handoff" if openapi else "docs_to_agent_bundle"
    primary_task = args.primary_task or f"Read the source documents for {title}, extract the useful facts, cite source files, and report missing checks."
    if args.dry_run:
        payload = {"status":"ok", "source": str(source), "would_write": str(out), "title": title, "doc_count": len(docs), "primary_doc": primary.relative_to(source).as_posix(), "task_type": task_type}
        print(json.dumps(payload, indent=2)); return 0
    if out.exists() and not args.force:
        print(f"output exists; use --force: {out}", file=sys.stderr); return 1
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    # Copy original source docs for auditability.
    src_out = out / "source"
    for p in docs:
        dest = src_out / p.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
    primary_excerpt = _read_excerpt(primary)
    write(out/"README.md", f"# {title}\n\nGenerated by AgentPress from `{source}`.\n\nPrimary source: `source/{primary.relative_to(source).as_posix()}`.\n\n## Source preview\n\n```\n{primary_excerpt}\n```\n\n## Agent use\n\nStart with `AGENT_ENTRYPOINT.md`, then inspect `source-map.json`, `agent-task-card.json`, `allowed-actions.json`, and the copied files under `source/`.\n")
    write(out/"AGENT_ENTRYPOINT.md", f"# {title} — Agent Entry Point\n\n## Primary task\n\n{primary_task}\n\n## Input contract\n\nProvide the question, target source files, and any freshness requirements.\n\n## Expected output schema\n\nReturn JSON with `decision`, `reasons`, `verified_sources`, `missing_checks`, `confidence`, and `disclaimer`.\n\n## Source files\n\n" + "\n".join(f"- `source/{r}`" for r in rel_docs) + "\n\n## Safety\n\nAllowed actions are local read, summarize, cite, transform, validate, create patch suggestions, and inspect allowed-actions safety boundaries. External writes, credential access, payments, production changes, and account actions are prohibited without explicit human approval.\n")
    card = _task_card(title, canonical, task_type, primary_task)
    card["input_contract"] = {"required": ["question_or_task"], "optional": ["target_files", "freshness_requirement", "output_format"]}
    card["primary_assets"] = ["AGENT_ENTRYPOINT.md", "source-map.json", "source/", "allowed-actions.json"]
    card["allowed_actions"] = ["read", "summarize", "cite", "transform", "validate", "create_patch_suggestion"]
    card["prohibited_actions"] = ["external_write", "credential_access", "payment", "production_change", "bypass_auth", "mass_distribution"]
    write(out/"agent-task-card.json", json.dumps(card, indent=2, ensure_ascii=False) + "\n")
    source_entries = []
    claims = []
    for i, p in enumerate(docs, 1):
        rel = p.relative_to(source).as_posix()
        b = p.read_bytes()
        source_entries.append({"id": f"src-{i:03d}", "path": f"source/{rel}", "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b), "role": "source_document"})
        claims.append({"claim": f"Source document available: {rel}", "source_ids": [f"src-{i:03d}"], "confidence": "source_file_present"})
    schema_claims = []
    for i, p in enumerate(docs, 1):
        rel = p.relative_to(source).as_posix()
        schema_claims.append({
            "claim_id": f"claim-{i:03d}",
            "claim": f"Source document available: {rel}",
            "confidence": "source_file_present",
            "sources": [{"title": rel, "url_or_path": f"source/{rel}", "retrieved_or_updated_at": _utc_now(), "evidence_type": "local_file_snapshot"}],
            "freshness_window_days": args.max_stale_days,
            "kill_criteria": ["source file missing", "hash mismatch", "content no longer supports the answer"]
        })
    source_map = {"schema_version":"1.0", "publication": title, "canonical_url": canonical, "source_files": source_entries, "claims": schema_claims, "verification_notes": ["Generated from local source files; agents must verify claims before external use."]}
    write(out/"source-map.json", json.dumps(source_map, indent=2, ensure_ascii=False) + "\n")
    freshness = {"schema_version":"1.0", "publication": title, "generated_at": _utc_now(), "last_reviewed_at": _utc_now(), "refresh_policy": "Regenerate this AgentPress bundle from the source directory after source changes.", "default_freshness_window_days": args.max_stale_days, "stale_zones": ["API paths", "error models", "examples", "source file mtimes"]}
    write(out/"freshness.json", json.dumps(freshness, indent=2) + "\n")
    allowed = {"schema_version":"1.0", "allowed": card["allowed_actions"], "requires_human_approval": ["external_write", "production_change", "payment", "credential_access"], "prohibited": card["prohibited_actions"], "notes": "This generated bundle is read-only coordination material."}
    write(out/"allowed-actions.json", json.dumps(allowed, indent=2) + "\n")
    write(out/"citation-policy.md", "# Citation Policy\n\nCite copied files under `source/` by path and source id from `source-map.json`. Mark unverified or stale claims explicitly.\n")
    write(out/"disclaimer.md", "# Disclaimer\n\nGenerated AgentPress bundle for agent reading, validation, and transformation. Not authorization for external writes, account actions, credential access, payments, or production changes.\n")
    write(out/"CITATION.cff", f"cff-version: 1.2.0\ntitle: {title}\nmessage: Cite source files listed in source-map.json.\n")
    write(out/"llms.txt", f"# {title}\n\nAgentPress bundle generated from local source docs.\n\nStart: AGENT_ENTRYPOINT.md\nTask card: agent-task-card.json\nSource map: source-map.json\nAllowed actions: allowed-actions.json\n\nSource files:\n" + "\n".join(f"- source/{r}" for r in rel_docs) + "\n")
    ingest = {"schema_version":"1.0", "name": title, "canonical_url": canonical, "entrypoint": canonical_join(canonical, "AGENT_ENTRYPOINT.md"), "llms_txt": canonical_join(canonical, "llms.txt"), "task_card": canonical_join(canonical, "agent-task-card.json"), "source_map": canonical_join(canonical, "source-map.json"), "allowed_actions": canonical_join(canonical, "allowed-actions.json"), "citation_policy": canonical_join(canonical, "citation-policy.md"), "disclaimer": canonical_join(canonical, "disclaimer.md"), "target_agents": ["coding_agent", "rag_agent", "browser_agent", "research_agent", "eval_agent"], "safety": allowed}
    write(out/".well-known/ai-ingestion.json", json.dumps(ingest, indent=2) + "\n")
    write(out/"sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f"  <url><loc>{canonical_join(canonical, asset)}</loc></url>\n" for asset in ["", "AGENT_ENTRYPOINT.md", "agent-task-card.json", "source-map.json", "llms.txt"]) + "</urlset>\n")
    write(out/"evals/smoke.jsonl", json.dumps({"input":"What source files are available?", "expected":"answer cites source-map.json and copied source paths"}) + "\n")
    if openapi:
        write(out/"openapi-detected.json", json.dumps({"detected": True, "path": f"source/{openapi.relative_to(source).as_posix()}", "agent_instruction": "Use this OpenAPI file to infer endpoints and required parameters before answering API questions."}, indent=2) + "\n")
    code, errors, warnings = audit_root(out, strict=True)
    total, detail = score_value(out)
    payload = {"status":"ok" if code == 0 else "fail", "source": str(source), "out": str(out), "title": title, "doc_count": len(docs), "score": total, "errors": errors, "warnings": warnings}
    print(json.dumps(payload, indent=2))
    if args.strict and warnings:
        return 1
    return code


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _short_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _csv_list(value, default=None):
    if value is None or value == "":
        return list(default or [])
    return [x.strip() for x in value.split(",") if x.strip()]


def _load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _detect_message_kind(payload: dict) -> tuple[str, str]:
    if "request_id" in payload and "needed_capability" in payload and "requester" in payload:
        return "agent_request", "agent-request-v1.schema.json"
    if "response_id" in payload and "responder" in payload:
        return "agent_response", "agent-response-v1.schema.json"
    if "thread_id" in payload and "messages" in payload:
        return "agent_thread", "agent-thread-v1.schema.json"
    if "message_id" in payload and "message_type" in payload:
        return "agent_message", "agent-message-v1.schema.json"
    return "unknown", ""


def _validate_message_payload(payload: dict, label: str = "message") -> tuple[str, list[str]]:
    kind, schema_file = _detect_message_kind(payload)
    if kind == "unknown":
        return kind, [f"{label}: unknown AgentPress message kind"]
    errors = _schema_required_errors(payload, schema_root() / schema_file, label)
    return kind, errors


def message_create_request(args):
    payload = {
        "schema_version": "1.0",
        "request_id": args.request_id or _short_id("req"),
        "requester": {"type": "agent", "id": args.requester_id},
        "needed_capability": args.capability,
        "task": args.task,
        "context_urls": _csv_list(args.context_urls),
        "required_sources": _csv_list(args.required_sources),
        "allowed_actions": _csv_list(args.allowed_actions, ["read", "validate", "summarize"]),
        "requires_human_approval": _csv_list(args.requires_human_approval, ["external_write", "production_change", "payment", "credential_access"]),
        "prohibited_actions": _csv_list(args.prohibited_actions, ["credential_access", "payment", "production_change", "bypass_auth"]),
        "output_schema": args.output_schema,
        "priority": args.priority,
        "deadline_utc": args.deadline_utc,
        "created_utc": _utc_now(),
    }
    _, errors = _validate_message_payload(payload, "request")
    if errors:
        print(json.dumps({"status":"fail", "errors": errors}, indent=2)); return 1
    out = pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status":"ok", "kind":"agent_request", "path": str(out), "request_id": payload["request_id"]}, indent=2))
    return 0


def message_route(args):
    directory = pathlib.Path(args.directory)
    idx = _load_json(directory)
    capability = args.capability
    agent_ids = idx.get("capabilities", {}).get(capability, [])
    agents = []
    for agent_id in agent_ids:
        meta = idx.get("agents", {}).get(agent_id, {})
        agents.append({"agent_id": agent_id, **meta})
    payload = {"status":"ok" if agents else "no_route", "capability": capability, "directory": str(directory), "agent_count": len(agents), "agents": agents}
    print(json.dumps(payload, indent=2) if args.json else "\n".join(a["agent_id"] for a in agents))
    return 0 if agents else 1


def message_create_response(args):
    request = _load_json(pathlib.Path(args.request))
    result_inline = {}
    if args.result_inline:
        result_inline = json.loads(args.result_inline)
    payload = {
        "schema_version": "1.0",
        "response_id": args.response_id or _short_id("res"),
        "request_id": request["request_id"],
        "responder": {"agent_id": args.responder_id, "capability_match": request.get("needed_capability", ""), "confidence_score": args.confidence},
        "status": args.status,
        "result_bundle_url": args.result_bundle or "",
        "result_inline": result_inline,
        "sources_used": _csv_list(args.sources_used),
        "missing_checks": _csv_list(args.missing_checks),
        "created_utc": _utc_now(),
        "safety": {
            "actions_taken": _csv_list(args.actions_taken, ["read", "validate"]),
            "requires_human_approval": request.get("requires_human_approval", []),
            "prohibited_actions_not_taken": request.get("prohibited_actions", []),
        },
    }
    _, errors = _validate_message_payload(payload, "response")
    if errors:
        print(json.dumps({"status":"fail", "errors": errors}, indent=2)); return 1
    out = pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status":"ok", "kind":"agent_response", "path": str(out), "response_id": payload["response_id"]}, indent=2))
    return 0


def message_validate(args):
    payload = _load_json(pathlib.Path(args.path))
    kind, errors = _validate_message_payload(payload, pathlib.Path(args.path).name)
    result = {"status":"ok" if not errors else "fail", "kind": kind, "path": args.path, "errors": errors}
    print(json.dumps(result, indent=2) if args.json else result["status"])
    return 0 if not errors else 1


def message_thread_create(args):
    request = _load_json(pathlib.Path(args.request))
    payload = {"schema_version":"1.0", "thread_id": args.thread_id or _short_id("thr"), "request_id": request["request_id"], "created_utc": _utc_now(), "messages": [request], "safety": {"static_site_safe": True, "external_side_effects": "not_authorized"}}
    _, errors = _validate_message_payload(payload, "thread")
    if errors:
        print(json.dumps({"status":"fail", "errors": errors}, indent=2)); return 1
    out = pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status":"ok", "kind":"agent_thread", "path": str(out), "thread_id": payload["thread_id"], "message_count": len(payload["messages"])}, indent=2))
    return 0


def message_thread_append(args):
    thread = _load_json(pathlib.Path(args.thread))
    message = _load_json(pathlib.Path(args.message))
    _, msg_errors = _validate_message_payload(message, "append_message")
    if msg_errors:
        print(json.dumps({"status":"fail", "errors": msg_errors}, indent=2)); return 1
    thread.setdefault("messages", []).append(message)
    thread["updated_utc"] = _utc_now()
    _, errors = _validate_message_payload(thread, "thread")
    if errors:
        print(json.dumps({"status":"fail", "errors": errors}, indent=2)); return 1
    out = pathlib.Path(args.out or args.thread); out.write_text(json.dumps(thread, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status":"ok", "kind":"agent_thread", "path": str(out), "message_count": len(thread["messages"])}, indent=2))
    return 0




def handoff_create(args):
    payload={"schema_version":"1.0","handoff_id":args.handoff_id or _short_id("handoff"),"from_agent":args.from_agent,"to_agent":args.to_agent,"capability":args.capability,"context_ref":args.context,"partial_response_ref":args.partial_response,"instructions":args.instructions,"parent_handoff_id":args.parent_handoff_id,"created_utc":_utc_now(),"safety":{"allowed_actions":["read","validate","summarize","continue_work","create_response"],"requires_human_approval":["external_write","production_change","payment","credential_access"],"prohibited":["credential_access","private_data_extraction","impersonation","spam"]}}
    errors=_schema_required_errors(payload, schema_root()/"handoff-v1.schema.json", "handoff")
    if errors: print(json.dumps({"status":"fail","errors":errors},indent=2)); return 1
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"ok","handoff_id":payload["handoff_id"],"out":str(out)},indent=2)); return 0


def handoff_validate(args):
    path=pathlib.Path(args.path); payload=json.loads(path.read_text(encoding="utf-8"))
    errors=_schema_required_errors(payload, schema_root()/"handoff-v1.schema.json", path.name)
    for ref_key in ["context_ref","partial_response_ref"]:
        ref=payload.get(ref_key)
        if ref and not pathlib.Path(ref).exists(): errors.append(f"{ref_key} missing local file: {ref}")
    result={"status":"ok" if not errors else "fail","path":str(path),"handoff_id":payload.get("handoff_id"),"from_agent":payload.get("from_agent"),"to_agent":payload.get("to_agent"),"errors":errors}
    print(json.dumps(result,indent=2) if args.json else result["status"]); return 0 if not errors else 1


def receipt_create(args):
    handoff=json.loads(pathlib.Path(args.handoff).read_text(encoding="utf-8"))
    evidence={"handoff":args.handoff,"response":args.response,"notes":args.notes or ""}
    if args.response and pathlib.Path(args.response).exists():
        evidence["response_sha256"]=hashlib.sha256(pathlib.Path(args.response).read_bytes()).hexdigest()
    payload={"schema_version":"1.0","receipt_id":args.receipt_id or _short_id("receipt"),"handoff_id":handoff.get("handoff_id"),"agent_id":args.agent_id,"status":args.status,"created_utc":_utc_now(),"evidence":evidence,"next_actions":_csv_list(args.next_actions)}
    errors=_schema_required_errors(payload, schema_root()/"receipt-v1.schema.json", "receipt")
    if errors: print(json.dumps({"status":"fail","errors":errors},indent=2)); return 1
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"ok","receipt_id":payload["receipt_id"],"out":str(out)},indent=2)); return 0


def receipt_validate(args):
    path=pathlib.Path(args.path); payload=json.loads(path.read_text(encoding="utf-8"))
    errors=_schema_required_errors(payload, schema_root()/"receipt-v1.schema.json", path.name)
    result={"status":"ok" if not errors else "fail","path":str(path),"receipt_id":payload.get("receipt_id"),"errors":errors}
    print(json.dumps(result,indent=2) if args.json else result["status"]); return 0 if not errors else 1


def _comms_root(path: str) -> pathlib.Path:
    return pathlib.Path(path)


def message_inbox_init(args):
    root=_comms_root(args.dir)
    for rel in ["agents", "messages", "responses", "threads"]:
        (root/rel).mkdir(parents=True, exist_ok=True)
    reg=root/"registry.json"
    if not reg.exists():
        reg.write_text(json.dumps({"schema_version":"2026-05-03.agentpress-static-inbox.v1", "agents":{}, "capabilities":{}}, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status":"ok", "dir":str(root), "registry":str(reg)}, indent=2))
    return 0


def _load_registry(root: pathlib.Path) -> dict:
    reg=root/"registry.json"
    if not reg.exists():
        with contextlib.redirect_stdout(io.StringIO()):
            message_inbox_init(argparse.Namespace(dir=str(root)))
    return json.loads(reg.read_text(encoding="utf-8"))


def _save_registry(root: pathlib.Path, data: dict):
    (root/"registry.json").write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")


def message_register(args):
    root=_comms_root(args.dir)
    with contextlib.redirect_stdout(io.StringIO()):
        with contextlib.redirect_stdout(io.StringIO()):
            message_inbox_init(argparse.Namespace(dir=str(root)))
    reg=_load_registry(root)
    caps=_csv_list(args.capabilities)
    agent={"agent_id":args.agent_id, "capabilities":caps, "registered_utc":_utc_now(), "inbox":f"agents/{args.agent_id}/inbox", "outbox":f"agents/{args.agent_id}/outbox"}
    reg.setdefault("agents", {})[args.agent_id]=agent
    reg.setdefault("capabilities", {})
    for c in caps:
        reg["capabilities"].setdefault(c, [])
        if args.agent_id not in reg["capabilities"][c]: reg["capabilities"][c].append(args.agent_id)
    _save_registry(root, reg)
    for rel in [f"agents/{args.agent_id}/inbox/pending", f"agents/{args.agent_id}/inbox/claimed", f"agents/{args.agent_id}/inbox/completed", f"agents/{args.agent_id}/outbox"]:
        (root/rel).mkdir(parents=True, exist_ok=True)
    print(json.dumps({"status":"ok", "agent_id":args.agent_id, "capabilities":caps}, indent=2))
    return 0


def _message_delivery_id(request: dict, to_agent: str) -> str:
    rid=request.get("request_id") or _short_id("req")
    return f"{rid}--to--{slugify(to_agent)}"


def message_send(args):
    root=_comms_root(args.dir); request=_load_json(pathlib.Path(args.request)); kind, errors=_validate_message_payload(request, "request")
    if errors or kind != "agent_request":
        print(json.dumps({"status":"fail", "errors":errors or ["message must be agent_request"]}, indent=2)); return 1
    reg=_load_registry(root)
    if args.to not in reg.get("agents", {}):
        print(json.dumps({"status":"fail", "errors":[f"unknown agent: {args.to}"]}, indent=2)); return 1
    delivery_id=_message_delivery_id(request, args.to)
    env={"schema_version":"2026-05-03.agentpress-delivery.v1", "delivery_id":delivery_id, "to_agent":args.to, "state":"pending", "created_utc":_utc_now(), "request":request}
    dest=root/f"agents/{args.to}/inbox/pending/{delivery_id}.json"; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(json.dumps(env, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status":"ok", "delivery_id":delivery_id, "path":str(dest)}, indent=2))
    return 0


def message_broadcast(args):
    root=_comms_root(args.dir); reg=_load_registry(root)
    targets=reg.get("capabilities", {}).get(args.capability, [])
    sent=[]; errors=[]
    for agent_id in targets:
        code=message_send(argparse.Namespace(dir=str(root), request=args.request, to=agent_id))
        if code == 0: sent.append(agent_id)
        else: errors.append(agent_id)
    print(json.dumps({"status":"ok" if sent and not errors else "fail", "capability":args.capability, "sent":sent, "errors":errors}, indent=2))
    return 0 if sent and not errors else 1


def message_inbox_check(args):
    root=_comms_root(args.dir); base=root/f"agents/{args.agent_id}/inbox"
    rows=[]
    for state in ["pending", "claimed", "completed"]:
        for p in sorted((base/state).glob("*.json")) if (base/state).exists() else []:
            try: d=json.loads(p.read_text(encoding="utf-8"))
            except Exception: d={}
            rows.append({"state":state, "delivery_id":d.get("delivery_id", p.stem), "path":str(p), "request_id":d.get("request", {}).get("request_id"), "capability":d.get("request", {}).get("needed_capability")})
    print(json.dumps({"status":"ok", "agent_id":args.agent_id, "count":len(rows), "messages":rows}, indent=2) if args.json else "\n".join(r["path"] for r in rows))
    return 0


def message_claim(args):
    root=_comms_root(args.dir); pending=root/f"agents/{args.agent_id}/inbox/pending/{args.message_id}.json"; claimed=root/f"agents/{args.agent_id}/inbox/claimed/{args.message_id}.json"
    if not pending.exists():
        print(json.dumps({"status":"fail", "errors":[f"pending message not found: {args.message_id}"]}, indent=2)); return 1
    claimed.parent.mkdir(parents=True, exist_ok=True)
    data=json.loads(pending.read_text(encoding="utf-8")); data["state"]="claimed"; data["claimed_by"]=args.agent_id; data["claimed_utc"]=_utc_now()
    claimed.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8"); pending.unlink()
    print(json.dumps({"status":"ok", "delivery_id":args.message_id, "path":str(claimed)}, indent=2))
    return 0


def message_complete(args):
    root=_comms_root(args.dir); claimed=root/f"agents/{args.agent_id}/inbox/claimed/{args.message_id}.json"; complete=root/f"agents/{args.agent_id}/inbox/completed/{args.message_id}.json"
    if not claimed.exists():
        print(json.dumps({"status":"fail", "errors":[f"claimed message not found: {args.message_id}"]}, indent=2)); return 1
    response=_load_json(pathlib.Path(args.response)); kind, errors=_validate_message_payload(response, "response")
    if errors or kind != "agent_response":
        print(json.dumps({"status":"fail", "errors":errors or ["response must be agent_response"]}, indent=2)); return 1
    data=json.loads(claimed.read_text(encoding="utf-8")); data["state"]="completed"; data["completed_utc"]=_utc_now(); data["response"]=response
    complete.parent.mkdir(parents=True, exist_ok=True); complete.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8"); claimed.unlink()
    outbox=root/f"agents/{args.agent_id}/outbox/{args.message_id}-response.json"; outbox.parent.mkdir(parents=True, exist_ok=True); outbox.write_text(json.dumps(response, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status":"ok", "delivery_id":args.message_id, "path":str(complete), "outbox":str(outbox)}, indent=2))
    return 0


def message_agents(args):
    root=_comms_root(args.dir); reg=_load_registry(root)
    print(json.dumps({"status":"ok", "count":len(reg.get("agents", {})), "agents":reg.get("agents", {}), "capabilities":reg.get("capabilities", {})}, indent=2) if args.json else "\n".join(reg.get("agents", {}).keys()))
    return 0







def discover_agentpress(args):
    if getattr(args, 'self_register', False):
        return mesh_self_register(args)
    if not args.url:
        print(json.dumps({"status":"fail","errors":["url required unless --self-register"]},indent=2)); return 2
    base=args.url
    if base.endswith('/llms.txt'):
        base=base[:-len('llms.txt')]
    base=base.rstrip('/')+'/'
    assets=[
        'llms.txt',
        '.well-known/agentpress.json',
        'agentpress/tools/agentpress-tools.json',
        'agentpress/releases/release-index.json',
        'agentpress/feeds/contract-feed.json',
        'agentpress/search/search-index.json',
    ]
    fetched={}; errors=[]
    for rel in assets:
        url=urljoin(base, rel)
        try:
            with urlopen(url, timeout=args.timeout) as resp:
                raw=resp.read().decode('utf-8', errors='replace')
            if rel.endswith('.json'):
                fetched[rel]=json.loads(raw)
            else:
                fetched[rel]={'text_excerpt': raw[:1200], 'bytes': len(raw.encode())}
        except Exception as e:
            errors.append({'asset':rel,'url':url,'error':str(e)})
    tools=[]
    t=fetched.get('agentpress/tools/agentpress-tools.json')
    if isinstance(t, dict):
        tools=[x.get('name') for x in t.get('tools', []) if x.get('name')]
    release=fetched.get('agentpress/releases/release-index.json') if isinstance(fetched.get('agentpress/releases/release-index.json'), dict) else {}
    contract=fetched.get('agentpress/feeds/contract-feed.json') if isinstance(fetched.get('agentpress/feeds/contract-feed.json'), dict) else {}
    payload={
        'schema_version':'1.0',
        'status':'ok' if tools else 'partial',
        'discovered_utc':_utc_now(),
        'agentpress_url':base,
        'compatible':bool(tools),
        'tool_count':len(tools),
        'tools':tools,
        'release': release.get('latest', {}),
        'contract_version': contract.get('current_contract_version'),
        'assets_found': sorted(fetched.keys()),
        'errors': errors,
        'next_actions':['install from release-index','run self-test','generate landing receipt','submit proof pack'] if tools else ['inspect errors','try llms.txt or well-known manifest directly']
    }
    if args.out:
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding='utf-8')
    if args.registry:
        reg_path=pathlib.Path(args.registry); reg_path.parent.mkdir(parents=True,exist_ok=True)
        if reg_path.exists():
            try: reg=json.loads(reg_path.read_text(encoding='utf-8'))
            except Exception: reg={}
        else: reg={}
        reg.setdefault('schema_version','1.0'); reg.setdefault('generated_utc',_utc_now()); reg.setdefault('agents', [])
        reg['agents']=[a for a in reg.get('agents', []) if a.get('agentpress_url') != base]
        reg['agents'].append({'agentpress_url':base,'discovered_utc':payload['discovered_utc'],'compatible':payload['compatible'],'tool_count':payload['tool_count'],'contract_version':payload.get('contract_version'),'release_version':payload.get('release',{}).get('version')})
        reg['generated_utc']=_utc_now(); reg['agent_count']=len(reg['agents'])
        reg_path.write_text(json.dumps(reg,indent=2)+"\n",encoding='utf-8')
        payload['registry']=str(reg_path)
    print(json.dumps(payload,indent=2) if args.json else (str(args.out) if args.out else payload['status']))
    return 0 if payload['compatible'] else 1

def mesh_self_register(args):
    canonical=(args.canonical_url or CANONICAL_BASE_URL).rstrip('/')+'/'
    agent_id=args.agent_id or ('agentpress-'+urlparse(canonical).netloc.replace('.','-').replace(':','-'))
    # Discover canonical URL first to extract live capabilities when possible.
    tmp=pathlib.Path('/tmp')/f"agentpress-self-register-{slugify(agent_id)}.json"
    dargs=argparse.Namespace(url=canonical,out=str(tmp),registry=None,timeout=args.timeout,json=True,self_register=False,canonical_url=canonical,agent_id=agent_id)
    with contextlib.redirect_stdout(io.StringIO()):
        code=discover_agentpress(dargs)
    discovery=json.loads(tmp.read_text(encoding='utf-8')) if tmp.exists() else {'compatible':False,'tools':[],'release':{},'contract_version':None,'errors':['discovery failed']}
    registry_path=pathlib.Path(args.registry or 'agentpress/mesh/known-agents.json')
    if registry_path.exists():
        try: reg=json.loads(registry_path.read_text(encoding='utf-8'))
        except Exception: reg={}
    else: reg={}
    reg.setdefault('schema_version','1.0'); reg.setdefault('agents', [])
    entry={'agent_id':agent_id,'agentpress_url':canonical,'canonical_url':canonical,'registered_utc':_utc_now(),'discovery_method':'self-registration','compatible':bool(discovery.get('compatible')),'tool_count':discovery.get('tool_count',0),'tools':discovery.get('tools',[]),'tools_url':urljoin(canonical,'agentpress/tools/agentpress-tools.json'),'release_url':urljoin(canonical,'agentpress/releases/release-index.json'),'contract_feed_url':urljoin(canonical,'agentpress/feeds/contract-feed.json'),'contract_version':discovery.get('contract_version'),'release_version':(discovery.get('release') or {}).get('version'),'self_test_status':'not_submitted','trust_tier':'self_registered'}
    reg['agents']=[a for a in reg.get('agents', []) if a.get('agent_id') != agent_id and a.get('agentpress_url') != canonical and a.get('canonical_url') != canonical]
    reg['agents'].append(entry); reg['agent_count']=len(reg['agents']); reg['generated_utc']=_utc_now(); reg['note']='Static registry of AgentPress-compatible nodes discovered or self-registered by agents.'
    registry_path.parent.mkdir(parents=True,exist_ok=True); registry_path.write_text(json.dumps(reg,indent=2)+"\n",encoding='utf-8')
    payload={'status':'registered','agent_id':agent_id,'canonical_url':canonical,'registry':str(registry_path),'compatible':entry['compatible'],'tool_count':entry['tool_count']}
    print(json.dumps(payload,indent=2) if args.json else f"registered {agent_id} -> {registry_path}")
    return 0 if entry['compatible'] else 1


def submission_pack(args):
    receipt=pathlib.Path(args.receipt)
    errors=[]
    if not receipt.exists(): errors.append(f"missing receipt: {receipt}")
    data={}
    if not errors:
        try: data=json.loads(receipt.read_text(encoding="utf-8"))
        except Exception as e: errors.append(f"receipt parse failed: {e}")
    if errors:
        print(json.dumps({"status":"fail","errors":errors},indent=2)); return 1
    out=pathlib.Path(args.out); out.mkdir(parents=True,exist_ok=True)
    kind="landing" if data.get("landing_id") or data.get("schema_version")=="1.0" and data.get("discovery_channel") else "receipt"
    agent_id=data.get("agent_id", "unknown-agent")
    safe=slugify(agent_id)
    receipt_out=out/f"{safe}-{kind}.json"
    receipt_out.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    title=f"AgentPress {kind} receipt: {agent_id}"
    issue=f"""# {title}\n\nThis is an opt-in AgentPress proof submission.\n\n## Agent\n- Agent ID: `{agent_id}`\n- Runtime: `{data.get('runtime','')}`\n- Discovery channel: `{data.get('discovery_channel','')}`\n- Capabilities: `{', '.join(data.get('capabilities') or ([data.get('capability')] if data.get('capability') else []))}`\n\n## Receipt file\nAttach or commit:\n\n`agentpress/landing/{receipt_out.name}`\n\n## Validation\n\n```bash\npython3 scripts/agentpress.py landing-index agentpress/landing --out agentpress/landing/agent-landing-index.json --json\npython3 scripts/agentpress.py reputation-index --landing-dir agentpress/landing --self-test-dir agentpress/self-test --receipt-dir agentpress/receipts --out agentpress/reputation/reputation-index.json --json\npython3 scripts/validate_agentpress_assets.py\n```\n\n## Privacy\nThis submission should contain no IP address, user-agent, secrets, private prompts, or credential material.\n"""
    (out/"github-issue.md").write_text(issue,encoding="utf-8")
    pr=f"""# AgentPress proof submission pack\n\n## Submit by PR\n\n1. Copy `{receipt_out.name}` to `agentpress/landing/{receipt_out.name}`.\n2. Rebuild indexes:\n\n```bash\npython3 scripts/agentpress.py landing-index agentpress/landing --out agentpress/landing/agent-landing-index.json --json\npython3 scripts/agentpress.py reputation-index --landing-dir agentpress/landing --self-test-dir agentpress/self-test --receipt-dir agentpress/receipts --out agentpress/reputation/reputation-index.json --json\npython3 scripts/validate_agentpress_assets.py\n```\n\n3. Open PR titled: `{title}`.\n\n## Submit by issue\n\nPaste `github-issue.md` into a GitHub issue and attach `{receipt_out.name}`.\n"""
    (out/"README.md").write_text(pr,encoding="utf-8")
    manifest={"schema_version":"1.0","status":"ok","generated_utc":_utc_now(),"agent_id":agent_id,"kind":kind,"files":[str(receipt_out),str(out/"github-issue.md"),str(out/"README.md")],"submit_by_pr":f"agentpress/landing/{receipt_out.name}","validation_commands":["python3 scripts/agentpress.py landing-index agentpress/landing --out agentpress/landing/agent-landing-index.json --json","python3 scripts/agentpress.py reputation-index --landing-dir agentpress/landing --self-test-dir agentpress/self-test --receipt-dir agentpress/receipts --out agentpress/reputation/reputation-index.json --json","python3 scripts/validate_agentpress_assets.py"]}
    (out/"submission-pack.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"ok","out":str(out),"files":len(manifest["files"])+1},indent=2) if args.json else str(out))
    return 0


def reputation_index(args):
    agents={}
    def rec(agent_id):
        return agents.setdefault(agent_id, {"agent_id":agent_id,"runtime":"","capabilities":set(),"score":0,"evidence":{"landing_receipts":0,"self_tests":0,"self_test_passes":0,"self_test_total":0,"handoff_receipts":0,"completed_receipts":0,"files":[]}})
    # landing receipts
    ldir=pathlib.Path(args.landing_dir)
    if ldir.exists():
        for p in sorted(ldir.glob("*.json")):
            if "index" in p.name: continue
            try: data=json.loads(p.read_text(encoding="utf-8"))
            except Exception: continue
            aid=data.get("agent_id")
            if not aid: continue
            r=rec(aid); r["runtime"]=r.get("runtime") or data.get("runtime",""); r["capabilities"].update(data.get("capabilities",[])); r["score"]+=20; r["evidence"]["landing_receipts"]+=1; r["evidence"]["files"].append(str(p))
    # self-test json/jsonl
    sdir=pathlib.Path(args.self_test_dir)
    if sdir.exists():
        paths=list(sdir.glob("*.jsonl"))+list(sdir.glob("*.json"))
        for p in sorted(paths):
            rows=[]
            try:
                text=p.read_text(encoding="utf-8")
                if p.suffix == ".jsonl": rows=[json.loads(line) for line in text.splitlines() if line.strip()]
                else:
                    data=json.loads(text); rows=data if isinstance(data,list) else data.get("results", [])
            except Exception: continue
            by_agent={}
            for row in rows:
                aid=row.get("agent_id");
                if aid: by_agent.setdefault(aid, []).append(row)
            for aid, ars in by_agent.items():
                r=rec(aid); total=len(ars); passed=sum(1 for x in ars if x.get("status")=="pass"); avg=sum(float(x.get("score",0)) for x in ars)/total if total else 0
                r["score"]+=min(50, avg*0.5); r["evidence"]["self_tests"]+=1; r["evidence"]["self_test_passes"]+=passed; r["evidence"]["self_test_total"]+=total; r["evidence"]["files"].append(str(p))
    # handoff receipts
    rdir=pathlib.Path(args.receipt_dir)
    if rdir.exists():
        for p in sorted(rdir.glob("*.json")):
            try: data=json.loads(p.read_text(encoding="utf-8"))
            except Exception: continue
            aid=data.get("agent_id")
            if not aid: continue
            r=rec(aid); r["score"]+=10; r["evidence"]["handoff_receipts"]+=1; r["evidence"]["completed_receipts"]+=1 if data.get("status")=="completed" else 0; r["evidence"]["files"].append(str(p))
    rows=[]
    for r in agents.values():
        r["capabilities"]=sorted(r["capabilities"]); r["score"]=round(min(100,r["score"]),2)
        r["trust_tier"]="verified" if r["score"]>=80 else ("provisional" if r["score"]>=40 else "landed")
        rows.append(r)
    rows=sorted(rows, key=lambda x:(-x["score"], x["agent_id"]))
    payload={"schema_version":"1.0","status":"ok","generated_utc":_utc_now(),"agent_count":len(rows),"agents":rows,"scoring":{"landing_receipt":"+20","self_test_average":"up to +50","handoff_receipt":"+10 each, capped at 100"},"privacy":"Evidence-derived from opt-in local artifacts; no hidden analytics."}
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"ok","out":str(out),"agent_count":len(rows)},indent=2) if args.json else str(out))
    return 0


def landing_receipt(args):
    caps=[]
    for c in args.capability or []:
        caps.extend(_csv_list(c))
    payload={"schema_version":"1.0","landing_id":args.landing_id or _short_id("landing"),"agent_id":args.agent_id,"runtime":args.runtime,"discovery_channel":args.discovery_channel,"capabilities":caps,"created_utc":_utc_now(),"privacy":{"no_ip":True,"no_user_agent":True,"no_secret_material":True,"contact":args.contact or ""},"evidence":{"agentpress_base":args.base_url,"submit_hint":"Open a PR or issue with this receipt, or add it to a landing registry directory."}}
    if args.self_test_ref:
        payload["self_test_ref"] = args.self_test_ref
    errors=_schema_required_errors(payload, schema_root()/"agent-landing-v1.schema.json", "landing_receipt")
    if errors: print(json.dumps({"status":"fail","errors":errors},indent=2)); return 1
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"ok","landing_id":payload["landing_id"],"out":str(out)},indent=2) if args.json else str(out))
    return 0


def landing_index(args):
    root=pathlib.Path(args.dir); receipts=[]; errors=[]
    for p in sorted(root.glob("*.json")) if root.exists() else []:
        if p.name == pathlib.Path(args.out).name or "index" in p.name or "schema" in p.name: continue
        try: data=json.loads(p.read_text(encoding="utf-8"))
        except Exception as e: errors.append(f"{p}: parse error {e}"); continue
        e=_schema_required_errors(data, schema_root()/"agent-landing-v1.schema.json", p.name)
        if e: errors.extend(e); continue
        public={k:data.get(k) for k in ["landing_id","agent_id","runtime","discovery_channel","capabilities","self_test_ref","created_utc"]}
        public["receipt_path"]=str(p)
        receipts.append(public)
    payload={"schema_version":"1.0","status":"ok" if not errors else "fail","generated_utc":_utc_now(),"receipt_count":len(receipts),"receipts":receipts,"errors":errors,"privacy":"Compiled from opt-in landing receipts only; no hidden tracking."}
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"out":str(out),"receipt_count":len(receipts),"errors":errors},indent=2) if args.json else str(out))
    return 0 if not errors else 1


def inbox_compile(args):
    root=pathlib.Path(args.inbox_dir); out=pathlib.Path(args.out); errors=[]
    if not root.exists(): errors.append(f"inbox dir missing: {root}")
    reg=_load_registry(root) if root.exists() else {"agents":{},"capabilities":{}}
    rows=[]
    counts={"pending":0,"claimed":0,"completed":0}
    for agent_id in sorted(reg.get("agents", {}).keys()):
        base=root/f"agents/{agent_id}/inbox"
        for state in ["pending","claimed","completed"]:
            for fp in sorted((base/state).glob("*.json")) if (base/state).exists() else []:
                try: d=json.loads(fp.read_text(encoding="utf-8"))
                except Exception as e:
                    d={"delivery_id":fp.stem,"parse_error":str(e)}
                req=d.get("request", {})
                row={"agent_id":agent_id,"state":state,"delivery_id":d.get("delivery_id",fp.stem),"request_id":req.get("request_id"),"capability":req.get("needed_capability"),"task":req.get("task"),"priority":req.get("priority"),"path":str(fp.relative_to(root)),"updated_utc":d.get("completed_utc") or d.get("claimed_utc") or d.get("created_utc")}
                rows.append(row); counts[state]=counts.get(state,0)+1
    payload={"schema_version":"1.0","status":"ok" if not errors else "fail","generated_utc":_utc_now(),"inbox_dir":str(root),"registry":{"agent_count":len(reg.get("agents",{})),"capability_count":len(reg.get("capabilities",{})),"agents":reg.get("agents",{}),"capabilities":reg.get("capabilities",{})},"counts":counts,"messages":rows,"errors":errors}
    out.mkdir(parents=True,exist_ok=True)
    (out/"inbox-index.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    # JSONL for agents that stream queue state
    with (out/"inbox-messages.jsonl").open("w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,sort_keys=True)+"\n")
    html_rows="\n".join(f"<tr><td>{html.escape(r.get('agent_id') or '')}</td><td>{html.escape(r.get('state') or '')}</td><td>{html.escape(r.get('capability') or '')}</td><td>{html.escape(r.get('priority') or '')}</td><td>{html.escape(r.get('delivery_id') or '')}</td><td>{html.escape((r.get('task') or '')[:160])}</td></tr>" for r in rows)
    page=f"""<!doctype html><meta charset='utf-8'><title>AgentPress Inbox Hub</title><style>body{{font-family:system-ui,sans-serif;margin:2rem;max-width:1100px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:.45rem;text-align:left}}th{{background:#f5f5f5}}code{{background:#f6f8fa;padding:.15rem .3rem}}</style><h1>AgentPress Inbox Hub</h1><p>Generated <code>{html.escape(payload['generated_utc'])}</code> from <code>{html.escape(str(root))}</code>.</p><p>Agents: <b>{payload['registry']['agent_count']}</b> · Pending: <b>{counts.get('pending',0)}</b> · Claimed: <b>{counts.get('claimed',0)}</b> · Completed: <b>{counts.get('completed',0)}</b></p><p>Machine files: <a href='inbox-index.json'>inbox-index.json</a> · <a href='inbox-messages.jsonl'>inbox-messages.jsonl</a></p><table><thead><tr><th>Agent</th><th>State</th><th>Capability</th><th>Priority</th><th>Delivery</th><th>Task</th></tr></thead><tbody>{html_rows}</tbody></table>"""
    (out/"index.html").write_text(page+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"out":str(out),"messages":len(rows),"counts":counts,"errors":errors},indent=2) if args.json else str(out))
    return 0 if not errors else 1


def message_command(args):
    if args.message_cmd == "create-request": return message_create_request(args)
    if args.message_cmd == "route": return message_route(args)
    if args.message_cmd == "create-response": return message_create_response(args)
    if args.message_cmd == "inbox-init": return message_inbox_init(args)
    if args.message_cmd == "register": return message_register(args)
    if args.message_cmd == "send": return message_send(args)
    if args.message_cmd == "broadcast": return message_broadcast(args)
    if args.message_cmd == "inbox-check": return message_inbox_check(args)
    if args.message_cmd == "claim": return message_claim(args)
    if args.message_cmd == "complete": return message_complete(args)
    if args.message_cmd == "agents": return message_agents(args)
    if args.message_cmd == "validate": return message_validate(args)
    if args.message_cmd == "thread-create": return message_thread_create(args)
    if args.message_cmd == "thread-append": return message_thread_append(args)
    print("unknown message command", file=sys.stderr); return 1


def eval_examples(args):
    root = pathlib.Path(args.root)
    examples = sorted(p for p in root.iterdir() if p.is_dir() and (p/"agent-task-card.json").exists()) if root.exists() else []
    total_rows = 0
    failures = []
    for ex in examples:
        eval_errors, count = _validate_eval_files(ex)
        total_rows += count
        failures.extend(eval_errors)
        if count == 0:
            failures.append(f"{ex}: no eval rows")
    if failures:
        for f in failures:
            print(f"error: {f}")
        return 1
    print(json.dumps({"status":"ok", "examples": len(examples), "eval_rows": total_rows}, indent=2))
    return 0


def check_registry(args):
    root = pathlib.Path(args.root)
    registry_path = pathlib.Path(args.registry)
    examples = sorted(p.name for p in root.iterdir() if p.is_dir() and (p/"agent-task-card.json").exists()) if root.exists() else []
    if not registry_path.exists():
        print(f"missing registry: {registry_path}")
        return 1
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    publications = registry.get("publications", [])
    slugs = sorted(p.get("slug") for p in publications)
    errors = []
    if registry.get("count") != len(publications):
        errors.append(f"registry count {registry.get('count')} != publications {len(publications)}")
    if slugs != examples:
        errors.append(f"registry slugs mismatch: examples={examples} registry={slugs}")
    if errors:
        for e in errors:
            print(f"error: {e}")
        return 1
    print(json.dumps({"status":"ok", "example_count": len(examples), "registry": str(registry_path)}, indent=2))
    return 0


def check_openapi(args):
    root = pathlib.Path(args.root)
    spec = pathlib.Path(args.openapi)
    if not spec.exists():
        print(f"missing OpenAPI spec: {spec}")
        return 1
    text = spec.read_text(encoding="utf-8")
    paths = []
    in_paths = False
    for line in text.splitlines():
        if line.startswith("paths:"):
            in_paths = True
            continue
        if in_paths:
            m = re.match(r"^  (/[^:]+):\s*$", line)
            if m:
                paths.append(m.group(1))
    errors = []
    for path in paths:
        rel = path.lstrip("/")
        local = root / rel
        if path.endswith("/") or path == "/":
            local = local / "index.html"
        if not local.exists():
            errors.append(f"OpenAPI path missing local asset: {path} -> {local}")
    if errors:
        for e in errors:
            print(f"error: {e}")
        return 1
    print(json.dumps({"status":"ok", "paths": len(paths), "openapi": str(spec)}, indent=2))
    return 0


def package_bundle(args):
    import hashlib, tarfile, zipfile
    root = pathlib.Path(args.root)
    out = pathlib.Path(args.out)
    if not root.exists():
        print(f"missing root: {root}", file=sys.stderr); return 1
    files = [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts]
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "zip":
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files: z.write(f, f.relative_to(root).as_posix())
    else:
        with tarfile.open(out, "w:gz") as t:
            for f in files: t.add(f, arcname=f.relative_to(root).as_posix())
    hashes = []
    for f in files:
        b=f.read_bytes(); hashes.append({"path": f.relative_to(root).as_posix(), "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)})
    hash_path = out.with_suffix(out.suffix + ".sha256.json")
    hash_path.write_text(json.dumps({"schema_version":"0.1","package":str(out),"count":len(hashes),"assets":hashes}, indent=2) + "\n")
    print(f"wrote {out}")
    print(f"wrote {hash_path}")
    return 0




ADAPTER_TYPES = ["codex", "claude", "gemini", "glm", "browser"]

def _adapter_entrypoint(agent_type: str) -> str:
    return f"""# AgentPress Quickstart for {agent_type}\n\nYou are an autonomous agent integrating with AgentPress. Use local CLI commands and machine-readable JSON.\n\n## Start here\n\n1. Fetch/search tools:\n   `python3 scripts/agentpress.py search \"bundle verify message self-test\" --json`\n2. Run self-test:\n   `python3 scripts/agentpress.py self-test --agent-id {agent_type}-agent --out /tmp/{agent_type}-agentpress-self-test.jsonl`\n3. Generate/verify a bundle:\n   `python3 scripts/agentpress.py bundle tests/fixtures/source-docs --out /tmp/{agent_type}-bundle --title \"{agent_type} Test Bundle\" --force`\n   `python3 scripts/agentpress.py verify /tmp/{agent_type}-bundle --json`\n4. Communicate through static inbox lifecycle when delegating work.\n\n## Safety\n\nNo credential access, payments, production changes, spam, impersonation, or private-data extraction without explicit human approval.\n"""


def _adapter_config(agent_type: str) -> dict:
    return {"schema_version":"1.0", "agent_type":agent_type, "agentpress_root":".", "default_commands":{"search":"python3 scripts/agentpress.py search <query> --json", "self_test":f"python3 scripts/agentpress.py self-test --agent-id {agent_type}-agent --out /tmp/{agent_type}-self-test.jsonl", "verify":"python3 scripts/agentpress.py verify <bundle> --json"}, "safety":{"requires_human_approval":["external_write","production_change","payment","credential_access"], "prohibited":["private_data_extraction","spam","impersonation"]}}



def _bundle_files(root: pathlib.Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts}


def _json_or_none(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except Exception:
        return None


def bundle_diff(args):
    a=pathlib.Path(args.bundle_a); b=pathlib.Path(args.bundle_b); errors=[]
    if not a.is_dir(): errors.append(f"bundle_a missing/not dir: {a}")
    if not b.is_dir(): errors.append(f"bundle_b missing/not dir: {b}")
    if errors:
        print(json.dumps({"status":"fail","errors":errors},indent=2)); return 1
    fa=_bundle_files(a); fb=_bundle_files(b)
    added=sorted(set(fb)-set(fa)); removed=sorted(set(fa)-set(fb)); modified=sorted(k for k in set(fa)&set(fb) if fa[k]!=fb[k])
    breaking=[]
    for required in AGENTPRESS_REQUIRED:
        if required in removed: breaking.append(f"required file removed: {required}")
    # contract-level checks
    card_a=_json_or_none(a/"agent-task-card.json") or {}; card_b=_json_or_none(b/"agent-task-card.json") or {}
    actions_a=_json_or_none(a/"allowed-actions.json") or {}; actions_b=_json_or_none(b/"allowed-actions.json") or {}
    fresh_a=_json_or_none(a/"freshness.json") or {}; fresh_b=_json_or_none(b/"freshness.json") or {}
    source_a=_json_or_none(a/"source-map.json") or {}; source_b=_json_or_none(b/"source-map.json") or {}
    contract_changes={}
    for name, va, vb in [("task_type", card_a.get("task_type"), card_b.get("task_type")), ("objective", card_a.get("objective"), card_b.get("objective")), ("output_contract", card_a.get("output_contract"), card_b.get("output_contract"))]:
        if va != vb: contract_changes[name]={"from":va,"to":vb}
    prohibited_a=set(actions_a.get("prohibited", actions_a.get("prohibited_actions", []))); prohibited_b=set(actions_b.get("prohibited", actions_b.get("prohibited_actions", [])))
    if prohibited_a != prohibited_b:
        contract_changes["prohibited_actions"]={"from":sorted(prohibited_a),"to":sorted(prohibited_b)}
        if not prohibited_b.issuperset(prohibited_a): breaking.append("prohibited action boundary loosened")
    claim_count_a=len(source_a.get("claims", [])); claim_count_b=len(source_b.get("claims", []))
    freshness_changed=fresh_a != fresh_b
    diff={"added_files":added,"removed_files":removed,"modified_files":modified,"contract_changes":contract_changes,"claim_count":{"from":claim_count_a,"to":claim_count_b},"freshness_changed":freshness_changed,"hashes":{"bundle_a":fa,"bundle_b":fb} if args.include_hashes else {}}
    total=len(added)+len(removed)+len(modified)+len(contract_changes)+(1 if freshness_changed else 0)
    verdict="identical" if total==0 else ("breaking_change" if breaking else "changed_non_breaking")
    payload={"schema_version":"1.0","status":"ok","bundle_a":str(a),"bundle_b":str(b),"generated_utc":_utc_now(),"changes":diff,"summary":{"total_changes":total,"breaking":bool(breaking),"breaking_reasons":breaking},"verdict":verdict}
    print(json.dumps(payload,indent=2) if args.json else verdict)
    return 0 if verdict != "breaking_change" or args.allow_breaking else 2


def upgrade_check(args):
    code_buf=io.StringIO()
    with contextlib.redirect_stdout(code_buf):
        code=bundle_diff(argparse.Namespace(bundle_a=args.current_bundle,bundle_b=args.latest_bundle,json=True,include_hashes=False,allow_breaking=True))
    payload=json.loads(code_buf.getvalue())
    payload["upgrade"]={"safe": payload.get("verdict") != "breaking_change", "recommendation": "upgrade" if payload.get("verdict") in ["identical","changed_non_breaking"] else "review_breaking_changes"}
    print(json.dumps(payload,indent=2) if args.json else payload["upgrade"]["recommendation"])
    return 0 if payload["upgrade"]["safe"] else 2


def adapter_quickstart(args):
    types = ADAPTER_TYPES if args.agent_type == "all" else [args.agent_type]
    out=pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    adapters=[]
    for t in types:
        if t not in ADAPTER_TYPES:
            print(json.dumps({"status":"fail", "errors":[f"unknown adapter type: {t}"]}, indent=2)); return 1
        d=out/t; d.mkdir(parents=True, exist_ok=True)
        entry={"codex":"CODEX.md","claude":"CLAUDE.md","gemini":"GEMINI.md","glm":"GLM.md","browser":"BROWSER_AGENT.md"}[t]
        config=f"{t}-agentpress-config.json"; tools=f"{t}-agentpress-tools.json"
        (d/entry).write_text(_adapter_entrypoint(t), encoding="utf-8")
        (d/config).write_text(json.dumps(_adapter_config(t), indent=2)+"\n", encoding="utf-8")
        tool_manifest = json.loads(pathlib.Path("agentpress/tools/agentpress-tools.json").read_text(encoding="utf-8")) if pathlib.Path("agentpress/tools/agentpress-tools.json").exists() else {"tools": []}
        (d/tools).write_text(json.dumps(tool_manifest, indent=2)+"\n", encoding="utf-8")
        st=d/"self-test.sh"
        st.write_text(f"#!/usr/bin/env bash\nset -euo pipefail\ncd \"$(dirname \"$0\")/../..\"\npython3 scripts/agentpress.py self-test --agent-id {t}-agent --out /tmp/{t}-agentpress-self-test.jsonl\npython3 scripts/agentpress.py search 'message route capability' --json >/tmp/{t}-agentpress-search.json\n", encoding="utf-8")
        st.chmod(0o755)
        adapters.append({"type":t,"dir":str(d),"entrypoint":entry,"config":config,"tools":tools,"self_test":"self-test.sh"})
    manifest={"schema_version":"1.0","generated_at":_utc_now(),"adapters":adapters,"safety":"local CLI only; no external side effects by default"}
    (out/"adapter-quickstart-manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status":"ok", "out":str(out), "adapter_count":len(adapters)}, indent=2) if args.json else f"wrote {len(adapters)} adapters to {out}")
    return 0


def adapter_quickstart_check(args):
    root=pathlib.Path(args.dir); manifest=root/"adapter-quickstart-manifest.json"; errors=[]
    if not manifest.exists(): errors.append("missing adapter-quickstart-manifest.json")
    else:
        data=json.loads(manifest.read_text(encoding="utf-8"))
        errors.extend(_schema_required_errors(data, schema_root()/"adapter-quickstart-v1.schema.json", "adapter_manifest"))
        for a in data.get("adapters", []):
            d=root/a.get("type", "")
            for key in ["entrypoint","config","tools","self_test"]:
                if not (d/a.get(key, "")).exists(): errors.append(f"missing {a.get('type')}/{a.get(key)}")
    payload={"status":"ok" if not errors else "fail", "dir":str(root), "errors":errors}
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0 if not errors else 1





def agent_route(args):
    routes_path=pathlib.Path(args.routes)
    if not routes_path.exists():
        print(json.dumps({"status":"fail","errors":[f"missing routes file: {routes_path}"]}, indent=2)); return 2
    data=json.loads(routes_path.read_text(encoding='utf-8'))
    runtime=args.runtime
    intent=args.intent
    routes=data.get('routes', [])
    if runtime == 'list':
        payload={'status':'ok','runtimes':data.get('agent_families', []),'intents':data.get('intents', [])}
        print(json.dumps(payload, indent=2) if args.json else '\n'.join(payload['runtimes']))
        return 0
    route=next((r for r in routes if r.get('runtime') == runtime), None)
    if not route:
        payload={'status':'fail','errors':[f'unknown runtime: {runtime}'],'available_runtimes':data.get('agent_families', [])}
        print(json.dumps(payload, indent=2)); return 1
    commands_by_intent=route.get('commands_by_intent', {})
    if intent == 'all':
        selected=commands_by_intent
    elif intent in commands_by_intent:
        selected={intent:commands_by_intent[intent]}
    else:
        payload={'status':'fail','runtime':runtime,'errors':[f'unknown intent: {intent}'],'available_intents':sorted(commands_by_intent)}
        print(json.dumps(payload, indent=2)); return 1
    payload={'schema_version':'2026-05-03.agentpress-agent-route-result.v1','status':'ok','runtime':runtime,'intent':intent,'route_id':route.get('route_id'),'entrypoints':route.get('entrypoints', []),'commands_by_intent':selected,'proof_required_for_reputation':route.get('proof_required_for_reputation', True),'privacy':route.get('privacy'),'next_step':'execute commands in order, then submit opt-in proof receipt'}
    if args.out:
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"AgentPress route: runtime={runtime} intent={intent}")
        for key, commands in selected.items():
            print(f"\n## {key}")
            for cmd in commands:
                print(cmd)
    return 0


def agent_traffic_audit(args):
    root=pathlib.Path(args.root)
    required=[
        'llms.txt','AGENTS.md','README.md','robots.txt','sitemap.xml','agent-sitemap.xml',
        '.well-known/agentpress.json','.well-known/ai-ingestion.json',
        'agentpress/CLI_AGENT_LAUNCH.md','agentpress/cli-launch.json',
        'agentpress/routes/agent-routes.json',
        'agentpress/traffic/crawler-seeds.txt','agentpress/traffic/agent-traffic-acquisition.json',
        'agentpress/tools/agentpress-tools.json','agentpress/compatibility/compatibility-matrix.json',
        'agentpress/directory-submission/agentpress-directory-pitch.json','agentpress/submissions/README.md','agentpress/landing/README.md'
    ]
    checks=[]
    for rel in required:
        path=root/rel
        ok=path.exists() and path.stat().st_size > 0
        detail={'path':rel,'exists':path.exists(),'bytes':path.stat().st_size if path.exists() else 0}
        if ok and rel.endswith('.json'):
            try: json.loads(path.read_text(encoding='utf-8'))
            except Exception as e: ok=False; detail['json_error']=str(e)
        checks.append({'name':'required_surface','status':'pass' if ok else 'fail','detail':detail})
    # verify core CTA terms are present in text entrypoints
    terms=['CLI_AGENT_LAUNCH','compatibility-matrix','landing-receipt','submission-pack']
    for rel in ['llms.txt','README.md','AGENTS.md','agentpress/CLI_AGENT_LAUNCH.md']:
        text=(root/rel).read_text(encoding='utf-8', errors='replace') if (root/rel).exists() else ''
        missing=[t for t in terms if t not in text]
        checks.append({'name':'cta_terms','status':'pass' if not missing else 'fail','detail':{'path':rel,'missing':missing}})
    # seed count
    seeds=root/'agentpress/traffic/crawler-seeds.txt'
    seed_count=len([x for x in seeds.read_text(encoding='utf-8').splitlines() if x.strip()]) if seeds.exists() else 0
    checks.append({'name':'crawler_seed_count','status':'pass' if seed_count >= 15 else 'fail','detail':{'count':seed_count,'minimum':15}})
    passed=sum(1 for c in checks if c['status']=='pass')
    payload={'schema_version':'2026-05-03.agentpress-agent-traffic-audit.v1','generated_utc':_utc_now(),'status':'ok' if passed==len(checks) else 'fail','score':round(100*passed/len(checks)) if checks else 0,'passed':passed,'total':len(checks),'checks':checks,'next_actions':['submit directory pitch to agent/tool indexes','monitor opt-in landing receipts','run compatibility matrix on external agent hosts']}
    out=pathlib.Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2) if args.json else f"{out} {payload['status']} {payload['score']}/100")
    return 0 if payload['status']=='ok' else 1


def compatibility_matrix(args):
    out=pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    workdir=pathlib.Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    runtimes=args.runtime or ["codex","claude","gemini","glm","browser","rag"]
    binary_map={"codex":"codex","claude":"claude","gemini":"gemini","glm":"python3","browser":"python3","rag":"python3"}
    rows=[]
    for runtime in runtimes:
        rid=slugify(runtime)
        agent_id=f"compat-{rid}-agent"
        row={"runtime":runtime,"agent_id":agent_id,"checked_utc":_utc_now(),"binary":binary_map.get(runtime, runtime),"binary_present":bool(shutil.which(binary_map.get(runtime, runtime))),"steps":[],"status":"unknown"}
        def step(name, ok, evidence=None, errors=None):
            row["steps"].append({"name":name,"status":"pass" if ok else "fail","evidence":evidence or {},"errors":errors or []})
        try:
            adapter_dir=workdir/f"adapter-{rid}"
            with contextlib.redirect_stdout(io.StringIO()):
                adapter_quickstart(argparse.Namespace(agent_type=runtime if runtime in ["codex","claude","gemini","glm","browser"] else "browser", out=str(adapter_dir), json=True))
                code=adapter_quickstart_check(argparse.Namespace(dir=str(adapter_dir), json=True))
            step("adapter_quickstart", code == 0, {"dir":str(adapter_dir)})
        except Exception as e:
            step("adapter_quickstart", False, errors=[str(e)])
        try:
            self_out=workdir/f"{rid}-self-test.jsonl"
            with contextlib.redirect_stdout(io.StringIO()):
                code=self_test(argparse.Namespace(agent_id=agent_id,bundle=args.bundle,suite=args.suite,out=str(self_out),index=args.index,workdir=str(workdir/f"self-{rid}"),run_id=None))
            lines=self_out.read_text(encoding="utf-8").strip().splitlines() if self_out.exists() else []
            step("self_test", code == 0, {"out":str(self_out),"jsonl_rows":len(lines)})
        except Exception as e:
            step("self_test", False, errors=[str(e)])
        try:
            receipt=workdir/f"{rid}-landing-receipt.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code=landing_receipt(argparse.Namespace(agent_id=agent_id,runtime=runtime,discovery_channel="compatibility-matrix",capability=["install","doctor","self-test","proof-submission"],self_test_ref=str(workdir/f"{rid}-self-test.jsonl"),contact=None,base_url=CANONICAL_BASE_URL,landing_id=None,out=str(receipt),json=True))
            step("landing_receipt", code == 0, {"out":str(receipt)})
        except Exception as e:
            step("landing_receipt", False, errors=[str(e)])
        try:
            pack=workdir/f"{rid}-submission-pack"
            with contextlib.redirect_stdout(io.StringIO()):
                code=submission_pack(argparse.Namespace(receipt=str(workdir/f"{rid}-landing-receipt.json"),out=str(pack),json=True))
            step("submission_pack", code == 0, {"out":str(pack)})
        except Exception as e:
            step("submission_pack", False, errors=[str(e)])
        passed=sum(1 for x in row["steps"] if x["status"] == "pass")
        row["passed_steps"]=passed
        row["total_steps"]=len(row["steps"])
        row["status"]="pass" if passed == len(row["steps"]) and row["steps"] else "fail"
        rows.append(row)
    payload={"schema_version":"2026-05-03.agentpress-compatibility-matrix.v1","generated_utc":_utc_now(),"status":"ok" if all(r["status"] == "pass" for r in rows) else "fail","runtimes_tested":len(rows),"pass_count":sum(1 for r in rows if r["status"] == "pass"),"matrix":rows,"next_actions":["run this on real Codex/Claude/Gemini/GLM/browser/RAG hosts","attach generated landing receipts via submission-pack","promote third-party verified receipts into reputation index"]}
    out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"{out} {payload['status']} {payload['pass_count']}/{payload['runtimes_tested']}")
    return 0 if payload["status"] == "ok" else 1


def tools_manifest(args):
    base=args.base_url.rstrip("/") + "/"
    tools=[
        {"name":"agentpress.fetch", "description":"Fetch core AgentPress machine assets.", "command":"python3 scripts/agentpress.py fetch --base {base} --out agentpress-fetch --json", "tags":["fetch","bootstrap","offline"]},
        {"name":"agentpress.discover", "description":"Discover another AgentPress node, inspect tools/releases/contracts, and update a known-agent mesh registry.", "command":"python3 scripts/agentpress.py discover <agentpress-url> --registry agentpress/mesh/known-agents.json --json", "tags":["discover","mesh","agent-network","tools","release","self-register"]},
        {"name":"agentpress.verify", "description":"Verify an AgentPress bundle fails/passes contract checks.", "command":"python3 scripts/agentpress.py verify <bundle> --json", "tags":["verify","schema","contract"]},
        {"name":"agentpress.bundle", "description":"Generate a valid AgentPress bundle from docs/API folder.", "command":"python3 scripts/agentpress.py bundle <source-dir> --out <bundle-dir> --title <title> --force", "tags":["generate","bundle","docs","api"]},
        {"name":"agentpress.message", "description":"Create, route, respond, thread, and validate agent work messages.", "command":"python3 scripts/agentpress.py message create-request --capability <capability> --task <task> --requester-id <agent-id> --out request.json", "tags":["message","route","handoff"]},
        {"name":"agentpress.search", "description":"Search AgentPress assets/capabilities/schemas by query.", "command":"python3 scripts/agentpress.py search <query> --json", "tags":["search","capability","discovery"]},
        {"name":"agentpress.self_test", "description":"Run standard suite proving an agent can use AgentPress.", "command":"python3 scripts/agentpress.py self-test --agent-id <agent-id> --out self-test.jsonl", "tags":["self-test","reputation","proof"]},
        {"name":"agentpress.team_pack", "description":"Create privacy-safe team/person capability pack.", "command":"python3 scripts/agentpress.py team-pack --slug <slug> --capability <kind:name> --consent-source public_source --out team.json", "tags":["team","capability","privacy"]},
        {"name":"agentpress.package_verify", "description":"Build and verify an offline AgentPress package by SHA256 manifest.", "command":"python3 scripts/agentpress.py package . --out dist/agentpress-offline.tar.gz && python3 scripts/agentpress.py package-verify dist/agentpress-offline.tar.gz --json", "tags":["package","sha256","offline"]},
        {"name":"agentpress.install", "description":"Install AgentPress offline package from static release index with SHA256 verification.", "command":"python3 -c \"$(curl -fsSL https://barneywohl.github.io/agentpress/agentpress/install/install.py)\" --json", "tags":["install","release","package","offline","sha256"]},
        {"name":"agentpress.landing_receipt", "description":"Create a privacy-safe opt-in receipt proving an agent discovered and landed on AgentPress.", "command":"python3 scripts/agentpress.py landing-receipt --agent-id <agent-id> --runtime <runtime> --discovery-channel <channel> --capability <capability> --out landing/<agent-id>.json --json", "tags":["landing","telemetry","adoption","privacy"]},
        {"name":"agentpress.reputation_index", "description":"Compile landing receipts, self-tests, and handoff receipts into an evidence-derived agent reputation index.", "command":"python3 scripts/agentpress.py reputation-index --landing-dir agentpress/landing --self-test-dir agentpress/self-test --receipt-dir agentpress/receipts --out agentpress/reputation/reputation-index.json --json", "tags":["reputation","leaderboard","proof","trust"]},
        {"name":"agentpress.submission_pack", "description":"Generate a PR/issue-ready pack for submitting landing/proof receipts back to AgentPress.", "command":"python3 scripts/agentpress.py submission-pack --receipt <receipt.json> --out submission-pack --json", "tags":["submission","github","landing","proof","adoption"]},
        {"name":"agentpress.feedback_submit", "description":"Emit or validate deterministic external-agent feedback against the AgentPress response template/rubric.", "command":"python3 scripts/agentpress.py feedback-submit --example", "tags":["feedback","rubric","first-contact","agent-review"]},
        {"name":"agentpress.consistency_check", "description":"Fail CI when first-contact machine contracts drift across llms.txt, README, schemas, and agent instructions.", "command":"python3 scripts/agentpress.py consistency-check --json", "tags":["consistency","ci","contract","drift"]},
        {"name":"agentpress.adoption_status", "description":"Summarize opt-in landing receipts, reputation, compatibility, mesh, and install-lane adoption state without hidden telemetry.", "command":"python3 scripts/agentpress.py adoption-status --json", "tags":["adoption","reputation","compatibility","privacy","proof"]},
        {"name":"agentpress.payment_status", "description":"Report payment/x402 readiness, budget guardrails, and fail-closed payment policy without performing payments.", "command":"python3 scripts/agentpress.py payment-status --json", "tags":["payments","x402","budget","safety","commerce"]},
        {"name":"agentpress.payment_intent", "description":"Create an unsigned quote/payment intent for budget approval workflows without signing or spending.", "command":"python3 scripts/agentpress.py payment-intent --capability-id free_agentpress_bootstrap --agent-id <agent-id> --max-amount 0 --json", "tags":["payments","quote","budget","intent","no-spend"]},
        {"name":"agentpress.adopt", "description":"Run the full one-command adoption funnel: doctor, self-test, landing receipt, payment posture, unsigned payment intent, and submission pack.", "command":"python3 scripts/agentpress.py adopt --agent-id <agent-id> --runtime <runtime> --out /tmp/agentpress-onboard --json", "tags":["onboard","adoption","self-test","landing","submission","payment","flywheel"]},
        {"name":"agentpress.compatibility_matrix", "description":"Run install/doctor/self-test/proof compatibility checks across agent runtime families and emit a machine-readable matrix.", "command":"python3 scripts/agentpress.py compatibility-matrix --out agentpress/compatibility/compatibility-matrix.json --json", "tags":["compatibility","runtime","matrix","proof","self-test"]},
        {"name":"agentpress.agent_traffic_audit", "description":"Audit whether AgentPress exposes the required machine surfaces for agent traffic and proof conversion.", "command":"python3 scripts/agentpress.py agent-traffic-audit --out agentpress/traffic/agent-traffic-audit.json --json", "tags":["traffic","audit","crawler","routes","proof"]},
        {"name":"agentpress.agent_route", "description":"Return exact commands and URLs for an agent runtime and intent from the AgentPress route manifest.", "command":"python3 scripts/agentpress.py agent-route --runtime codex --intent prove --json", "tags":["agent-route","routes","runtime","intent","commands"]},
    ]
    payload={
        "schema_version":"2026-05-03.agentpress-tools-manifest.v1",
        "name":"AgentPress Tool Discovery Manifest",
        "canonical_url":urljoin(base, args.out),
        "generated_at":_utc_now(),
        "purpose":"Let autonomous agents discover executable AgentPress tools without reading prose.",
        "safety":{"external_side_effects":"none by default", "requires_human_approval":["external_write","production_change","payment","credential_access"], "prohibited":["credential_access","private_data_extraction","spam","impersonation"]},
        "tools":tools,
        "mcp_static_hint":{"manifest_url":urljoin(base, args.out), "transport":"static-json", "call_mode":"local-cli"}
    }
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status":"ok", "out":str(out), "tool_count":len(tools)}, indent=2))
    return 0


def tools_manifest_check(args):
    path=pathlib.Path(args.path); data=json.loads(path.read_text(encoding="utf-8"))
    errors=[]
    names=[t.get("name") for t in data.get("tools", [])]
    for required in ["agentpress.fetch","agentpress.verify","agentpress.bundle","agentpress.search","agentpress.self_test"]:
        if required not in names: errors.append(f"missing tool: {required}")
    for t in data.get("tools", []):
        if not t.get("command") or not t.get("description"):
            errors.append(f"tool missing command/description: {t.get('name')}")
    payload={"status":"ok" if not errors else "fail", "path":str(path), "tool_count":len(names), "errors":errors}
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0 if not errors else 1



def release_index(args):
    package=pathlib.Path(args.package)
    manifest=pathlib.Path(args.manifest or (str(package)+".sha256.json"))
    errors=[]
    if not package.exists(): errors.append(f"missing package: {package}")
    if not manifest.exists(): errors.append(f"missing manifest: {manifest}")
    if errors:
        print(json.dumps({"status":"fail","errors":errors},indent=2)); return 1
    base=args.base_url.rstrip("/")+"/"
    pkg_rel=args.package_url or package.as_posix()
    man_rel=args.manifest_url or manifest.as_posix()
    package_sha=hashlib.sha256(package.read_bytes()).hexdigest()
    manifest_sha=hashlib.sha256(manifest.read_bytes()).hexdigest()
    mdata=json.loads(manifest.read_text(encoding="utf-8"))
    payload={"schema_version":"1.0","status":"ok","generated_utc":_utc_now(),"name":"AgentPress offline release index","latest":{"version":args.version,"package_url":urljoin(base,pkg_rel),"manifest_url":urljoin(base,man_rel),"package_sha256":package_sha,"manifest_sha256":manifest_sha,"bytes":package.stat().st_size,"asset_count":mdata.get("count"),"install_command":f"python3 -c \"$(curl -fsSL {urljoin(base,args.install_path)})\" --base-url {base} --out agentpress-offline"},"mirrors":[{"kind":"github_pages","base_url":base},{"kind":"raw_github","base_url":args.raw_base_url}],"verify_command":f"python3 scripts/agentpress.py package-verify {package.name} --manifest {manifest.name} --json","privacy":"static release index; no tracking"}
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"ok","out":str(out),"package_sha256":package_sha},indent=2) if args.json else str(out))
    return 0


def install_script(args):
    script = """#!/usr/bin/env python3
import argparse, json, pathlib, shutil, sys, tarfile, tempfile, urllib.request, hashlib
from urllib.parse import urljoin

def read_url(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def main():
    ap=argparse.ArgumentParser(description='Install AgentPress offline package from static release index')
    ap.add_argument('--base-url', default='__BASE_URL__')
    ap.add_argument('--release-index', default='agentpress/releases/release-index.json')
    ap.add_argument('--out', default='agentpress-offline')
    ap.add_argument('--json', action='store_true')
    args=ap.parse_args()
    base=args.base_url.rstrip('/')+'/'
    index_url=urljoin(base,args.release_index)
    idx=json.loads(read_url(index_url).decode())
    latest=idx['latest']
    pkg=read_url(latest['package_url'])
    if sha256(pkg) != latest['package_sha256']:
        raise SystemExit('package sha256 mismatch')
    manifest_bytes=read_url(latest['manifest_url'])
    if sha256(manifest_bytes) != latest['manifest_sha256']:
        raise SystemExit('manifest sha256 mismatch')
    manifest=json.loads(manifest_bytes.decode())
    out=pathlib.Path(args.out)
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    tmp=pathlib.Path(tempfile.mkdtemp())/'agentpress-offline.tar.gz'
    tmp.write_bytes(pkg)
    with tarfile.open(tmp,'r:*') as t:
        t.extractall(out)
    checked=0
    for row in manifest.get('assets',[]):
        p=out/row['path']
        if not p.exists(): raise SystemExit('missing asset after extract: '+row['path'])
        if sha256(p.read_bytes()) != row['sha256']: raise SystemExit('asset sha256 mismatch: '+row['path'])
        checked+=1
    payload={'status':'ok','out':str(out),'checked':checked,'release_index':index_url,'version':latest.get('version')}
    print(json.dumps(payload,indent=2) if args.json else 'AgentPress installed to '+str(out))
if __name__ == '__main__':
    main()
""".replace('__BASE_URL__', args.base_url)
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(script,encoding="utf-8"); out.chmod(0o755)
    print(json.dumps({"status":"ok","out":str(out)},indent=2) if args.json else str(out))
    return 0


def package_verify(args):
    import tarfile, zipfile
    package = pathlib.Path(args.package)
    manifest = pathlib.Path(args.manifest or (str(package) + ".sha256.json"))
    errors=[]
    if not package.exists(): errors.append(f"missing package: {package}")
    if not manifest.exists(): errors.append(f"missing manifest: {manifest}")
    if errors:
        print(json.dumps({"status":"fail", "errors":errors}, indent=2)); return 1
    data=json.loads(manifest.read_text(encoding="utf-8"))
    rows=data.get("assets", [])
    tmp=pathlib.Path(args.workdir)
    if tmp.exists(): shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        if package.suffix == ".zip":
            with zipfile.ZipFile(package) as z: z.extractall(tmp)
        else:
            with tarfile.open(package, "r:*") as t: t.extractall(tmp)
    except Exception as e:
        print(json.dumps({"status":"fail", "errors":[f"extract failed: {e}"]}, indent=2)); return 1
    checked=[]
    for row in rows:
        rel=row.get("path")
        if not rel: continue
        f=tmp/rel
        if not f.exists():
            errors.append(f"missing packaged asset: {rel}"); continue
        b=f.read_bytes(); sha=hashlib.sha256(b).hexdigest()
        if sha != row.get("sha256"):
            errors.append(f"sha256 mismatch: {rel}")
        checked.append({"path":rel, "bytes":len(b), "sha256":sha})
    required=["llms.txt", ".well-known/agentpress.json", "agentpress/schemas/index.json", "scripts/agentpress.py"]
    for rel in required:
        if not (tmp/rel).exists(): errors.append(f"missing required offline asset: {rel}")
    payload={"status":"ok" if not errors else "fail", "package":str(package), "manifest":str(manifest), "checked":len(checked), "errors":errors}
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    if not args.keep_workdir and tmp.exists(): shutil.rmtree(tmp)
    return 0 if not errors else 1


def package_index(args):
    package=pathlib.Path(args.package)
    manifest=pathlib.Path(args.manifest or (str(package)+".sha256.json"))
    if not package.exists() or not manifest.exists():
        print(json.dumps({"status":"fail", "errors":["package and manifest required"]}, indent=2)); return 1
    data=json.loads(manifest.read_text(encoding="utf-8"))
    pkg_sha=hashlib.sha256(package.read_bytes()).hexdigest()
    payload={
        "schema_version":"2026-05-03.agentpress-offline-package-index.v1",
        "generated_at":_utc_now(),
        "package":{"path":str(package), "bytes":package.stat().st_size, "sha256":pkg_sha},
        "manifest":{"path":str(manifest), "asset_count":data.get("count"), "sha256":hashlib.sha256(manifest.read_bytes()).hexdigest()},
        "verify_command":f"python3 scripts/agentpress.py package-verify {package} --manifest {manifest} --json",
        "core_assets":["llms.txt", ".well-known/agentpress.json", "agentpress/schemas/index.json", "scripts/agentpress.py"]
    }
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status":"ok", "out":str(out), "package_sha256":pkg_sha}, indent=2))
    return 0


def doctor(args):
    root = pathlib.Path(args.root)
    entrypoints = [
        "llms.txt",
        ".well-known/agentpress.json",
        ".well-known/ai-ingestion.json",
        "agentpress/articles/article-index.json",
        "agentpress/examples/agent-knowledge-sharing/AGENT_ENTRYPOINT.md",
        "agentpress/examples/agent-knowledge-sharing/agent-task-card.json",
        "agentpress/examples/agent-knowledge-sharing/mirrors.json",
        "agentpress/examples/agent-knowledge-sharing/translation-policy.md",
        "AGENTS.md",
        "sitemap.xml",
    ]
    rows = []
    ok = True
    for rel in entrypoints:
        exists = (root/rel).exists()
        rows.append({"path": rel, "status": "OK" if exists else "MISSING"})
        if not exists:
            ok = False
    ref = root/"agentpress/examples/agent-knowledge-sharing"
    primary_errors = []
    primary_warnings = []
    primary_score = None
    if ref.exists():
        code, primary_errors, primary_warnings = audit_root(ref, strict=True)
        if code:
            ok = False
        primary_score, detail = score_value(ref)
        if primary_score < 100:
            ok = False
    else:
        ok = False
        primary_errors.append("missing primary neutral reference")
    payload = {
        "status": "ok" if ok else "fail",
        "root": str(root),
        "entrypoints": rows,
        "primary_reference_score": primary_score,
        "primary_reference_errors": primary_errors,
        "primary_reference_warnings": primary_warnings,
        "canonical_url": "https://barneywohl.github.io/agentpress/",
        "raw_fallback": "https://raw.githubusercontent.com/barneywohl/agentpress/refs/heads/main/",
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
        return 0 if ok else 1
    print("AgentPress doctor")
    print(f"root: {root}")
    for row in rows:
        print(f"{row['status']:<7} {row['path']}")
    if primary_errors:
        print(json.dumps({"primary_reference_errors": primary_errors, "warnings": primary_warnings}, indent=2), file=sys.stderr)
    if primary_score is not None:
        print(f"primary_reference_score: {primary_score}/100")
    print("canonical_url: https://barneywohl.github.io/agentpress/")
    print("raw_fallback: https://raw.githubusercontent.com/barneywohl/agentpress/refs/heads/main/")
    return 0 if ok else 1




def payment_status(args):
    """Report AgentPress payment/x402 posture without performing payments."""
    root=pathlib.Path(args.root)
    errors=[]
    def load(rel):
        path=root/rel
        if not path.exists():
            errors.append(f"missing {rel}"); return {}
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"{rel}: {e}"); return {}
    policy=load("agentpress/payments/payment-policy.json")
    capabilities=load("agentpress/payments/payment-capabilities.json")
    x402=load("agentpress/payments/x402-readiness.json")
    caps=capabilities.get("capabilities", []) if isinstance(capabilities, dict) else []
    payment_required=[c for c in caps if c.get("payment_required")]
    payload={
        "schema_version":"2026-05-03.agentpress-payment-status-result.v1",
        "generated_utc":_utc_now(),
        "status":"ok" if not errors else "fail",
        "verdict": policy.get("agent_answer") or "Payment metadata is useful; live payments are not authorized by public files.",
        "live_payments_enabled": False,
        "core_discovery_free": True,
        "x402_posture": x402.get("verdict", "metadata_only"),
        "capability_count": len(caps),
        "payment_required_capability_count": len(payment_required),
        "free_capabilities": [c.get("capability_id") for c in caps if not c.get("payment_required")],
        "requires_separate_authorization": policy.get("requires_separate_authorization", []),
        "prohibited_by_public_bundle": policy.get("prohibited_by_public_bundle", []),
        "errors": errors,
        "agent_next_action": "Read payment-policy.json. If payment is required, fail closed unless explicit budget/signer/network/asset/receipt authorization exists."
    }
    if args.out:
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["verdict"])
    return 0 if not errors else 1


def payment_intent(args):
    """Create an unsigned, non-executing payment intent for budget approval workflows."""
    root=pathlib.Path(args.root)
    caps_path=root/"agentpress/payments/payment-capabilities.json"
    if not caps_path.exists():
        print(f"missing {caps_path}", file=sys.stderr); return 1
    data=json.loads(caps_path.read_text(encoding="utf-8"))
    caps=data.get("capabilities", [])
    cap=next((c for c in caps if c.get("capability_id") == args.capability_id), None)
    if not cap:
        print(f"unknown capability_id: {args.capability_id}", file=sys.stderr); return 1
    payload={
        "schema_version":"2026-05-03.agentpress-payment-intent.v1",
        "intent_id": _short_id("pay-intent"),
        "created_utc": _utc_now(),
        "capability_id": args.capability_id,
        "status":"quote_only" if not cap.get("payment_required") else "blocked_pending_authorization",
        "payment_required": bool(cap.get("payment_required")),
        "authorization_required": True,
        "requested_by":{"type":"agent", "id":args.agent_id},
        "budget":{"max_amount":str(args.max_amount), "currency":args.currency, "max_per_request":str(args.max_per_request or args.max_amount), "expires_utc":args.expires_utc},
        "accepted_protocols": cap.get("payment_protocol_candidates", []),
        "receipt_policy":{"required": True, "schema":"https://barneywohl.github.io/agentpress/agentpress/schemas/payment-intent-v1.schema.json", "settlement_receipt":"external_only_not_generated_by_public_bundle"},
        "prohibited_fields":["private_key","seed_phrase","wallet_secret","facilitator_api_key","bearer_token"],
        "notes":"Unsigned quote/intent only. This command never signs, submits, or settles payment."
    }
    if args.out:
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["intent_id"])
    return 0


def agent_onboard(args):
    """One-command AgentPress adoption funnel for outside agents."""
    root=pathlib.Path(args.root)
    out=pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    agent_id=args.agent_id
    runtime=args.runtime
    errors=[]
    steps=[]
    def capture_step(name, fn, ns, artifact=None):
        buf=io.StringIO()
        code=1
        try:
            with contextlib.redirect_stdout(buf):
                code=fn(ns)
        except SystemExit as e:
            code=int(e.code or 0) if isinstance(e.code, int) else 1
        except Exception as e:
            code=1; errors.append(f"{name}: {e}")
        stdout=buf.getvalue().strip()
        if stdout:
            (out/f"{name}.stdout.txt").write_text(stdout+"\n", encoding="utf-8")
        step={"name":name,"status":"pass" if code==0 else "fail","exit_code":code}
        if artifact: step["artifact"]=str(artifact)
        if code!=0: errors.append(f"{name} failed with exit {code}")
        steps.append(step)
        return code

    doctor_out=out/"doctor.json"
    # doctor prints JSON; preserve stdout and parseable artifact for agents.
    buf=io.StringIO(); code=1
    try:
        with contextlib.redirect_stdout(buf): code=doctor(argparse.Namespace(root=str(root), json=True))
    except Exception as e:
        errors.append(f"doctor: {e}")
    text=buf.getvalue().strip(); doctor_out.write_text(text+"\n", encoding="utf-8")
    steps.append({"name":"doctor","status":"pass" if code==0 else "fail","exit_code":code,"artifact":str(doctor_out)})
    if code!=0: errors.append("doctor failed")

    self_test_out=out/"self-test.jsonl"
    capture_step("self-test", self_test, argparse.Namespace(agent_id=agent_id, bundle=args.bundle, suite=args.suite, out=str(self_test_out), index=args.index, workdir=str(out/"work/self-test"), run_id=None), self_test_out)

    landing_out=out/"landing-receipt.json"
    capture_step("landing-receipt", landing_receipt, argparse.Namespace(agent_id=agent_id, runtime=runtime, discovery_channel=args.discovery_channel, capability=["agentpress_onboard,self-test,landing-receipt,submission-pack,payment-status"], out=str(landing_out), landing_id=None, base_url=args.base_url, self_test_ref=str(self_test_out), contact=args.contact, json=True), landing_out)

    payment_status_out=out/"payment-status.json"
    capture_step("payment-status", payment_status, argparse.Namespace(root=str(root), out=str(payment_status_out), json=True), payment_status_out)

    payment_intent_out=out/"payment-intent.json"
    capture_step("payment-intent", payment_intent, argparse.Namespace(root=str(root), capability_id=args.payment_capability_id, agent_id=agent_id, max_amount=args.max_amount, max_per_request=args.max_per_request, currency=args.currency, expires_utc=args.expires_utc, out=str(payment_intent_out), json=True), payment_intent_out)

    submission_out=out/"submission-pack"
    if landing_out.exists():
        capture_step("submission-pack", submission_pack, argparse.Namespace(receipt=str(landing_out), out=str(submission_out), json=True), submission_out)
    else:
        errors.append("submission-pack skipped: landing receipt missing")
        steps.append({"name":"submission-pack","status":"fail","exit_code":1,"artifact":str(submission_out)})

    files=[]
    for fp in sorted(out.rglob("*")):
        if fp.is_file():
            files.append({"path":str(fp.relative_to(out)),"bytes":fp.stat().st_size,"sha256":hashlib.sha256(fp.read_bytes()).hexdigest()})
    manifest={
        "schema_version":"2026-05-03.agentpress-agent-onboard.v1",
        "status":"ok" if not errors else "fail",
        "generated_utc":_utc_now(),
        "agent_id":agent_id,
        "runtime":runtime,
        "root":str(root),
        "base_url":args.base_url,
        "steps":steps,
        "files":files,
        "errors":errors,
        "next_actions":[
            "Inspect manifest.json, doctor.json, self-test.jsonl, landing-receipt.json, payment-status.json, and payment-intent.json.",
            "Submit submission-pack by GitHub issue or PR if you want public reputation credit.",
            "Do not execute payment unless a separate trusted budget/signer/network/asset authorization exists."
        ],
        "privacy":"Generated locally from opt-in agent id/runtime/contact. No IP address, user-agent, secret, wallet key, or private prompt is collected."
    }
    manifest_out=out/"manifest.json"; manifest_out.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    readme=f"""# AgentPress onboarding pack for `{agent_id}`\n\nStatus: `{manifest['status']}`\n\nGenerated: `{manifest['generated_utc']}`\n\n## Files\n\n- `manifest.json` — full machine-readable onboarding summary.\n- `doctor.json` — local AgentPress health check.\n- `self-test.jsonl` — standard self-test results.\n- `landing-receipt.json` — privacy-safe opt-in landing proof.\n- `payment-status.json` — payment/x402 posture; live payments disabled.\n- `payment-intent.json` — unsigned quote/budget intent only; no spend.\n- `submission-pack/` — issue/PR-ready proof submission.\n\n## Submit proof\n\nUse `submission-pack/README.md` and `submission-pack/github-issue.md`.\n\n## Safety\n\nThis onboarding command does not sign, submit, settle, or authorize payments.\n"""
    (out/"README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({"status":manifest["status"],"out":str(out),"manifest":str(manifest_out),"steps":len(steps),"errors":errors}, indent=2) if args.json else str(out))
    return 0 if manifest["status"] == "ok" else 1

def adoption_status(args):
    """Summarize opt-in AgentPress adoption/proof state without hidden telemetry."""
    root=pathlib.Path(args.root)
    errors=[]
    def load(rel, default):
        path=root/rel
        if not path.exists():
            errors.append(f"missing {rel}"); return default
        try: return json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:
            errors.append(f"{rel}: {e}"); return default
    mesh=load('agentpress/mesh/known-agents.json', {})
    landing=load('agentpress/landing/agent-landing-index.json', {})
    rep=load('agentpress/reputation/reputation-index.json', {})
    compat=load('agentpress/compatibility/compatibility-matrix.json', {})
    catalog=load('agentpress/install/install-catalog.json', {})
    third_party=0
    for r in landing.get('receipts', []):
        aid=(r.get('agent_id') or '')
        if aid and not aid.startswith('compat-') and aid != 'agentpress-barneywohl':
            third_party+=1
    metrics={
        'mesh_known_agents': mesh.get('agent_count', 0),
        'landing_receipts': landing.get('receipt_count', 0),
        'reputation_agents': rep.get('agent_count', 0),
        'compatibility_profiles_passed': compat.get('pass_count', 0),
        'compatibility_profiles_tested': compat.get('runtimes_tested', 0),
        'third_party_receipts': third_party,
        'install_lanes_live': sum(1 for x in catalog.get('lanes', []) if str(x.get('status','')).startswith('live')),
    }
    status='ok' if not errors and metrics['compatibility_profiles_passed'] == metrics['compatibility_profiles_tested'] and metrics['landing_receipts'] >= 1 else 'needs_attention'
    payload={'schema_version':'2026-05-03.agentpress-adoption-status-result.v1','generated_utc':_utc_now(),'status':status,'metrics':metrics,'errors':errors,'next_actions':['collect independent third-party receipts','publish package registry lanes after ownership confirmation','run compatibility from real external hosts','add non-GitHub mirror']}
    if args.out:
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(payload, indent=2) if args.json else status)
    return 0 if status == 'ok' or args.allow_needs_attention else 1

def feedback_submit(args):
    """Emit or validate a deterministic AgentPress feedback response."""
    template_path = pathlib.Path(args.template)
    rubric_path = pathlib.Path(args.rubric)
    if args.example:
        payload = {
            "schema_version": "2026-05-03.agentpress-feedback-response.v1",
            "agent_id": args.agent_id or "example-agent",
            "agent_family": args.agent_family,
            "runtime_or_model": args.runtime_or_model or "unknown",
            "target_url": args.target_url,
            "submitted_utc": _utc_now(),
            "scores": {
                "first_contact_score_0_10": 8,
                "machine_readability_score_0_10": 9,
                "trust_integrity_score_0_10": 8,
                "handoff_quality_score_0_10": 8,
                "recommendation_likelihood_0_10": 8,
            },
            "top_blockers": [
                {"severity": "P1", "evidence_url_or_path": "https://barneywohl.github.io/agentpress/llms.txt", "blocker": "Agent can start, but explicit proof-submission loop should be repeated in every first-contact surface."}
            ],
            "missing_machine_files": [],
            "recommended_next_builds": ["Keep landing receipt, self-test, and proof-submission commands adjacent in llms.txt and README.md."],
            "evidence_urls": ["https://barneywohl.github.io/agentpress/llms.txt"],
            "commands_run": ["python3 scripts/agentpress.py doctor --json"],
            "patch_suggestions": [{"path": "llms.txt", "change": "Add one exact feedback-submit example after landing receipt instructions."}],
            "privacy": {"contains_secrets": False, "contains_private_prompts": False, "contains_user_data": False},
        }
        print(json.dumps(payload, indent=2))
        return 0
    if not args.input:
        print("feedback-submit requires --example or --input", file=sys.stderr)
        return 1
    errors=[]
    try:
        payload=json.loads(pathlib.Path(args.input).read_text(encoding='utf-8'))
    except Exception as e:
        print(json.dumps({"status":"fail","errors":[f"input parse failed: {e}"]}, indent=2)); return 1
    required=["schema_version","agent_id","agent_family","target_url","submitted_utc","scores","top_blockers","evidence_urls","patch_suggestions","privacy"]
    for k in required:
        if k not in payload: errors.append(f"feedback missing required field: {k}")
    scores=payload.get('scores') or {}
    for k in ["first_contact_score_0_10","machine_readability_score_0_10","trust_integrity_score_0_10"]:
        v=scores.get(k)
        if not isinstance(v, (int,float)) or v < 0 or v > 10: errors.append(f"scores.{k} must be number 0..10")
    for idx, b in enumerate(payload.get('top_blockers') or []):
        if not isinstance(b, dict): errors.append(f"top_blockers[{idx}] must be object"); continue
        for k in ["severity","evidence_url_or_path","blocker"]:
            if not b.get(k): errors.append(f"top_blockers[{idx}] missing {k}")
    result={"status":"ok" if not errors else "fail", "input": args.input, "template": str(template_path), "rubric": str(rubric_path), "errors": errors}
    print(json.dumps(result, indent=2) if args.json else result["status"])
    return 0 if not errors else 1


def consistency_check(args):
    """Check that first-contact machine surfaces point to the same core contracts."""
    root=pathlib.Path(args.root)
    surfaces=["README.md","llms.txt","agentpress/AGENT_START_HERE.md","agentpress/agent-instructions.json","agentpress/schemas/index.json"]
    required_terms=["llms.txt","agentpress/agent-instructions.json","agentpress/schemas/index.json","python3 scripts/agentpress.py doctor --json","landing-receipt"]
    checked=[]; errors=[]
    for rel in surfaces:
        path=root/rel
        if not path.exists():
            errors.append(f"missing first-contact surface: {rel}"); continue
        text=path.read_text(encoding='utf-8', errors='replace')
        checked.append(rel)
        for term in required_terms[:3]:
            if term not in text and rel != 'agentpress/schemas/index.json': errors.append(f"{rel} missing contract reference: {term}")
    # exact command surfaces should be explicit on human+agent entrypoints, not every JSON index.
    for rel in ["README.md","llms.txt","agentpress/AGENT_START_HERE.md"]:
        path=root/rel
        if path.exists():
            text=path.read_text(encoding='utf-8', errors='replace')
            for term in required_terms[3:]:
                if term not in text: errors.append(f"{rel} missing execution/proof instruction: {term}")
    payload={"schema_version":"2026-05-03.agentpress-consistency-check.v1","consistent":not errors,"status":"ok" if not errors else "fail","checked":checked,"required_terms":required_terms,"errors":errors}
    print(json.dumps(payload, indent=2) if args.json else payload['status'])
    return 0 if not errors else 1

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("out"); p.add_argument("--title", required=True); p.add_argument("--canonical"); p.add_argument("--summary"); p.add_argument("--primary-task"); p.add_argument("--task-type", default="agent_native_publication")
    p = sub.add_parser("validate"); p.add_argument("out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("audit"); p.add_argument("out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("verify"); p.add_argument("out", nargs="?", default="."); p.add_argument("--json", action="store_true")
    p = sub.add_parser("schema"); p.add_argument("name", nargs="?"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("fetch"); p.add_argument("--base", default=CANONICAL_BASE_URL); p.add_argument("--out", default="agentpress-fetch"); p.add_argument("--asset", action="append", help="relative asset to fetch; repeatable; defaults to core machine entrypoints"); p.add_argument("--timeout", type=int, default=20); p.add_argument("--keep-going", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("discover"); p.add_argument("url", nargs="?"); p.add_argument("--out"); p.add_argument("--registry"); p.add_argument("--timeout", type=int, default=20); p.add_argument("--json", action="store_true"); p.add_argument("--self-register", action="store_true"); p.add_argument("--canonical-url", default=CANONICAL_BASE_URL); p.add_argument("--agent-id")
    p = sub.add_parser("negative-fixtures"); p.add_argument("--manifest", default="agentpress/fixtures/broken-bundles/expected-failures.json"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("feedback-submit"); p.add_argument("--example", action="store_true"); p.add_argument("--input"); p.add_argument("--template", default="agentpress/feedback/response-template.json"); p.add_argument("--rubric", default="agentpress/feedback/scoring-rubric.json"); p.add_argument("--agent-id"); p.add_argument("--agent-family", default="codex"); p.add_argument("--runtime-or-model"); p.add_argument("--target-url", default=CANONICAL_BASE_URL); p.add_argument("--json", action="store_true")
    p = sub.add_parser("consistency-check"); p.add_argument("root", nargs="?", default="."); p.add_argument("--json", action="store_true")
    p = sub.add_parser("adoption-status"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out"); p.add_argument("--json", action="store_true"); p.add_argument("--allow-needs-attention", action="store_true")
    p = sub.add_parser("payment-status"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("payment-intent"); p.add_argument("root", nargs="?", default="."); p.add_argument("--capability-id", required=True); p.add_argument("--agent-id", required=True); p.add_argument("--max-amount", default="0"); p.add_argument("--max-per-request"); p.add_argument("--currency", default="USD"); p.add_argument("--expires-utc"); p.add_argument("--out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-onboard", aliases=["adopt"]); p.add_argument("root", nargs="?", default="."); p.add_argument("--agent-id", default="local-agent"); p.add_argument("--runtime", default="unknown"); p.add_argument("--out", default="/tmp/agentpress-onboard"); p.add_argument("--bundle", default="agentpress/examples/api-docs-handoff"); p.add_argument("--suite", default="agentpress/self-tests/standard-suite.json"); p.add_argument("--index", default="agentpress/search/search-index.json"); p.add_argument("--discovery-channel", default="agent-onboard-cli"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--contact"); p.add_argument("--payment-capability-id", default="free_agentpress_bootstrap"); p.add_argument("--max-amount", default="0"); p.add_argument("--max-per-request"); p.add_argument("--currency", default="USD"); p.add_argument("--expires-utc"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("score"); p.add_argument("out")
    p = sub.add_parser("build"); p.add_argument("out"); p.add_argument("--out", dest="dest", required=True)
    p = sub.add_parser("list"); p.add_argument("root", nargs="?", default="agentpress/examples"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("build-all"); p.add_argument("root", nargs="?", default="agentpress/examples"); p.add_argument("--out", dest="dest", required=True); p.add_argument("--clean", action="store_true")
    p = sub.add_parser("index-articles"); p.add_argument("root", nargs="?", default="agentpress/examples"); p.add_argument("--out", default="agentpress/articles"); p.add_argument("--base-url", default="https://barneywohl.github.io/agentpress")
    p = sub.add_parser("doctor"); p.add_argument("root", nargs="?", default="."); p.add_argument("--json", action="store_true")
    p = sub.add_parser("eval"); p.add_argument("root", nargs="?", default="agentpress/examples")
    p = sub.add_parser("check-registry"); p.add_argument("root", nargs="?", default="agentpress/examples"); p.add_argument("--registry", default="agentpress/agentpress-registry.json")
    p = sub.add_parser("check-openapi"); p.add_argument("root", nargs="?", default="."); p.add_argument("--openapi", default="openapi.yaml")
    p = sub.add_parser("message"); msg = p.add_subparsers(dest="message_cmd", required=True)
    q = msg.add_parser("create-request"); q.add_argument("--capability", required=True); q.add_argument("--task", required=True); q.add_argument("--priority", choices=["P0","P1","P2","P3"], default="P1"); q.add_argument("--requester-id", required=True); q.add_argument("--out", required=True); q.add_argument("--request-id"); q.add_argument("--context-urls"); q.add_argument("--required-sources"); q.add_argument("--allowed-actions"); q.add_argument("--requires-human-approval"); q.add_argument("--prohibited-actions"); q.add_argument("--output-schema", default="https://barneywohl.github.io/agentpress/agentpress/schemas/agent-response-v1.schema.json"); q.add_argument("--deadline-utc")
    q = msg.add_parser("route"); q.add_argument("--capability", required=True); q.add_argument("--directory", default="agentpress/hub/routing/capability-index.json"); q.add_argument("--json", action="store_true")
    q = msg.add_parser("create-response"); q.add_argument("--request", required=True); q.add_argument("--responder-id", required=True); q.add_argument("--status", choices=["accepted","in_progress","completed","partial","rejected","escalated","timeout"], default="completed"); q.add_argument("--out", required=True); q.add_argument("--response-id"); q.add_argument("--confidence", type=float, default=0.8); q.add_argument("--result-inline"); q.add_argument("--result-bundle"); q.add_argument("--sources-used"); q.add_argument("--missing-checks"); q.add_argument("--actions-taken")
    q = msg.add_parser("inbox-init"); q.add_argument("--dir", default="agent-comms")
    q = msg.add_parser("register"); q.add_argument("--agent-id", required=True); q.add_argument("--capabilities", required=True); q.add_argument("--dir", default="agent-comms")
    q = msg.add_parser("send"); q.add_argument("--to", required=True); q.add_argument("--request", required=True); q.add_argument("--dir", default="agent-comms")
    q = msg.add_parser("broadcast"); q.add_argument("--capability", required=True); q.add_argument("--request", required=True); q.add_argument("--dir", default="agent-comms")
    q = msg.add_parser("inbox-check"); q.add_argument("--agent-id", required=True); q.add_argument("--dir", default="agent-comms"); q.add_argument("--json", action="store_true")
    q = msg.add_parser("claim"); q.add_argument("--message-id", required=True); q.add_argument("--agent-id", required=True); q.add_argument("--dir", default="agent-comms")
    q = msg.add_parser("complete"); q.add_argument("--message-id", required=True); q.add_argument("--agent-id", required=True); q.add_argument("--response", required=True); q.add_argument("--dir", default="agent-comms")
    q = msg.add_parser("agents"); q.add_argument("--dir", default="agent-comms"); q.add_argument("--json", action="store_true")
    q = msg.add_parser("validate"); q.add_argument("path"); q.add_argument("--json", action="store_true")
    q = msg.add_parser("thread-create"); q.add_argument("--request", required=True); q.add_argument("--out", required=True); q.add_argument("--thread-id")
    q = msg.add_parser("thread-append"); q.add_argument("--thread", required=True); q.add_argument("--message", required=True); q.add_argument("--out")
    p = sub.add_parser("submission-pack"); p.add_argument("--receipt", required=True); p.add_argument("--out", required=True); p.add_argument("--json", action="store_true")
    p = sub.add_parser("reputation-index"); p.add_argument("--landing-dir", default="agentpress/landing"); p.add_argument("--self-test-dir", default="agentpress/self-test"); p.add_argument("--receipt-dir", default="agentpress/receipts"); p.add_argument("--out", required=True); p.add_argument("--json", action="store_true")
    p = sub.add_parser("landing-receipt"); p.add_argument("--agent-id", required=True); p.add_argument("--runtime", required=True); p.add_argument("--discovery-channel", required=True); p.add_argument("--capability", action="append"); p.add_argument("--self-test-ref"); p.add_argument("--contact"); p.add_argument("--base-url", default="https://barneywohl.github.io/agentpress/"); p.add_argument("--landing-id"); p.add_argument("--out", required=True); p.add_argument("--json", action="store_true")
    p = sub.add_parser("landing-index"); p.add_argument("dir"); p.add_argument("--out", required=True); p.add_argument("--json", action="store_true")
    p = sub.add_parser("inbox-compile"); p.add_argument("inbox_dir"); p.add_argument("--out", required=True); p.add_argument("--json", action="store_true")
    p = sub.add_parser("bundle-diff"); p.add_argument("bundle_a"); p.add_argument("bundle_b"); p.add_argument("--json", action="store_true"); p.add_argument("--include-hashes", action="store_true"); p.add_argument("--allow-breaking", action="store_true")
    p = sub.add_parser("upgrade-check"); p.add_argument("current_bundle"); p.add_argument("latest_bundle"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("adapter-quickstart"); p.add_argument("--agent-type", choices=["codex","claude","gemini","glm","browser","all"], default="all"); p.add_argument("--out", required=True); p.add_argument("--json", action="store_true")
    p = sub.add_parser("adapter-quickstart-check"); p.add_argument("dir"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("handoff-create"); p.add_argument("--from-agent", required=True); p.add_argument("--to-agent", required=True); p.add_argument("--capability", required=True); p.add_argument("--context", required=True); p.add_argument("--partial-response"); p.add_argument("--instructions", required=True); p.add_argument("--parent-handoff-id"); p.add_argument("--handoff-id"); p.add_argument("--out", required=True)
    p = sub.add_parser("handoff-validate"); p.add_argument("path"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("receipt-create"); p.add_argument("--handoff", required=True); p.add_argument("--agent-id", required=True); p.add_argument("--status", choices=["accepted","completed","partial","rejected","blocked"], default="completed"); p.add_argument("--response"); p.add_argument("--notes"); p.add_argument("--next-actions"); p.add_argument("--receipt-id"); p.add_argument("--out", required=True)
    p = sub.add_parser("receipt-validate"); p.add_argument("path"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-route"); p.add_argument("--runtime", required=True, help="codex|claude|gemini|glm|browser|rag|crawler|mcp|eval_harness|workflow_agent|list"); p.add_argument("--intent", default="all", help="discover|install|verify|prove|submit|coordinate|all"); p.add_argument("--routes", default="agentpress/routes/agent-routes.json"); p.add_argument("--out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-traffic-audit"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/traffic/agent-traffic-audit.json"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("compatibility-matrix"); p.add_argument("--runtime", action="append", choices=["codex","claude","gemini","glm","browser","rag"]); p.add_argument("--out", default="agentpress/compatibility/compatibility-matrix.json"); p.add_argument("--workdir", default="/tmp/agentpress-compatibility-matrix"); p.add_argument("--bundle", default="agentpress/examples/api-docs-handoff"); p.add_argument("--suite", default="agentpress/self-tests/standard-suite.json"); p.add_argument("--index", default="agentpress/search/search-index.json"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("tools-manifest"); p.add_argument("--out", default="agentpress/tools/agentpress-tools.json"); p.add_argument("--base-url", default="https://barneywohl.github.io/agentpress/")
    p = sub.add_parser("tools-manifest-check"); p.add_argument("path", nargs="?", default="agentpress/tools/agentpress-tools.json"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("team-pack"); p.add_argument("--slug", required=True); p.add_argument("--display-name"); p.add_argument("--pack-type", choices=["team_capability_pack","person_capability_pack"], default="team_capability_pack"); p.add_argument("--capability", action="append", required=True); p.add_argument("--consent-source", choices=["explicit","public_source","internal_private_do_not_publish"], required=True); p.add_argument("--public-sources"); p.add_argument("--allowed-handoffs"); p.add_argument("--availability", default="available_for_agent_handoff"); p.add_argument("--canonical-url"); p.add_argument("--out", required=True); p.add_argument("--allow-private", action="store_true")
    p = sub.add_parser("team-pack-validate"); p.add_argument("path"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("self-test"); p.add_argument("--agent-id", required=True); p.add_argument("--bundle", default="agentpress/examples/api-docs-handoff"); p.add_argument("--suite", default="agentpress/self-tests/standard-suite.json"); p.add_argument("--out", default="agentpress/self-test/self-test-results.jsonl"); p.add_argument("--index", default="agentpress/search/search-index.json"); p.add_argument("--workdir", default="/tmp/agentpress-self-test"); p.add_argument("--run-id")
    p = sub.add_parser("index-search"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/search/search-index.json"); p.add_argument("--base-url", default="https://barneywohl.github.io/agentpress/"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("search"); p.add_argument("query"); p.add_argument("--index", default="agentpress/search/search-index.json"); p.add_argument("--limit", type=int, default=10); p.add_argument("--json", action="store_true")
    p = sub.add_parser("bundle"); p.add_argument("source"); p.add_argument("--out", required=True); p.add_argument("--title"); p.add_argument("--canonical-url"); p.add_argument("--primary-task"); p.add_argument("--dry-run", action="store_true"); p.add_argument("--strict", action="store_true"); p.add_argument("--force", action="store_true"); p.add_argument("--max-stale-days", type=int, default=30)
    p = sub.add_parser("install-script"); p.add_argument("--out", default="agentpress/install/install.py"); p.add_argument("--base-url", default="https://barneywohl.github.io/agentpress/"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("release-index"); p.add_argument("package"); p.add_argument("--manifest"); p.add_argument("--out", default="agentpress/releases/release-index.json"); p.add_argument("--base-url", default="https://barneywohl.github.io/agentpress/"); p.add_argument("--raw-base-url", default="https://raw.githubusercontent.com/barneywohl/agentpress/refs/heads/main/"); p.add_argument("--package-url"); p.add_argument("--manifest-url"); p.add_argument("--install-path", default="agentpress/install/install.py"); p.add_argument("--version", default="2026-05-03"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("package"); p.add_argument("root", nargs="?", default="."); p.add_argument("--format", choices=["tar", "zip"], default="tar"); p.add_argument("--out", default="dist/agentpress-offline.tar.gz")
    p = sub.add_parser("package-verify"); p.add_argument("package"); p.add_argument("--manifest"); p.add_argument("--workdir", default="/tmp/agentpress-package-verify"); p.add_argument("--keep-workdir", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("package-index"); p.add_argument("package"); p.add_argument("--manifest"); p.add_argument("--out", default="dist/agentpress-offline-index.json")
    args = ap.parse_args()
    if args.cmd == "init": init(args); return 0
    if args.cmd == "validate": return validate(args)
    if args.cmd == "audit": return audit(args)
    if args.cmd == "verify": return verify(args)
    if args.cmd == "schema": return schema_command(args)
    if args.cmd == "fetch": return fetch(args)
    if args.cmd == "discover": return discover_agentpress(args)
    if args.cmd == "negative-fixtures": return negative_fixtures(args)
    if args.cmd == "feedback-submit": return feedback_submit(args)
    if args.cmd == "consistency-check": return consistency_check(args)
    if args.cmd == "adoption-status": return adoption_status(args)
    if args.cmd == "payment-status": return payment_status(args)
    if args.cmd == "payment-intent": return payment_intent(args)
    if args.cmd in {"agent-onboard", "adopt"}: return agent_onboard(args)
    if args.cmd == "score": return score(args)
    if args.cmd == "build": return build(args)
    if args.cmd == "list": return list_examples(args)
    if args.cmd == "build-all": return build_all(args)
    if args.cmd == "index-articles": return index_articles(args)
    if args.cmd == "doctor": return doctor(args)
    if args.cmd == "eval": return eval_examples(args)
    if args.cmd == "check-registry": return check_registry(args)
    if args.cmd == "check-openapi": return check_openapi(args)
    if args.cmd == "submission-pack": return submission_pack(args)
    if args.cmd == "reputation-index": return reputation_index(args)
    if args.cmd == "landing-receipt": return landing_receipt(args)
    if args.cmd == "landing-index": return landing_index(args)
    if args.cmd == "inbox-compile": return inbox_compile(args)
    if args.cmd == "bundle-diff": return bundle_diff(args)
    if args.cmd == "upgrade-check": return upgrade_check(args)
    if args.cmd == "adapter-quickstart": return adapter_quickstart(args)
    if args.cmd == "adapter-quickstart-check": return adapter_quickstart_check(args)
    if args.cmd == "handoff-create": return handoff_create(args)
    if args.cmd == "handoff-validate": return handoff_validate(args)
    if args.cmd == "receipt-create": return receipt_create(args)
    if args.cmd == "receipt-validate": return receipt_validate(args)
    if args.cmd == "agent-route": return agent_route(args)
    if args.cmd == "agent-traffic-audit": return agent_traffic_audit(args)
    if args.cmd == "compatibility-matrix": return compatibility_matrix(args)
    if args.cmd == "tools-manifest": return tools_manifest(args)
    if args.cmd == "tools-manifest-check": return tools_manifest_check(args)
    if args.cmd == "team-pack": return team_pack(args)
    if args.cmd == "team-pack-validate": return team_pack_validate(args)
    if args.cmd == "self-test": return self_test(args)
    if args.cmd == "index-search": return build_search_index(args)
    if args.cmd == "search": return search_index(args)
    if args.cmd == "message": return message_command(args)
    if args.cmd == "bundle": return bundle_from_source(args)
    if args.cmd == "install-script": return install_script(args)
    if args.cmd == "release-index": return release_index(args)
    if args.cmd == "package": return package_bundle(args)
    if args.cmd == "package-verify": return package_verify(args)
    if args.cmd == "package-index": return package_index(args)
if __name__ == "__main__":
    sys.exit(main())
