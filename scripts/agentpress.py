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
  python3 scripts/agentpress.py score out-dir
  python3 scripts/agentpress.py build out-dir --out public-dir
"""
import argparse
import hashlib
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


def message_command(args):
    if args.message_cmd == "create-request": return message_create_request(args)
    if args.message_cmd == "route": return message_route(args)
    if args.message_cmd == "create-response": return message_create_response(args)
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

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("out"); p.add_argument("--title", required=True); p.add_argument("--canonical"); p.add_argument("--summary"); p.add_argument("--primary-task"); p.add_argument("--task-type", default="agent_native_publication")
    p = sub.add_parser("validate"); p.add_argument("out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("audit"); p.add_argument("out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("verify"); p.add_argument("out", nargs="?", default="."); p.add_argument("--json", action="store_true")
    p = sub.add_parser("schema"); p.add_argument("name", nargs="?"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("fetch"); p.add_argument("--base", default=CANONICAL_BASE_URL); p.add_argument("--out", default="agentpress-fetch"); p.add_argument("--asset", action="append", help="relative asset to fetch; repeatable; defaults to core machine entrypoints"); p.add_argument("--timeout", type=int, default=20); p.add_argument("--keep-going", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("negative-fixtures"); p.add_argument("--manifest", default="agentpress/fixtures/broken-bundles/expected-failures.json"); p.add_argument("--json", action="store_true")
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
    q = msg.add_parser("validate"); q.add_argument("path"); q.add_argument("--json", action="store_true")
    q = msg.add_parser("thread-create"); q.add_argument("--request", required=True); q.add_argument("--out", required=True); q.add_argument("--thread-id")
    q = msg.add_parser("thread-append"); q.add_argument("--thread", required=True); q.add_argument("--message", required=True); q.add_argument("--out")
    p = sub.add_parser("package"); p.add_argument("root", nargs="?", default="."); p.add_argument("--format", choices=["tar", "zip"], default="tar"); p.add_argument("--out", default="dist/agentpress-offline.tar.gz")
    args = ap.parse_args()
    if args.cmd == "init": init(args); return 0
    if args.cmd == "validate": return validate(args)
    if args.cmd == "audit": return audit(args)
    if args.cmd == "verify": return verify(args)
    if args.cmd == "schema": return schema_command(args)
    if args.cmd == "fetch": return fetch(args)
    if args.cmd == "negative-fixtures": return negative_fixtures(args)
    if args.cmd == "score": return score(args)
    if args.cmd == "build": return build(args)
    if args.cmd == "list": return list_examples(args)
    if args.cmd == "build-all": return build_all(args)
    if args.cmd == "index-articles": return index_articles(args)
    if args.cmd == "doctor": return doctor(args)
    if args.cmd == "eval": return eval_examples(args)
    if args.cmd == "check-registry": return check_registry(args)
    if args.cmd == "check-openapi": return check_openapi(args)
    if args.cmd == "message": return message_command(args)
    if args.cmd == "package": return package_bundle(args)
if __name__ == "__main__":
    sys.exit(main())
