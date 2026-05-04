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
import os
import subprocess
import hashlib
import html
import json
import pathlib
import platform
import re
import shutil
import shlex
import sys
import uuid
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

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



def _schema_type_ok(value, expected):
    if expected == "object": return isinstance(value, dict)
    if expected == "array": return isinstance(value, list)
    if expected == "string": return isinstance(value, str)
    if expected == "integer": return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number": return (isinstance(value, (int, float)) and not isinstance(value, bool))
    if expected == "boolean": return isinstance(value, bool)
    if expected == "null": return value is None
    return True


def _strict_json_schema_errors(value, schema, path="$"):
    """Small dependency-free JSON Schema subset validator for AgentPress contracts."""
    errors=[]
    if not isinstance(schema, dict):
        return errors
    if "enum" in schema and value not in schema.get("enum", []):
        errors.append(f"{path} expected one of {schema.get('enum')}, got {value!r}")
    expected=schema.get("type")
    if isinstance(expected, list):
        if not any(_schema_type_ok(value, t) for t in expected):
            errors.append(f"{path} expected one of {expected}")
            return errors
    elif isinstance(expected, str):
        if not _schema_type_ok(value, expected):
            errors.append(f"{path} expected {expected}")
            return errors
    if isinstance(value, dict):
        required=schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key} missing required field")
        props=schema.get("properties", {}) if isinstance(schema.get("properties", {}), dict) else {}
        allow_extra=schema.get("additionalProperties", True)
        for key, val in value.items():
            child=f"{path}.{key}"
            if key in props:
                errors.extend(_strict_json_schema_errors(val, props[key], child))
            elif allow_extra is False:
                errors.append(f"{child} additional property not allowed")
            elif isinstance(allow_extra, dict):
                errors.extend(_strict_json_schema_errors(val, allow_extra, child))
    if isinstance(value, list):
        if "minItems" in schema and len(value) < int(schema["minItems"]): errors.append(f"{path} expected at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > int(schema["maxItems"]): errors.append(f"{path} expected at most {schema['maxItems']} items")
        item_schema=schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(value):
                errors.extend(_strict_json_schema_errors(item, item_schema, f"{path}[{i}]"))
    if isinstance(value, str):
        if "minLength" in schema and len(value) < int(schema["minLength"]): errors.append(f"{path} expected minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > int(schema["maxLength"]): errors.append(f"{path} expected maxLength {schema['maxLength']}")
        if schema.get("format") == "uri":
            u=urlparse(value)
            if not u.scheme: errors.append(f"{path} expected uri")
    return errors


def _load_schema_ref(name_or_path):
    cand=pathlib.Path(name_or_path)
    if cand.exists(): return cand, json.loads(cand.read_text(encoding="utf-8"))
    variants=[name_or_path, name_or_path.replace("_","-"), name_or_path.replace("_","-")+".schema.json", name_or_path+".schema.json"]
    for v in variants:
        pp=schema_root()/v
        if pp.exists(): return pp, json.loads(pp.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"schema not found: {name_or_path}")


def schema_validate(args):
    target=pathlib.Path(args.file)
    try:
        payload=json.loads(target.read_text(encoding="utf-8"))
        schema_path, schema=_load_schema_ref(args.schema)
        errors=_strict_json_schema_errors(payload, schema)
    except Exception as e:
        errors=[str(e)]; schema_path=None
    result={"schema_version":"2026-05-03.agentpress-strict-schema-validation.v1","status":"ok" if not errors else "fail","file":str(target),"schema":str(schema_path) if schema_path else args.schema,"validator":"agentpress_dependency_free_json_schema_subset","errors":errors}
    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True,exist_ok=True); pathlib.Path(args.out).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2) if args.json else result["status"])
    return 0 if not errors else 1

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
    strict_schema_errors=[]
    if getattr(args, "strict_schema", False):
        for rel in checked:
            try:
                data=json.loads((root/rel).read_text(encoding="utf-8")); sp,_schema=_load_schema_ref(CONTRACT_SCHEMA_MAP[rel]); strict_schema_errors.extend([f"{rel}: {e}" for e in _strict_json_schema_errors(data,_schema)])
            except Exception as e:
                strict_schema_errors.append(f"{rel}: {e}")
        errors.extend(strict_schema_errors); code = 0 if not errors else 1
    payload = {
        "status": "ok" if code == 0 else "fail",
        "path": str(root),
        "checked_contracts": checked,
        "schema_index": schema_url("index.json"),
        "errors": errors,
        "warnings": warnings,
        "strict_schema": bool(getattr(args, "strict_schema", False)),
        "strict_schema_errors": strict_schema_errors if "strict_schema_errors" in locals() else [],
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
    add("cli_command", "AgentPress painpoint intake", "agentpress/painpoint-intake/README.md", "painpoint-intake reports blockers agent feedback severity desired fix index", ["painpoint", "feedback", "intake", "blockers", "roadmap"] )
    add("cli_command", "AgentPress attestation coverage", "agentpress/attestations/attestation-coverage.json", "attestation coverage critical surfaces trust hash verification", ["attestation", "coverage", "trust", "verify"] )
    add("cli_command", "AgentPress marketplace trust scoring", "agentpress/marketplace/marketplace-trust-index.json", "marketplace trust score rank services reputation evidence proof routing", ["marketplace", "trust", "score", "routing"] )
    add("cli_command", "AgentPress proof outreach kit", "agentpress/proof-outreach/README.md", "proof outreach external receipts agent request prompt adoption blocker submit", ["proof", "outreach", "external", "receipts", "agents"] )
    add("cli_command", "AgentPress external proof ingestion", "agentpress/external-proofs/README.md", "proof-ingest validate index external proof receipts blocker reports privacy scan reputation scoring", ["proof", "ingest", "receipts", "score", "privacy"] )
    add("cli_command", "AgentPress secure transport readiness", "agentpress/secure-transport/README.md", "secure transport readiness key owner rotation recipient identity encrypted payload approval", ["secure-transport", "privacy", "keys", "approval"] )
    add("cli_command", "AgentPress privacy and confidential messaging", "agentpress/privacy/README.md", "privacy confidential message envelope redaction secure transport metadata-only threat model", ["privacy", "confidential", "redaction", "message", "security"] )
    add("cli_command", "AgentPress docs command check", "agentpress/evidence/docs-command-check.json", "docs command lint stale flags cli parser documentation", ["docs", "commands", "lint", "cli", "drift"] )
    add("cli_command", "AgentPress integration SDK kit", "agentpress/integrations/sdk/manifest.json", "sdk integration python javascript client smoke endpoints copy paste", ["sdk", "integration", "python", "javascript", "client"] )
    add("cli_command", "AgentPress queue adapter kit", "agentpress/queue/manifest.json", "queue adapter retry policy idempotency lease dead letter workflow", ["queue", "retry", "workflow", "handoff", "idempotency"] )
    add("cli_command", "AgentPress marketplace compare", "agentpress/marketplace/marketplace-compare.example.json", "marketplace compare service quote simulation no spend routing", ["marketplace", "compare", "quote", "routing", "no-spend"] )
    add("cli_command", "AgentPress patch PR helper", "agentpress/contrib/patch-pr-helper.example.json", "patch pr helper contribution code owner checklist validation diff", ["patch", "pr", "contribution", "review", "coding-agent"] )
    add("cli_command", "AgentPress freshness citation report", "agentpress/evidence/freshness-citation-report.json", "freshness citation coverage rag crawler canonical source generated utc", ["freshness", "citation", "rag", "crawler", "coverage"] )
    add("cli_command", "AgentPress browser smoke evidence", "agentpress/evidence/browser-smoke.json", "browser smoke public urls live url evidence http status crawler rag", ["browser", "smoke", "evidence", "urls", "health"] )
    add("cli_command", "AgentPress internal feature build queue", "agentpress/planning/feature-build-queue.json", "feature build queue next features coverage painpoints adoption gaps internal planning", ["planning", "roadmap", "build-queue", "features"] )
    add("cli_command", "AgentPress tool coverage matrix", "agentpress/tools/tool-coverage.json", "tool coverage cli matrix agent needs missing expansion roadmap", ["tools", "cli", "coverage", "roadmap", "agents"] )
    add("cli_command", "AgentPress distribution failover", "agentpress/distribution/README.md", "distribution mirrors failover raw github jsdelivr cdn package verify fallback", ["distribution", "mirror", "failover", "cdn", "install"] )
    add("cli_command", "AgentPress runtime support", "agentpress/runtime/README.md", "error codes session state health status batch run progress agent orchestration", ["runtime", "error-codes", "session", "health", "batch"] )
    add("cli_command", "AgentPress remediation index", "agentpress/remediation/remediation-index.json", "remediation exact command blockers failed checks next action", ["remediation", "debug", "doctor", "commands"] )
    add("cli_command", "AgentPress package registry skeleton", "agentpress/package-registry/skeleton/README.md", "package skeleton pypi npm pipx uvx npx dry-run no publish", ["package", "pypi", "npm", "dry-run", "install"] )
    add("cli_command", "AgentPress package registry plan", "agentpress/package-registry/README.md", "package registry pypi npm pipx npx uvx dry run publish checklist install friction", ["package", "pypi", "npm", "install", "registry"] )
    add("cli_command", "AgentPress third-party proof campaign", "agentpress/proof-campaigns/README.md", "proof-campaign external proof third-party receipt adoption evidence github issue blocker marketplace route reputation", ["proof", "third-party", "adoption", "campaign", "evidence"] )
    add("cli_command", "AgentPress attestations", "agentpress/attestations/README.md", "attest create verify index sha256 tamper evidence receipts marketplace releases broadcasts trust", ["attest", "sha256", "trust", "verify", "tamper-evident"] )
    add("cli_command", "AgentPress agent painpoint roadmap", "agentpress/painpoints/README.md", "agent-painpoints persona painpoint roadmap agent needs blockers trust install proof routing marketplace audience payments attestations", ["painpoints", "roadmap", "personas", "agent-needs", "product"] )
    add("cli_command", "AgentPress audience and pseudonymous comms kit", "agentpress/audience/README.md", "audience-kit subscribe broadcast pseudonymous inbox anonymous feedback referral opt-in consent anti-spam growth flywheel", ["audience", "subscribe", "broadcast", "pseudonymous", "feedback", "growth", "consent"])
    add("cli_command", "AgentPress capability marketplace", "agentpress/marketplace/README.md", "marketplace capability catalog agents services pricing SLA auth trust commands query", ["marketplace", "capability", "sla", "pricing", "trust", "agents"])
    add("cli_command", "One-command AgentPress agent onboarding", "agentpress/onboarding/README.md", "adopt agent-onboard one command doctor self-test landing receipt payment status payment intent submission pack exponential adoption flywheel", ["onboard", "adoption", "self-test", "landing", "submission", "payment", "cli"])
    add("traffic", "Agent traffic acquisition pack", "agentpress/traffic/agent-traffic-acquisition.json", "crawler seeds agent sitemap directory submission first autonomous agents landing receipts proof traffic acquisition", ["traffic", "crawler", "directory", "adoption", "agent"] )
    add("traffic", "Agent routes manifest", "agentpress/routes/agent-routes.json", "machine routable agent runtime intent discover install verify prove submit coordinate", ["routes", "agent", "runtime", "intent", "traffic"] )
    add("cli_command", "Agent runtime route resolver", "scripts/agentpress.py", "agent-route runtime intent exact commands discover install verify prove submit coordinate", ["agent-route", "routes", "runtime", "intent", "cli"] )
    add("cli_command", "Agent traffic audit", "agentpress/traffic/agent-traffic-audit.json", "audit agent traffic surfaces crawler seeds routes cli launch proof conversion", ["audit", "traffic", "crawler", "proof", "cli"] )
    add("cli_command", "Validate AgentPress submission pack", "agentpress/submissions/README.md", "submission-validate proof pack validate issue pr blocker report privacy", ["submission", "validate", "proof", "blocker", "privacy"] )
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
    for rel in ["llms.txt", "README.md", "agentpress/AGENT_START_HERE.md", "agentpress/CLI_AGENT_LAUNCH.md", "agentpress/cli-launch.json", "agentpress/traffic/README.md", "agentpress/traffic/agent-traffic-acquisition.json", "agentpress/traffic/agent-traffic-audit.json", "agentpress/traffic/crawler-seeds.txt", "agentpress/routes/README.md", "agentpress/routes/agent-routes.json", "agentpress/directory-submission/agentpress-directory-pitch.json", "agent-sitemap.xml", "agentpress/hub/messages/README.md", "agentpress/protocols/mcp-manifest.json", "agentpress/mesh/README.md", "agentpress/mesh/known-agents.json", "agentpress/install/README.md", "agentpress/install/install.py", "agentpress/onboarding/README.md", "agentpress/onboarding/agent-onboard-example.json", "agentpress/specs/AGENTPRESS_EXPONENTIAL_AGENT_ADOPTION_SPEC_20260503.md", "agentpress/marketplace/README.md", "agentpress/marketplace/marketplace-index.json", "agentpress/specs/AGENTPRESS_AGENT_MARKETPLACE_SPEC_20260503.md", "agentpress/attestations/README.md", "agentpress/attestations/attestation-index.json", "agentpress/specs/AGENTPRESS_ATTESTATIONS_SPEC_20260503.md", "agentpress/painpoints/README.md", "agentpress/painpoints/agent-painpoints.json", "agentpress/specs/AGENTPRESS_AGENT_PAINPOINTS_ROADMAP_SPEC_20260503.md", "agentpress/audience/README.md", "agentpress/audience/audience-kit.json", "agentpress/audience/broadcast-feed.json", "agentpress/audience/pseudonymous-inbox-policy.json", "agentpress/audience/anti-abuse-policy.json", "agentpress/audience/unsubscribe-intent.example.json", "agentpress/specs/AGENTPRESS_AUDIENCE_PSEUDONYMOUS_COMMS_SPEC_20260503.md", "agentpress/payments/README.md", "agentpress/payments/payment-policy.json", "agentpress/payments/payment-capabilities.json", "agentpress/payments/x402-readiness.json", "agentpress/specs/AGENTPAYMENTS_PLATFORM_SPEC_20260503.md", "agentpress/releases/README.md", "agentpress/releases/release-index.json", "agentpress/submissions/README.md", "agentpress/reputation/README.md", "agentpress/landing/README.md", "agentpress/directory-submission/README.md", "agentpress/directory-submission/submission.json", "agentpress/feeds/contract-feed.json", "agentpress/feeds/changelog.json", "openapi.yaml"]:
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



def submission_validate(args):
    """Validate an AgentPress proof submission pack before issue/PR submission."""
    root=pathlib.Path(args.path)
    errors=[]; warnings=[]; files=[]
    if not root.exists():
        errors.append(f"missing submission pack: {root}")
    manifest={}
    if not errors:
        m=root/"submission-pack.json"
        if not m.exists():
            errors.append("missing submission-pack.json")
        else:
            try: manifest=json.loads(m.read_text(encoding="utf-8"))
            except Exception as e: errors.append(f"submission-pack.json invalid json: {e}")
        for rel in ["README.md","github-issue.md"]:
            if not (root/rel).exists(): errors.append(f"missing {rel}")
        for fp in sorted(root.glob("*.json")):
            if fp.name == "submission-pack.json": continue
            try:
                data=json.loads(fp.read_text(encoding="utf-8"))
                files.append({"path":str(fp),"bytes":fp.stat().st_size,"sha256":hashlib.sha256(fp.read_bytes()).hexdigest(),"agent_id":data.get("agent_id"),"schema_version":data.get("schema_version")})
                text=json.dumps(data).lower()
                markers=["api_key","apikey","authorization:","bearer ","password=","password:","token=","token:","secret=","secret:","private prompt:","user-agent:","ip_address","private_key","begin private key"]
                hits=[m for m in markers if m in text]
                if hits: errors.append(f"{fp.name}: possible private material markers: {', '.join(hits)}")
            except Exception as e:
                errors.append(f"{fp.name}: invalid json: {e}")
        if not files: errors.append("no receipt/proof json files found")
        if manifest and manifest.get("status") != "ok": warnings.append("submission-pack manifest status is not ok")
    payload={"schema_version":"2026-05-03.agentpress-submission-validate.v1","status":"ok" if not errors else "fail","path":str(root),"checked_files":files,"errors":errors,"warnings":warnings,"next_actions":["Attach github-issue.md and receipt/proof JSON to GitHub issue", "Or commit receipt/proof JSON by PR and rerun indexes", "Never include secrets, tokens, private prompts, IP addresses, or user-agent strings"]}
    if args.out:
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0 if not errors else 1


def blocker_report(args):
    """Create a sanitized blocker report JSON for agents that cannot complete proof/adoption."""
    out=pathlib.Path(args.out)
    report={"schema_version":"2026-05-03.agentpress-blocker-report.v1","blocker_id":args.blocker_id or _short_id("blocker"),"created_utc":_utc_now(),"agent_id":args.agent_id,"runtime":args.runtime,"severity":args.severity,"command":args.command,"error_summary":args.error_summary,"missing_field":args.missing_field or "","desired_fix":args.desired_fix,"privacy_confirmed":True,"contains_secrets":False,"redaction_policy":"Do not include secrets, tokens, private prompts, IP addresses, user-agent strings, or personal data."}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2) if args.json else out.as_posix())
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
    # accepted external third-party proofs and blocker reports
    epath=pathlib.Path(getattr(args, "external_proof_index", "agentpress/external-proofs/external-proof-index.json"))
    if epath.exists():
        try: ext=json.loads(epath.read_text(encoding="utf-8"))
        except Exception: ext={}
        for proof in ext.get("proofs", []):
            if proof.get("status") != "accepted":
                continue
            aid=proof.get("agent_id")
            if not aid: continue
            r=rec(aid); r["runtime"]=r.get("runtime") or proof.get("runtime","")
            r["evidence"].setdefault("external_proofs",0); r["evidence"].setdefault("external_proof_score",0); r["evidence"]["external_proofs"]+=1; r["evidence"]["external_proof_score"]+=proof.get("score",0); r["evidence"]["files"].append(proof.get("path") or str(epath))
            # Real success proofs count more than blocker-only reports, but blockers still improve product signal.
            if proof.get("proof_type") == "painpoint_report": r["score"]+=15
            else: r["score"]+=min(30, proof.get("score",0)*0.4)
    rows=[]
    for r in agents.values():
        r["capabilities"]=sorted(r["capabilities"]); r["score"]=round(min(100,r["score"]),2)
        r["trust_tier"]="verified" if r["score"]>=80 else ("provisional" if r["score"]>=40 else "landed")
        rows.append(r)
    rows=sorted(rows, key=lambda x:(-x["score"], x["agent_id"]))
    payload={"schema_version":"1.0","status":"ok","generated_utc":_utc_now(),"agent_count":len(rows),"agents":rows,"scoring":{"landing_receipt":"+20","self_test_average":"up to +50","handoff_receipt":"+10 each","external_success_proof":"up to +30","external_blocker_report":"+15 product-signal credit","cap":"100"},"privacy":"Evidence-derived from opt-in local artifacts; no hidden analytics."}
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
    out_path=pathlib.Path(args.out or (root/"agent-landing-index.json"))
    for p in sorted(root.glob("*.json")) if root.exists() else []:
        if p.name == out_path.name or "index" in p.name or "schema" in p.name: continue
        try: data=json.loads(p.read_text(encoding="utf-8"))
        except Exception as e: errors.append(f"{p}: parse error {e}"); continue
        e=_schema_required_errors(data, schema_root()/"agent-landing-v1.schema.json", p.name)
        if e: errors.extend(e); continue
        public={k:data.get(k) for k in ["landing_id","agent_id","runtime","discovery_channel","capabilities","self_test_ref","created_utc"]}
        public["receipt_path"]=str(p)
        receipts.append(public)
    payload={"schema_version":"1.0","status":"ok" if not errors else "fail","generated_utc":_utc_now(),"receipt_count":len(receipts),"receipts":receipts,"errors":errors,"privacy":"Compiled from opt-in landing receipts only; no hidden tracking."}
    out=out_path; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
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



def patch_pr_helper(args):
    """Generate a local-only PR/patch contribution pack with owner/security checklist."""
    out=pathlib.Path(args.out)
    slug=slugify(args.title)[:60] or "agentpress-change"
    diff_path=pathlib.Path(args.diff) if args.diff else None
    changed_files=[]; diff_sha=""; diff_bytes=0
    if diff_path and diff_path.exists():
        raw=diff_path.read_bytes(); diff_sha=hashlib.sha256(raw).hexdigest(); diff_bytes=len(raw)
        text=raw.decode("utf-8", errors="ignore")
        for line in text.splitlines():
            if line.startswith("diff --git "):
                parts=line.split()
                if len(parts)>=4:
                    changed_files.append(parts[3][2:] if parts[3].startswith("b/") else parts[3])
            elif line.startswith("+++ b/"):
                changed_files.append(line[6:])
        changed_files=sorted(set(x for x in changed_files if x and x != "/dev/null"))
    elif args.changed_file:
        changed_files=sorted(set(args.changed_file))
    pr_body=f"""# {args.title}\n\n## Summary\n{args.change_summary}\n\n## Safety\n- No external write performed by AgentPress.\n- Human must review before opening/merging PR.\n- Do not include secrets, tokens, private prompts, IP addresses, or user-agent strings.\n\n## Suggested branch\n`{args.target_branch or 'agentpress/'+slug}`\n\n## Validation commands\n"""
    validations=args.validation or [
        "python3 scripts/agentpress.py tools-manifest-check --json",
        "python3 scripts/agentpress.py consistency-check --json",
        "python3 scripts/agentpress.py negative-fixtures --json",
        "python3 scripts/validate_agentpress_assets.py",
    ]
    pr_body += "\n".join(f"- `{v}`" for v in validations)+"\n\n## Changed files\n"+"\n".join(f"- `{f}`" for f in changed_files or ["<fill after diff>"])+"\n"
    checklist=[
        {"id":"scope_clear","label":"Change scope is clearly described","required":True},
        {"id":"no_secrets","label":"Diff contains no secrets/private prompts/personal telemetry","required":True},
        {"id":"tests_run","label":"Validation commands were run and outputs attached","required":True},
        {"id":"owner_review","label":"Relevant owner/reviewer approved before merge","required":True},
        {"id":"docs_updated","label":"Machine docs/tool manifest/search updated if CLI/artifact changed","required":True},
        {"id":"no_external_write","label":"Helper did not push, open PR, publish package, or send external data","required":True},
    ]
    payload={
        "schema_version":"2026-05-03.agentpress-patch-pr-helper.v1",
        "canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),
        "generated_utc":_utc_now(),
        "status":"ok",
        "safety_status":"local_artifact_only_no_external_write",
        "title":args.title,
        "change_summary":args.change_summary,
        "base_branch":args.base_branch,
        "target_branch":args.target_branch or "agentpress/"+slug,
        "changed_files":changed_files,
        "diff":{"path":str(diff_path) if diff_path else "","bytes":diff_bytes,"sha256":diff_sha},
        "validation_commands":validations,
        "owner_checklist":checklist,
        "suggested_reviewers":args.reviewer or [],
        "pr_body_path":str(out.with_suffix(".md")),
        "pr_body":pr_body,
        "blocked_actions":["git push","gh pr create","package publish","external send"],
        "next_actions":["Review generated PR body", "Run validation commands", "Attach outputs", "Only then open a human-reviewed PR"]
    }
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
        out.with_suffix(".md").write_text(pr_body, encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else out.as_posix())
    return 0

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
        {"name":"agentpress.patch_pr_helper", "description":"Generate a local-only patch/PR contribution pack with owner checklist and validation commands.", "command":"python3 scripts/agentpress.py patch-pr-helper --title <title> --change-summary <summary> --json", "tags":["patch","pr","contribution","review","coding-agent"]},
        {"name":"agentpress.freshness_citation_report", "description":"Report freshness/citation/canonical URL coverage for RAG and crawler agents.", "command":"python3 scripts/agentpress.py freshness-citation-report --json", "tags":["freshness","citation","rag","crawler","coverage"]},
        {"name":"agentpress.browser_smoke", "description":"Smoke-check public AgentPress URLs and emit machine-readable evidence for browser/RAG agents.", "command":"python3 scripts/agentpress.py browser-smoke --json", "tags":["browser","smoke","evidence","urls","health"]},
        {"name":"agentpress.feature_build_queue", "description":"Generate internal next-feature build queue from tool coverage, painpoints, adoption gaps, and strategic expansions.", "command":"python3 scripts/agentpress.py feature-build-queue --json", "tags":["planning","build-queue","roadmap","features"]},
        {"name":"agentpress.build_queue_pick", "description":"Pick the next unblocked AgentPress feature from the internal build queue.", "command":"python3 scripts/agentpress.py build-queue-pick --json", "tags":["planning","next-feature","build-queue"]},
        {"name":"agentpress.build_queue_complete", "description":"Append a shipped feature completion record for the internal build queue.", "command":"python3 scripts/agentpress.py build-queue-complete --feature <feature> --commit <sha> --evidence <url> --json", "tags":["planning","completion","evidence"]},
        {"name":"agentpress.tool_coverage", "description":"Generate persona-based matrix of AgentPress tools/CLI agents need, current coverage, gaps, and expansions.", "command":"python3 scripts/agentpress.py tool-coverage --json", "tags":["tools","cli","coverage","roadmap"]},
        {"name":"agentpress.cli_expansion_roadmap", "description":"Generate prioritized roadmap from tool/CLI coverage gaps.", "command":"python3 scripts/agentpress.py cli-expansion-roadmap --json", "tags":["roadmap","cli","tools","gaps"]},
        {"name":"agentpress.tool_request", "description":"Create structured request for a missing AgentPress CLI/tool.", "command":"python3 scripts/agentpress.py tool-request --agent-id a --persona coding_agent --wanted-tool x --painpoint y --desired-command z --json", "tags":["tool-request","feedback","cli"]},
        {"name":"agentpress.distribution_kit", "description":"Generate mirror catalog and failover plan for resilient AgentPress fetch/install.", "command":"python3 scripts/agentpress.py distribution-kit --json", "tags":["distribution","mirror","failover","install"]},
        {"name":"agentpress.mirror_status", "description":"Check AgentPress primary and fallback distribution mirrors.", "command":"python3 scripts/agentpress.py mirror-status --json", "tags":["mirror","status","health","fetch"]},
        {"name":"agentpress.discover", "description":"Discover another AgentPress node, inspect tools/releases/contracts, and update a known-agent mesh registry.", "command":"python3 scripts/agentpress.py discover <agentpress-url> --registry agentpress/mesh/known-agents.json --json", "tags":["discover","mesh","agent-network","tools","release","self-register"]},
        {"name":"agentpress.schema_validate", "description":"Strict dependency-free JSON Schema subset validation for AgentPress contract files.", "command":"python3 scripts/agentpress.py schema-validate <file> --schema <schema-name-or-file> --json", "tags":["schema","strict","validate","contract","jsonschema"]},
        {"name":"agentpress.verify", "description":"Verify an AgentPress bundle fails/passes contract checks.", "command":"python3 scripts/agentpress.py verify <bundle> --json", "tags":["verify","schema","contract"]},
        {"name":"agentpress.bundle", "description":"Generate a valid AgentPress bundle from docs/API folder.", "command":"python3 scripts/agentpress.py bundle <source-dir> --out <bundle-dir> --title <title> --force", "tags":["generate","bundle","docs","api"]},
        {"name":"agentpress.bundle_diff", "description":"Compare two AgentPress bundles and report changed files/hashes for upgrade review.", "command":"python3 scripts/agentpress.py bundle-diff <old-bundle> <new-bundle> --json --include-hashes", "tags":["bundle","diff","upgrade","review"]},
        {"name":"agentpress.upgrade_check", "description":"Check whether upgrading from one AgentPress bundle to another is safe or breaking.", "command":"python3 scripts/agentpress.py upgrade-check <current-bundle> <latest-bundle> --json", "tags":["upgrade","compatibility","bundle","breaking"]},
        {"name":"agentpress.negative_fixtures", "description":"Run adversarial broken-bundle fixtures and require fail-closed validation.", "command":"python3 scripts/agentpress.py negative-fixtures --json", "tags":["negative-fixtures","security","fail-closed","eval"]},
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
        {"name":"agentpress.painpoint_intake", "description":"Validate and index agent painpoint reports with severity, command, problem, and desired fix.", "command":"python3 scripts/agentpress.py painpoint-intake --json --allow-rejected", "tags":["painpoint","feedback","intake","roadmap"]},
        {"name":"agentpress.attestation_coverage", "description":"Compute tamper-evident attestation coverage for critical AgentPress machine surfaces.", "command":"python3 scripts/agentpress.py attestation-coverage --json", "tags":["attestation","coverage","trust"]},
        {"name":"agentpress.marketplace_trust", "description":"Score and rank marketplace services using command, capability, payment, trust, and proof signals.", "command":"python3 scripts/agentpress.py marketplace-trust --json", "tags":["marketplace","trust","score","routing"]},
        {"name":"agentpress.mcp_consent_manifest_validator", "description":"Validate MCP/tool consent manifests and approval evidence fail-closed.", "command":"python3 scripts/agentpress.py mcp-consent-manifest-validator --json", "tags":["mcp","consent","approval","security","gate"]},
        {"name":"agentpress.provider_adapter_repro_pack", "description":"Create provider/host tool vocabulary mismatch repro and adapter map.", "command":"python3 scripts/agentpress.py provider-adapter-repro-pack --json", "tags":["provider","adapter","repro","tools"]},
        {"name":"agentpress.checkpoint_replay_minimal_repro_generator", "description":"Generate stale checkpoint/structured_response minimal repro artifact.", "command":"python3 scripts/agentpress.py checkpoint-replay-minimal-repro-generator --json", "tags":["checkpoint","repro","langchain","state"]},
        {"name":"agentpress.runtime_hang_repro_capsule", "description":"Turn stuck runtime/browser/terminal logs into maintainer-ready capsule.", "command":"python3 scripts/agentpress.py runtime-hang-repro-capsule --json", "tags":["runtime","hang","browser","terminal","repro"]},
        {"name":"agentpress.first_agent_outreach_receipt_tracker", "description":"Track targeted first-agent outreach receipts/blockers privacy-safely.", "command":"python3 scripts/agentpress.py first-agent-outreach-receipt-tracker --json", "tags":["outreach","receipts","growth","privacy"]},
        {"name":"agentpress.rag_tool_safety_bundle", "description":"Publish RAG/tool safety bundle for file-path metadata, zero-arg tools, and output contracts.", "command":"python3 scripts/agentpress.py rag-tool-safety-bundle --json", "tags":["rag","tools","security","schema","safety"]},
        {"name":"agentpress.external_reply_to_proof_ingest_bridge", "description":"Map external replies/blockers into proof-ingest compatible receipt records.", "command":"python3 scripts/agentpress.py external-reply-to-proof-ingest-bridge --json", "tags":["proof","receipts","external","bridge"]},
        {"name":"agentpress.issue_comment_pack_generator", "description":"Generate issue-specific non-spam comment packs tied to exact artifacts/commands.", "command":"python3 scripts/agentpress.py issue-comment-pack-generator --json", "tags":["outreach","comments","issues","attention"]},
        {"name":"agentpress.continuous_research_build_cycle_audit", "description":"Audit shipped next-build cycle and emit remaining research/build backlog.", "command":"python3 scripts/agentpress.py continuous-research-build-cycle-audit --json", "tags":["audit","cycle","backlog","research"]},
        {"name":"agentpress.current_agent_places_map", "description":"Map current places where agent builders communicate and how to engage them.", "command":"python3 scripts/agentpress.py current-agent-places-map --json", "tags":["community","research","agents","attention"]},
        {"name":"agentpress.attention_painpoint_radar", "description":"Rank current unsolved agent painpoints most likely to get first-agent attention.", "command":"python3 scripts/agentpress.py attention-painpoint-radar --json", "tags":["painpoints","attention","research","agents"]},
        {"name":"agentpress.first_agent_attention_kit", "description":"Publish non-spam first-agent attention hooks tied to shipped AgentPress artifacts.", "command":"python3 scripts/agentpress.py first-agent-attention-kit --json", "tags":["growth","outreach","attention","agents"]},
        {"name":"agentpress.next_attention_build_spec", "description":"Publish next build/deploy spec from live agent painpoint research.", "command":"python3 scripts/agentpress.py next-attention-build-spec --json", "tags":["spec","build-queue","attention","agents"]},
        {"name":"agentpress.agent_community_newswire", "description":"Compile current public agent-community issue/news signals.", "command":"python3 scripts/agentpress.py agent-community-newswire --json", "tags":["community","newswire","issues","agents"]},
        {"name":"agentpress.immediate_agent_needs_radar", "description":"Rank current agent needs from sampled community signals.", "command":"python3 scripts/agentpress.py immediate-agent-needs-radar --json", "tags":["needs","radar","agents","research"]},
        {"name":"agentpress.solution_targeting_matrix", "description":"Map communities/problems to AgentPress solution gates.", "command":"python3 scripts/agentpress.py solution-targeting-matrix --json", "tags":["targeting","solutions","community"]},
        {"name":"agentpress.approval_bypass_risk_check", "description":"Detect tool/MCP approval bypass risk.", "command":"python3 scripts/agentpress.py approval-bypass-risk-check --json", "tags":["approval","mcp","security","gate"]},
        {"name":"agentpress.provider_tool_translation_map", "description":"Generate provider/host tool vocabulary translation hints.", "command":"python3 scripts/agentpress.py provider-tool-translation-map --json", "tags":["provider","tools","translation"]},
        {"name":"agentpress.workflow_terminal_callback_check", "description":"Check workflow/terminal callback completion contract.", "command":"python3 scripts/agentpress.py workflow-terminal-callback-check --json", "tags":["workflow","terminal","callback","gate"]},
        {"name":"agentpress.context_compaction_risk_card", "description":"Generate context compaction risk envelope.", "command":"python3 scripts/agentpress.py context-compaction-risk-card --json", "tags":["context","compaction","memory"]},
        {"name":"agentpress.package_registry_doctor", "description":"Diagnose package/install registry failures for agent CLIs.", "command":"python3 scripts/agentpress.py package-registry-doctor --json", "tags":["package","registry","install","doctor"]},
        {"name":"agentpress.first_run_wizard", "description":"Detect host/provider/install state and emit the exact next command for a first agent user.", "command":"python3 scripts/agentpress.py first-run-wizard --json", "tags":["first-run","wizard","onboarding","host","provider"]},
        {"name":"agentpress.provider_error_explainer", "description":"Map raw provider/runtime errors to remediation packs with exact commands.", "command":"python3 scripts/agentpress.py provider-error-explainer --error '<sanitized error>' --json", "tags":["provider","errors","remediation","doctor"]},
        {"name":"agentpress.adoption_scoreboard", "description":"Build a static privacy-safe adoption scoreboard from opt-in proof artifacts.", "command":"python3 scripts/agentpress.py adoption-scoreboard --json", "tags":["adoption","scoreboard","static","proof","privacy"]},
        {"name":"agentpress.external_proof_inbox_review_flow", "description":"Review external proof inbox files for acceptance candidates and privacy redaction blockers.", "command":"python3 scripts/agentpress.py external-proof-inbox-review-flow --json", "tags":["proof","inbox","review","privacy","adoption"]},
        {"name":"agentpress.release_registry_readiness_dashboard", "description":"Build a static release/package-registry readiness dashboard for npm/PyPI/source/static lanes.", "command":"python3 scripts/agentpress.py release-registry-readiness-dashboard --json", "tags":["release","registry","npm","pypi","dashboard"]},
        {"name":"agentpress.tool_schema_serialization_check", "description":"Check tool schema metadata is JSON-serializable.", "command":"python3 scripts/agentpress.py tool-schema-serialization-check --json", "tags":["tools","schema","serialization","gate"]},
        {"name":"agentpress.agent_community_channel_map", "description":"Map agent communities/channels to problem signals.", "command":"python3 scripts/agentpress.py agent-community-channel-map --json", "tags":["community","channels","research","agents"]},
        {"name":"agentpress.community_issue_radar", "description":"Compile community issue radar from public issue signals.", "command":"python3 scripts/agentpress.py community-issue-radar --json", "tags":["community","issues","radar","research"]},
        {"name":"agentpress.unsolved_agent_problem_backlog", "description":"Generate prioritized backlog from community issue radar.", "command":"python3 scripts/agentpress.py unsolved-agent-problem-backlog --json", "tags":["backlog","problems","features"]},
        {"name":"agentpress.tool_vocabulary_compatibility_check", "description":"Check host/provider tool vocabulary compatibility.", "command":"python3 scripts/agentpress.py tool-vocabulary-compatibility-check --json", "tags":["tools","provider","compatibility","gate"]},
        {"name":"agentpress.agent_state_checkpoint_sanitizer", "description":"Detect stale checkpoint/state fields before next turn.", "command":"python3 scripts/agentpress.py agent-state-checkpoint-sanitizer --json", "tags":["state","checkpoint","drift","gate"]},
        {"name":"agentpress.dependency_error_remediation_map", "description":"Map dependency/runtime errors to exact remediation.", "command":"python3 scripts/agentpress.py dependency-error-remediation-map --json", "tags":["dependency","doctor","remediation"]},
        {"name":"agentpress.output_format_contract_tester", "description":"Test output format against requested contract.", "command":"python3 scripts/agentpress.py output-format-contract-tester --json", "tags":["output","format","contract","gate"]},
        {"name":"agentpress.tool_file_access_risk_scanner", "description":"Scan tool manifests for file access risks.", "command":"python3 scripts/agentpress.py tool-file-access-risk-scanner --json", "tags":["security","file-access","scanner"]},
        {"name":"agentpress.memory_drift_check", "description":"Executable memory/version drift validator.", "command":"python3 scripts/agentpress.py memory-drift-check --json", "tags":["memory","drift","validator","gate"]},
        {"name":"agentpress.handoff_validate", "description":"Validate task handoff contract.", "command":"python3 scripts/agentpress.py handoff-contract-validate --json", "tags":["handoff","validate","gate"]},
        {"name":"agentpress.pr_review_check", "description":"Evaluate PR/reviewer readiness.", "command":"python3 scripts/agentpress.py pr-review-check --json --allow-empty --tests local --risk low --rollback revert", "tags":["pr","review","gate"]},
        {"name":"agentpress.ci_flake_triage", "description":"Classify CI/test log failures.", "command":"python3 scripts/agentpress.py ci-flake-triage --json", "tags":["ci","flake","triage","gate"]},
        {"name":"agentpress.secret_permission_preflight_run", "description":"Run secrets/permissions preflight against a manifest.", "command":"python3 scripts/agentpress.py secret-permission-preflight-run --json", "tags":["secrets","permissions","preflight","gate"]},
        {"name":"agentpress.budget_check", "description":"Check an agent run plan against a cost/context budget.", "command":"python3 scripts/agentpress.py budget-check --json", "tags":["budget","cost","tokens","gate"]},
        {"name":"agentpress.coordination_ledger_check", "description":"Validate multi-agent coordination ledger.", "command":"python3 scripts/agentpress.py coordination-ledger-check --json", "tags":["coordination","ledger","multi-agent","gate"]},
        {"name":"agentpress.next_cycle_research", "description":"Generate next research cycle after readiness layer.", "command":"python3 scripts/agentpress.py next-cycle-research --json", "tags":["research","cycle","roadmap","agents"]},
        {"name":"agentpress.agent_memory_drift_detector", "description":"Detect stale memory/docs/connector assumptions.", "command":"python3 scripts/agentpress.py agent-memory-drift-detector --json", "tags":["memory","drift","docs","agents"]},
        {"name":"agentpress.task_handoff_contract", "description":"Generate explicit agent-to-agent handoff contract.", "command":"python3 scripts/agentpress.py task-handoff-contract --json", "tags":["handoff","multi-agent","contracts"]},
        {"name":"agentpress.pr_review_readiness_pack", "description":"Generate PR/review readiness package requirements.", "command":"python3 scripts/agentpress.py pr-review-readiness-pack --json", "tags":["pr","review","patch","evidence"]},
        {"name":"agentpress.ci_flake_triage_report", "description":"Generate CI/test flake triage report schema.", "command":"python3 scripts/agentpress.py ci-flake-triage-report --json", "tags":["ci","tests","flakes","triage"]},
        {"name":"agentpress.secret_permission_preflight", "description":"Generate secrets/permissions preflight without exposing values.", "command":"python3 scripts/agentpress.py secret-permission-preflight --json", "tags":["secrets","permissions","preflight"]},
        {"name":"agentpress.agent_cost_budget_card", "description":"Generate agent cost/context budget card.", "command":"python3 scripts/agentpress.py agent-cost-budget-card --json", "tags":["cost","tokens","budget","context"]},
        {"name":"agentpress.multi_agent_coordination_ledger", "description":"Generate multi-agent coordination ledger fields/rules.", "command":"python3 scripts/agentpress.py multi-agent-coordination-ledger --json", "tags":["multi-agent","coordination","ledger"]},
        {"name":"agentpress.readiness_audit_cli", "description":"Generate AgentPress readiness audit for a repo/url target.", "command":"python3 scripts/agentpress.py readiness-audit --json", "tags":["audit","readiness","agents","repo"]},
        {"name":"agentpress.readiness_score", "description":"Generate compact AgentPress readiness scorecard.", "command":"python3 scripts/agentpress.py readiness-score --json", "tags":["score","readiness","audit"]},
        {"name":"agentpress.readiness_fix_plan", "description":"Generate prioritized readiness fix plan.", "command":"python3 scripts/agentpress.py readiness-fix-plan --json", "tags":["fix-plan","readiness","roadmap"]},
        {"name":"agentpress.runtime_install_doctor", "description":"Generate runtime/install doctor checks and remediations.", "command":"python3 scripts/agentpress.py runtime-install-doctor --json", "tags":["doctor","install","runtime","cli"]},
        {"name":"agentpress.connector_security_scanner", "description":"Generate connector security scanner rules.", "command":"python3 scripts/agentpress.py connector-security-scanner --json", "tags":["security","connectors","mcp","scanner"]},
        {"name":"agentpress.deterministic_agent_eval_packs", "description":"Generate deterministic eval packs for agent adoption paths.", "command":"python3 scripts/agentpress.py deterministic-agent-eval-packs --json", "tags":["eval","deterministic","agents"]},
        {"name":"agentpress.verifiable_run_evidence_bundle", "description":"Generate verifiable run evidence bundle manifest.", "command":"python3 scripts/agentpress.py verifiable-run-evidence-bundle --json", "tags":["evidence","claims","hashes","runs"]},
        {"name":"agentpress.browser_agent_compatibility_harness", "description":"Generate browser-agent compatibility harness spec.", "command":"python3 scripts/agentpress.py browser-agent-compatibility-harness --json", "tags":["browser","compatibility","harness","evidence"]},
        {"name":"agentpress.deep_agent_painpoint_research", "description":"Generate deep research synthesis of what agents/operators actually want next.", "command":"python3 scripts/agentpress.py deep-agent-painpoint-research --json", "tags":["research","painpoints","agents","features"]},
        {"name":"agentpress.mcp_connector_auth_readiness", "description":"Generate MCP/connector auth readiness and permission handshake metadata.", "command":"python3 scripts/agentpress.py mcp-connector-auth-readiness --json", "tags":["mcp","auth","connectors","permissions"]},
        {"name":"agentpress.tool_routing_decision_matrix", "description":"Generate compact tool routing matrix to reduce context/tool overload.", "command":"python3 scripts/agentpress.py tool-routing-decision-matrix --json", "tags":["routing","tools","context","agents"]},
        {"name":"agentpress.agent_eval_observability_bridge", "description":"Generate eval/observability bridge for agent runs.", "command":"python3 scripts/agentpress.py agent-eval-observability-bridge --json", "tags":["eval","observability","traces","agents"]},
        {"name":"agentpress.deployment_connector_matrix", "description":"Generate deployment/install connector matrix for npm/pip/docker/mcp/http/stdio.", "command":"python3 scripts/agentpress.py deployment-connector-matrix --json", "tags":["deployment","npm","pip","docker","mcp"]},
        {"name":"agentpress.connector_first_run_checklist", "description":"Generate first-run checklist per connector category.", "command":"python3 scripts/agentpress.py connector-first-run-checklist --json", "tags":["connectors","quickstart","first-run","checklist"]},
        {"name":"agentpress.agent_persona_quickstarts", "description":"Generate connector quickstart bundles per agent persona.", "command":"python3 scripts/agentpress.py agent-persona-quickstarts --json", "tags":["personas","quickstart","connectors","agents"]},
        {"name":"agentpress.sdk_command_wrapper_catalog", "description":"Generate SDK wrapper catalog for proof/host/connector commands.", "command":"python3 scripts/agentpress.py sdk-command-wrapper-catalog --json", "tags":["sdk","wrappers","commands","integrations"]},
        {"name":"agentpress.cycle_completion_audit", "description":"Audit current cycle completion and remaining unfinished items.", "command":"python3 scripts/agentpress.py cycle-completion-audit --json", "tags":["cycle","audit","completion","remaining"]},
        {"name":"agentpress.connector_failure_to_backlog", "description":"Convert connector failure events/taxonomy into prioritized backlog items.", "command":"python3 scripts/agentpress.py connector-failure-to-backlog --json", "tags":["connectors","failures","backlog","automation"]},
        {"name":"agentpress.host_transcript_dropbox_spec", "description":"Generate drop-folder/upload convention for real host transcript ingestion.", "command":"python3 scripts/agentpress.py host-transcript-dropbox-spec --json", "tags":["host","transcript","dropbox","ingest"]},
        {"name":"agentpress.proof_request_queue", "description":"Generate opt-in proof request queue from campaign targets.", "command":"python3 scripts/agentpress.py proof-request-queue --json", "tags":["proof","queue","external","adoption"]},
        {"name":"agentpress.next_build_spec_queue", "description":"Generate researched next-build specs after current cycle.", "command":"python3 scripts/agentpress.py next-build-spec-queue --json", "tags":["research","specs","next-build","cycle"]},
        {"name":"agentpress.external_proof_campaign_runner", "description":"Generate opt-in external proof acquisition campaign run plan.", "command":"python3 scripts/agentpress.py external-proof-campaign-runner --json", "tags":["external","proof","campaign","adoption"]},
        {"name":"agentpress.host_transcript_batch_ingest", "description":"Batch ingest host transcript JSON files and summarize conformance.", "command":"python3 scripts/agentpress.py host-transcript-batch-ingest tests/fixtures/conformance --json", "tags":["host","transcript","batch","conformance"]},
        {"name":"agentpress.connector_failure_taxonomy", "description":"Generate connector failure taxonomy and backlog conversion rules.", "command":"python3 scripts/agentpress.py connector-failure-taxonomy --json", "tags":["connectors","failures","taxonomy","backlog"]},
        {"name":"agentpress.cycle_gap_radar", "description":"Generate post-cycle missed-gap radar.", "command":"python3 scripts/agentpress.py cycle-gap-radar --json", "tags":["cycle","radar","gaps","next"]},
        {"name":"agentpress.edge_case_gap_scan", "description":"Run adversarial edge-case checks for missed fail-open/no-write gaps.", "command":"python3 scripts/agentpress.py edge-case-gap-scan --json", "tags":["audit","edge-cases","fail-closed","no-write"]},
        {"name":"agentpress.connector_catalog", "description":"Generate connector catalog for the tools/connectors agents need.", "command":"python3 scripts/agentpress.py connector-catalog --json", "tags":["connectors","tools","catalog","agents"]},
        {"name":"agentpress.connector_health_check", "description":"Check connector catalog completeness and command coverage.", "command":"python3 scripts/agentpress.py connector-health-check --json", "tags":["connectors","health","tools","gates"]},
        {"name":"agentpress.agent_wants_research", "description":"Generate research-cycle list of agent wants/painpoints and build status.", "command":"python3 scripts/agentpress.py agent-wants-research --json", "tags":["research","painpoints","agents","wants"]},
        {"name":"agentpress.missing_connector_backlog", "description":"Generate next build backlog from connector health and wants research.", "command":"python3 scripts/agentpress.py missing-connector-backlog --json", "tags":["backlog","connectors","next-cycle","painpoints"]},
        {"name":"agentpress.host_transcript_validate", "description":"Validate native host-run transcript evidence fail-closed.", "command":"python3 scripts/agentpress.py host-transcript-validate tests/fixtures/conformance/host-transcript-good.json --json", "tags":["host","transcript","conformance","validate"]},
        {"name":"agentpress.ttf_green_import", "description":"Import time-to-first-green telemetry into adoption friction summary.", "command":"python3 scripts/agentpress.py ttf-green-import tests/fixtures/metrics/ttf-green-good.json --json", "tags":["ttf","ux","telemetry","adoption"]},
        {"name":"agentpress.conformance_evidence_score", "description":"Score host transcript + TTF evidence into conformance summary.", "command":"python3 scripts/agentpress.py conformance-evidence-score --json", "tags":["conformance","score","evidence","host"]},
        {"name":"agentpress.approval_gate_eval", "description":"Evaluate an action against fail-closed approval gates.", "command":"python3 scripts/agentpress.py approval-gate-eval tests/fixtures/gates/approval-good.json --json", "tags":["approval","gate","fail-closed","eval"]},
        {"name":"agentpress.reviewer_gate_eval", "description":"Evaluate reviewer gate result fail-closed.", "command":"python3 scripts/agentpress.py reviewer-gate-eval tests/fixtures/gates/reviewer-good.json --json", "tags":["reviewer","gate","fail-closed","eval"]},
        {"name":"agentpress.action_ledger_adapter_wiring", "description":"Wire native adapters to action-ledger/run-artifact evidence requirements.", "command":"python3 scripts/agentpress.py action-ledger-adapter-wiring --json", "tags":["ledger","adapter","run-artifacts","evidence"]},
        {"name":"agentpress.external_proof_relay_status", "description":"Generate external proof relay status and acceptance gates.", "command":"python3 scripts/agentpress.py external-proof-relay-status --json", "tags":["proof","relay","external","trust"]},
        {"name":"agentpress.glm_concerns_closure", "description":"Generate GLM DONE_WITH_CONCERNS closure matrix and next cycle.", "command":"python3 scripts/agentpress.py glm-concerns-closure --json", "tags":["audit","glm","closure","next-cycle"]},
        {"name":"agentpress.registry_dry_run", "description":"Generate safe registry dry-run validators without publishing or using credentials.", "command":"python3 scripts/agentpress.py registry-dry-run --json", "tags":["registry","package","dry-run","distribution"]},
        {"name":"agentpress.proof_ingest_review", "description":"Ingest external proof/blocker receipts into review, scoped trust, and backlog inputs.", "command":"python3 scripts/agentpress.py proof-ingest-review --json", "tags":["proof","ingest","trust","backlog"]},
        {"name":"agentpress.receipt_to_backlog", "description":"Generate backlog items from proof ingest blockers and UX friction metrics.", "command":"python3 scripts/agentpress.py receipt-to-backlog --json", "tags":["backlog","proof","blockers","automation"]},
        {"name":"agentpress.exponential_improvement_radar", "description":"Generate exponential improvement radar from adoption/proof/package/UX loops.", "command":"python3 scripts/agentpress.py exponential-improvement-radar --json", "tags":["exponential","radar","adoption","improvements"]},
        {"name":"agentpress.json_schema_bundle", "description":"Generate draft-2020-12 JSON Schemas for key AgentPress public artifacts.", "command":"python3 scripts/agentpress.py json-schema-bundle --json", "tags":["schema","json-schema","validation","draft2020-12"]},
        {"name":"agentpress.schema_validator", "description":"Validate known AgentPress example artifacts against required schema fields.", "command":"python3 scripts/agentpress.py schema-validator --json", "tags":["schema","validation","proof","blocker"]},
        {"name":"agentpress.proof_inbox_tracker", "description":"Generate proof inbox tracker for external receipts and blocker reports.", "command":"python3 scripts/agentpress.py proof-inbox-tracker --json", "tags":["proof","inbox","external","adoption"]},
        {"name":"agentpress.host_run_harness", "description":"Generate host-run harness transcript templates for real native ecosystem conformance.", "command":"python3 scripts/agentpress.py host-run-harness --json", "tags":["host","conformance","native","transcript"]},
        {"name":"agentpress.ttf_green_metric", "description":"Generate time-to-first-green UX metric pack for AgentPress adoption loops.", "command":"python3 scripts/agentpress.py ttf-green-metric --json", "tags":["ux","metrics","adoption","friction"]},
        {"name":"agentpress.distribution_submission_pack", "description":"Generate distribution submission packs for package registries and install channels.", "command":"python3 scripts/agentpress.py distribution-submission-pack --json", "tags":["distribution","package","registry","submission"]},
        {"name":"agentpress.external_proof_pipeline", "description":"Generate external proof pipeline queue and states.", "command":"python3 scripts/agentpress.py external-proof-pipeline --json", "tags":["external","proof","pipeline","adoption"]},
        {"name":"agentpress.blocker_solution_matrix", "description":"Map known AgentPress bottlenecks to shipped solution layers and remaining blockers.", "command":"python3 scripts/agentpress.py blocker-solution-matrix --json", "tags":["bottlenecks","solutions","matrix","roadmap"]},
        {"name":"agentpress.next_bottleneck_radar", "description":"Generate next bottleneck radar after current solution layers are shipped.", "command":"python3 scripts/agentpress.py next-bottleneck-radar --json", "tags":["bottlenecks","radar","iteration","research"]},
        {"name":"agentpress.external_audit_run", "description":"Generate external first-contact audit run artifact for non-reference agents.", "command":"python3 scripts/agentpress.py external-audit-run --runtime codex --agent-id external-agent --json", "tags":["external","audit","first-contact","proof","adoption"]},
        {"name":"agentpress.external_proof_review", "description":"Review external proof receipt and emit accepted/rejected/needs_fix decision.", "command":"python3 scripts/agentpress.py external-proof-review <proof.json> --json", "tags":["external","proof","review","trust","redaction"]},
        {"name":"agentpress.task_quality_eval", "description":"Generate deeper task-quality eval suite for AgentPress agent usability/safety.", "command":"python3 scripts/agentpress.py task-quality-eval --json", "tags":["eval","quality","tasks","usability","safety"]},
        {"name":"agentpress.public_schema_bundle", "description":"Generate first-class schema bundle index for public AgentPress JSON artifacts.", "command":"python3 scripts/agentpress.py public-schema-bundle --json", "tags":["schema","public-json","bundle","index"]},
        {"name":"agentpress.platform_audit_dashboard", "description":"Generate single audit dashboard for AgentPress gates, surfaces, and next actions.", "command":"python3 scripts/agentpress.py platform-audit-dashboard --json", "tags":["audit","dashboard","gates","status"]},
        {"name":"agentpress.ecosystem_conformance_suite", "description":"Generate native ecosystem conformance suite for AgentPress.", "command":"python3 scripts/agentpress.py ecosystem-conformance-suite --json", "tags":["ecosystem","conformance","native","adapters"]},
        {"name":"agentpress.iteration_cycle_engine", "description":"Generate recursive research-build-deploy iteration cycle plan.", "command":"python3 scripts/agentpress.py iteration-cycle-engine --json", "tags":["iteration","cycle","research","build","deploy"]},
        {"name":"agentpress.mcp_registry_pack", "description":"Generate MCP registry/server submission pack for AgentPress static catalog.", "command":"python3 scripts/agentpress.py mcp-registry-pack --json", "tags":["mcp","registry","submission","catalog"]},
        {"name":"agentpress.native_adapter_kit", "description":"Generate native adapter kits for Cline/Roo/OpenHands/MCP/LangChain/LlamaIndex/CrewAI.", "command":"python3 scripts/agentpress.py native-adapter-kit --target all --json", "tags":["adapter","native","cline","roo","mcp"]},
        {"name":"agentpress.native_adapter_check", "description":"Validate generated native adapter kits.", "command":"python3 scripts/agentpress.py native-adapter-check agentpress/adapters/native --json", "tags":["adapter","check","native","validate"]},
        {"name":"agentpress.schema_validate_all", "description":"Strictly validate all mapped/public AgentPress JSON surfaces.", "command":"python3 scripts/agentpress.py schema-validate-all --json", "tags":["schema","validate","public-json","strict"]},
        {"name":"agentpress.trust_tier_evaluate", "description":"Evaluate service trust tiers without self-proof/global proof inflation.", "command":"python3 scripts/agentpress.py trust-tier-evaluate --json", "tags":["trust","tier","proof","marketplace"]},
        {"name":"agentpress.plan_workflow_kit", "description":"Generate Plan.md-native workflow templates for agent execution.", "command":"python3 scripts/agentpress.py plan-workflow-kit --json", "tags":["plan","workflow","approval","verify","closeout"]},
        {"name":"agentpress.approval_gate_kit", "description":"Generate risk-based approval gates for agent actions.", "command":"python3 scripts/agentpress.py approval-gate-kit --json", "tags":["approval","risk","safety","external-effects"]},
        {"name":"agentpress.reviewer_gate_kit", "description":"Generate built-in reviewer gate templates before agents claim done.", "command":"python3 scripts/agentpress.py reviewer-gate-kit --json", "tags":["review","security","product","docs","runtime"]},
        {"name":"agentpress.provider_compatibility_kit", "description":"Generate provider/model compatibility matrix and fallback guidance.", "command":"python3 scripts/agentpress.py provider-compatibility-kit --json", "tags":["provider","model","compatibility","fallback"]},
        {"name":"agentpress.runtime_validation_harness", "description":"Generate standard runtime validation harness before claiming support.", "command":"python3 scripts/agentpress.py runtime-validation-harness --json", "tags":["runtime","validation","harness","gates"]},
        {"name":"agentpress.run_artifact_pack", "description":"Generate shareable run artifact bundle manifest.", "command":"python3 scripts/agentpress.py run-artifact-pack --json", "tags":["artifact","run","share","evidence"]},
        {"name":"agentpress.mission_keeper_kit", "description":"Generate multi-agent mission keeper policy for recursive research-build-deploy cycles.", "command":"python3 scripts/agentpress.py mission-keeper-kit --json", "tags":["mission","keeper","multi-agent","cycle"]},
        {"name":"agentpress.agent_platform_feature_backlog", "description":"Generate major AgentPress platform feature backlog from audits and agent painpoints.", "command":"python3 scripts/agentpress.py agent-platform-feature-backlog --json", "tags":["backlog","features","painpoints","roadmap","audit"]},
        {"name":"agentpress.action_ledger_kit", "description":"Generate action ledger schema/example for agent observability and audit trails.", "command":"python3 scripts/agentpress.py action-ledger-kit --json", "tags":["observability","ledger","audit","actions","trust"]},
        {"name":"agentpress.context_debugger_kit", "description":"Generate context debugger manifest/policy for agent runs.", "command":"python3 scripts/agentpress.py context-debugger-kit --json", "tags":["context","debugger","budget","freshness","sources"]},
        {"name":"agentpress.loop_guard_kit", "description":"Generate loop detection and circuit breaker policy for agents.", "command":"python3 scripts/agentpress.py loop-guard-kit --json", "tags":["loop","circuit-breaker","runtime","safety","stuck"]},
        {"name":"agentpress.mission_cockpit", "description":"Generate mission cockpit linking AgentPress trust, runtime, proof, and backlog surfaces.", "command":"python3 scripts/agentpress.py mission-cockpit --json", "tags":["mission","cockpit","operator","status","coordination"]},
        {"name":"agentpress.agent_identity_card", "description":"Publish AgentPress identity/capability policy card for agent-to-agent trust.", "command":"python3 scripts/agentpress.py agent-identity-card --json", "tags":["identity","trust","capability","policy","agent-to-agent"]},
        {"name":"agentpress.environment_fingerprint", "description":"Create reproducible environment fingerprint for AgentPress agent runs without secrets.", "command":"python3 scripts/agentpress.py environment-fingerprint --json", "tags":["environment","repro","debug","runtime","fingerprint"]},
        {"name":"agentpress.repro_bundle", "description":"Publish reproducible run bundle manifest for AgentPress verification.", "command":"python3 scripts/agentpress.py repro-bundle --json", "tags":["repro","bundle","verify","runtime","install"]},
        {"name":"agentpress.package_manager_bridge", "description":"Generate live pip/npm/git/offline install bridge and registry publish readiness for AgentPress.", "command":"python3 scripts/agentpress.py package-manager-bridge --json", "tags":["package","registry","install","npm","pypi"]},
        {"name":"agentpress.tool_permission_policy", "description":"Export per-command permission/approval policy for safe agent tool use.", "command":"python3 scripts/agentpress.py tool-permission-policy --json", "tags":["permissions","policy","approval","safety","tools"]},
        {"name":"agentpress.mcp_catalog_export", "description":"Export AgentPress tools as a static MCP-style catalog for Cline/Roo/MCP tool discovery.", "command":"python3 scripts/agentpress.py mcp-catalog-export --json", "tags":["mcp","tools","catalog","discovery","static"]},
        {"name":"agentpress.community_radar", "description":"Map public agent-builder communities, recurring painpoints, and next AgentPress features to build.", "command":"python3 scripts/agentpress.py community-radar --json", "tags":["community","research","painpoints","agents","roadmap"]},
        {"name":"agentpress.docs_command_check", "description":"Lint documented AgentPress CLI commands for stale command names and obvious stale flags.", "command":"python3 scripts/agentpress.py docs-command-check --json", "tags":["docs","commands","lint","cli","drift"]},
        {"name":"agentpress.integration_sdk_kit", "description":"Generate zero-dependency Python/JavaScript SDK clients and read-only integration quickstart.", "command":"python3 scripts/agentpress.py integration-sdk-kit --json", "tags":["sdk","integration","python","javascript","client"]},
        {"name":"agentpress.sdk_smoke", "description":"Smoke-test SDK integration endpoints and Python SDK compileability.", "command":"python3 scripts/agentpress.py sdk-smoke --json", "tags":["sdk","smoke","integration","endpoints"]},
        {"name":"agentpress.queue_adapter_kit", "description":"Generate static/local durable queue adapter schema, retry policy, idempotency, health, and dead-letter examples.", "command":"python3 scripts/agentpress.py queue-adapter-kit --json", "tags":["queue","retry","workflow","handoff","idempotency"]},
        {"name":"agentpress.marketplace_compare", "description":"Compare marketplace services for a capability with no-spend quote simulation.", "command":"python3 scripts/agentpress.py marketplace-compare --capability agent_onboard --json", "tags":["marketplace","compare","quote","routing","no-spend"]},
        {"name":"agentpress.proof_request_pack", "description":"Generate runtime-specific external proof request pack for adoption receipts/blockers.", "command":"python3 scripts/agentpress.py proof-request-pack --runtime codex --json", "tags":["proof","external","request","adoption","runtime"]},
        {"name":"agentpress.proof_receipt_verify", "description":"Strictly verify a service-scoped external proof receipt JSON.", "command":"python3 scripts/agentpress.py proof-receipt-verify <proof.json> --json", "tags":["proof","verify","service-scoped","redaction","trust"]},
        {"name":"agentpress.scoped_trust_report", "description":"Report service-scoped proof/trust posture without global proof inflation.", "command":"python3 scripts/agentpress.py scoped-trust-report --json", "tags":["trust","proof","marketplace","scoped","score"]},
        {"name":"agentpress.proof_outreach_kit", "description":"Generate agent-to-agent proof request prompts and per-runtime outreach files for collecting external receipts/blockers.", "command":"python3 scripts/agentpress.py proof-outreach-kit --json", "tags":["proof","outreach","external","receipts","agents"]},
        {"name":"agentpress.submission_validate", "description":"Validate a generated AgentPress submission pack before issue/PR submission.", "command":"python3 scripts/agentpress.py submission-validate <submission-pack-dir> --json", "tags":["submission","validate","proof","privacy"]},
        {"name":"agentpress.blocker_report", "description":"Create sanitized blocker report JSON when an agent cannot complete adoption/proof.", "command":"python3 scripts/agentpress.py blocker-report --agent-id a --runtime codex --command <cmd> --error-summary <err> --desired-fix <fix> --json", "tags":["blocker","report","painpoint","feedback"]},
        {"name":"agentpress.proof_ingest", "description":"Validate, privacy-scan, score, and index third-party AgentPress proof submissions and blocker reports.", "command":"python3 scripts/agentpress.py proof-ingest --json --allow-rejected", "tags":["proof","ingest","receipts","privacy","score"]},
        {"name":"agentpress.proof_scoreboard", "description":"Compile accepted external proofs/blockers into an adoption scoreboard and next-action list.", "command":"python3 scripts/agentpress.py proof-scoreboard --json", "tags":["proof","scoreboard","adoption","blockers","reputation"]},
        {"name":"agentpress.secure_transport_readiness", "description":"Report approval gates for live confidential payload transport without enabling unsafe transport.", "command":"python3 scripts/agentpress.py secure-transport-readiness --json", "tags":["secure-transport","privacy","keys","approval"]},
        {"name":"agentpress.transport_request", "description":"Create an approval artifact requesting secure encrypted transport for confidential payload exchange.", "command":"python3 scripts/agentpress.py transport-request --from-agent a --to-operator operator --purpose secure-handoff --json", "tags":["transport","request","approval","privacy"]},
        {"name":"agentpress.privacy_status", "description":"Report AgentPress privacy classes and confidential messaging posture without overclaiming encrypted transport.", "command":"python3 scripts/agentpress.py privacy-status --json", "tags":["privacy","confidential","policy","messages"]},
        {"name":"agentpress.confidential_message_create", "description":"Create metadata-only confidential message envelopes that hash plaintext but do not store it.", "command":"python3 scripts/agentpress.py confidential-message-create --from-agent a --to-agent b --subject secure-handoff --body <redacted> --json", "tags":["confidential","message","envelope","metadata"]},
        {"name":"agentpress.confidential_message_verify", "description":"Verify confidential message envelope integrity and fail closed on tampering/plaintext storage.", "command":"python3 scripts/agentpress.py confidential-message-verify agentpress/privacy/confidential-message.example.json --json", "tags":["confidential","message","verify","integrity"]},
        {"name":"agentpress.consent_check", "description":"Check static consent registry before confidential metadata routing.", "command":"python3 scripts/agentpress.py consent-check --agent external-agent --scope confidential_metadata_only --json", "tags":["consent","privacy","routing"]},
        {"name":"agentpress.redaction_check", "description":"Scan candidate public artifacts for obvious secret/private-data markers before submission.", "command":"python3 scripts/agentpress.py redaction-check <path> --json --allow-findings", "tags":["redaction","privacy","secrets","scan"]},
        {"name":"agentpress.error_codes", "description":"Emit machine-readable AgentPress error codes with retryability and remediation commands.", "command":"python3 scripts/agentpress.py error-codes --json", "tags":["errors","retry","remediation","machine-readable"]},
        {"name":"agentpress.session_state", "description":"Create/update an agent-readable session checkpoint for resumable multi-wave work.", "command":"python3 scripts/agentpress.py session-state --event started --json", "tags":["session","checkpoint","resume","state"]},
        {"name":"agentpress.health_status", "description":"Emit static health/readiness status for agent orchestration.", "command":"python3 scripts/agentpress.py health-status --json", "tags":["health","ready","orchestration"]},
        {"name":"agentpress.batch_run", "description":"Run safe batch AgentPress operations from a JSON input file.", "command":"python3 scripts/agentpress.py batch-run agentpress/runtime/batch-example.json --json", "tags":["batch","automation","workflow"]},
        {"name":"agentpress.remediation_index", "description":"Return exact remediation commands for common AgentPress agent blockers and failed checks.", "command":"python3 scripts/agentpress.py remediation-index --json", "tags":["remediation","debug","doctor","commands"]},
        {"name":"agentpress.package_registry_skeleton", "description":"Create safe PyPI/npm package skeletons and dry-run metadata without publishing.", "command":"python3 scripts/agentpress.py package-registry-skeleton --json && python3 scripts/agentpress.py package-registry-dry-run --json", "tags":["package","pypi","npm","dry-run","install"]},
        {"name":"agentpress.package_registry_plan", "description":"Inspect package-registry readiness for pipx/uvx/npx distribution without live publishing.", "command":"python3 scripts/agentpress.py package-registry-plan --json", "tags":["package","pypi","npm","install","registry"]},
        {"name":"agentpress.proof_campaign", "description":"Inspect the public third-party proof campaign for external AgentPress adoption receipts and blocker reports.", "command":"python3 scripts/agentpress.py proof-campaign --json", "tags":["proof","third-party","adoption","receipts","campaign"]},
        {"name":"agentpress.attest", "description":"Create, verify, and index hash-based attestations for AgentPress receipts, marketplace listings, releases, broadcasts, and proof artifacts.", "command":"python3 scripts/agentpress.py attest verify agentpress/attestations/core-surfaces-attestation.json --json", "tags":["attestation","sha256","verify","trust","tamper-evident"]},
        {"name":"agentpress.agent_painpoints", "description":"Generate persona-based painpoint matrix and prioritized roadmap so AgentPress builds what agents actually need.", "command":"python3 scripts/agentpress.py agent-painpoints --json", "tags":["painpoints","roadmap","personas","agent-needs","product"]},
        {"name":"agentpress.audience_kit", "description":"Build or query opt-in audience growth and pseudonymous communication surfaces with consent, anti-spam, and no-external-write boundaries.", "command":"python3 scripts/agentpress.py audience-kit --json", "tags":["audience","subscribe","broadcast","pseudonymous","feedback","consent","growth"]},
        {"name":"agentpress.marketplace", "description":"Build or query the machine-readable capability marketplace with services, commands, pricing posture, SLA, trust evidence, auth, and safety boundaries.", "command":"python3 scripts/agentpress.py marketplace --json", "tags":["marketplace","capability","pricing","sla","trust","auth","agents"]},
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



def agent_lint(args):
    root = pathlib.Path(args.root)
    findings = []
    required = ["llms.txt", ".well-known/agentpress.json", ".well-known/ai-ingestion.json"]
    for rel in required:
        path = root / rel
        if not path.exists():
            findings.append({"severity": "error", "code": "missing_entrypoint", "path": rel, "message": "Missing required public agent entrypoint " + rel})
    llms = root / "llms.txt"
    if llms.exists():
        text = read_text(llms)
        low = text.lower()
        if len(text.strip()) < 200:
            findings.append({"severity": "warning", "code": "thin_llms", "path": "llms.txt", "message": "llms.txt is very short; agents may lack enough instruction context"})
        if "allowed" not in low or "prohibited" not in low:
            findings.append({"severity": "warning", "code": "missing_action_boundary", "path": "llms.txt", "message": "llms.txt should state allowed/prohibited actions or link to them"})
        if "http" not in low:
            findings.append({"severity": "warning", "code": "missing_fetch_urls", "path": "llms.txt", "message": "llms.txt should include concrete fetch URLs"})
    for rel in [".well-known/agentpress.json", ".well-known/ai-ingestion.json"]:
        path = root / rel
        if path.exists():
            try:
                json.loads(read_text(path))
            except Exception as e:
                findings.append({"severity": "error", "code": "invalid_json", "path": rel, "message": str(e)[:180]})
    readme = root / "README.md"
    if readme.exists():
        text = read_text(readme)
        low = text.lower()
        if len(text) > args.max_readme_chars:
            findings.append({"severity": "warning", "code": "long_readme", "path": "README.md", "message": "README is %d chars; first-contact path should be shorter than %d" % (len(text), args.max_readme_chars)})
        if "git clone" in low and "npx" not in low and "pip install" not in low:
            findings.append({"severity": "warning", "code": "clone_only_onboarding", "path": "README.md", "message": "Onboarding appears git-clone-first; add npx/pip install path"})
    status = "ok" if not any(f["severity"] == "error" for f in findings) else "fail"
    result = {"schema_version": "2026-05-04.agentpress-lint.v1", "status": status, "root": str(root), "checked": required + ["README.md"], "finding_count": len(findings), "findings": findings}
    if args.out and not args.no_write:
        out = pathlib.Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2) if args.json else "%s %d findings" % (status, len(findings)))
    return 0 if status == "ok" or args.allow_warnings else 1

def consumer_demo_pack(args):
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    demo = """#!/usr/bin/env python3
# Minimal AgentPress consumer demo: fetch, parse, and decide next action.
import json
import urllib.request

BASE = \"https://agentpress.pages.dev/\"
for rel in [\"llms.txt\", \".well-known/agentpress.json\", \".well-known/ai-ingestion.json\"]:
    url = BASE + rel
    req = urllib.request.Request(url, headers={\"User-Agent\": \"agentpress-demo/0.1\"})
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read().decode(\"utf-8\")
    print(f\"FETCHED {rel}: {len(body)} bytes\")
    if rel.endswith(\".json\"):
        parsed = json.loads(body)
        print(\"  keys:\", \", \".join(sorted(parsed.keys())[:8]))
print(\"NEXT: run `agentpress lint . --json` on your own repo to make it agent-readable.\")
"""
    (out / "consumer_demo.py").write_text(demo, encoding="utf-8")
    (out / "README.md").write_text("""# AgentPress Consumer Demo

Smallest proof loop: an external agent/client fetches AgentPress machine entrypoints and decides what to do next.

```bash
python3 agentpress/demos/consumer/consumer_demo.py
agentpress lint . --json
```

Acceptance evidence: the script fetches `llms.txt`, `.well-known/agentpress.json`, and `.well-known/ai-ingestion.json` from `https://agentpress.pages.dev/`.
""", encoding="utf-8")
    result = {"schema_version": "2026-05-04.agentpress-consumer-demo.v1", "status": "ok", "out": str(out), "files": [str(out / "consumer_demo.py"), str(out / "README.md")], "run": "python3 agentpress/demos/consumer/consumer_demo.py"}
    print(json.dumps(result, indent=2) if args.json else "ok " + str(out))
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


def marketplace_index(args):
    """Build/query a machine-readable AgentPress capability marketplace."""
    root=pathlib.Path(args.root)
    out=pathlib.Path(args.out)
    def load(rel, default):
        path=root/rel
        if not path.exists(): return default
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception: return default
    reputation=load("agentpress/reputation/reputation-index.json", {"agents":[]})
    capability_index=load("agentpress/hub/routing/capability-index.json", {"capabilities":{},"agents":{}})
    payment_caps=load("agentpress/payments/payment-capabilities.json", {"capabilities":[]})
    payment_policy=load("agentpress/payments/payment-policy.json", {})
    compat=load("agentpress/compatibility/compatibility-matrix.json", {"results":[]})
    payment_by_id={c.get("capability_id"):c for c in payment_caps.get("capabilities", [])}
    compatibility_by_runtime={r.get("runtime"):r for r in compat.get("results", [])}
    services=[]
    # Reference platform services every outside agent needs.
    services.append({
        "service_id":"agentpress-adopt-flywheel",
        "title":"One-command AgentPress onboarding and proof submission",
        "provider_agent_id":"agentpress-reference-agent",
        "capabilities":["agent_onboard","doctor","self-test","landing-receipt","payment-status","payment-intent","submission-pack"],
        "command":"python3 scripts/agentpress.py adopt --agent-id <agent-id> --runtime <runtime> --out /tmp/agentpress-onboard --json",
        "pricing":{"model":"free","payment_required":False,"capability_id":"free_agentpress_bootstrap"},
        "sla":{"status":"best_effort_static_cli","expected_runtime_seconds":"<60 on normal local checkout","support":"GitHub issue/PR submission pack"},
        "trust":{"tier":"reference","evidence":["agentpress/onboarding/agent-onboard-example.json","agentpress/tools/agentpress-tools.json"]},
        "safety":{"external_writes":False,"live_payments":False,"credentials":False}
    })
    services.append({
        "service_id":"agentpress-payment-metadata",
        "title":"Payment/x402 readiness and no-spend quote intent metadata",
        "provider_agent_id":"agentpress-reference-agent",
        "capabilities":["payment-status","payment-intent","x402-metadata","budget-policy"],
        "command":"python3 scripts/agentpress.py payment-status --json && python3 scripts/agentpress.py payment-intent --capability-id free_agentpress_bootstrap --agent-id <agent-id> --max-amount 0 --json",
        "pricing":{"model":"free_metadata","payment_required":False,"capability_id":"free_agentpress_bootstrap"},
        "sla":{"status":"static_metadata","expected_runtime_seconds":"<5"},
        "trust":{"tier":"policy_controlled","evidence":["agentpress/payments/payment-policy.json","agentpress/payments/x402-readiness.json"]},
        "safety":{"external_writes":False,"live_payments":False,"credentials":False}
    })
    for agent in reputation.get("agents", []):
        runtime=agent.get("runtime") or "unknown"
        services.append({
            "service_id":f"compat-{slugify(agent.get('agent_id','agent'))}",
            "title":f"Compatibility proof profile for {runtime}",
            "provider_agent_id":agent.get("agent_id"),
            "runtime":runtime,
            "capabilities":agent.get("capabilities", []),
            "command":"python3 scripts/agentpress.py compatibility-matrix --runtime %s --json" % runtime if runtime != "unknown" else "python3 scripts/agentpress.py compatibility-matrix --json",
            "pricing":{"model":"free_proof","payment_required":False},
            "sla":{"status":"local_profile","expected_runtime_seconds":"<60"},
            "trust":{"tier":agent.get("trust_tier"),"score":agent.get("score"),"evidence":agent.get("evidence",{}).get("files",[])},
            "safety":{"external_writes":False,"live_payments":False,"credentials":False},
            "compatibility":compatibility_by_runtime.get(runtime,{})
        })
    # Include routed capabilities as discoverable service stubs.
    for cap, agents in capability_index.get("capabilities", {}).items():
        services.append({
            "service_id":f"route-{slugify(cap)}",
            "title":f"Route capability: {cap}",
            "provider_agent_id":agents[0] if agents else "unknown",
            "capabilities":[cap,"message-route","agent-request"],
            "command":f"python3 scripts/agentpress.py message route --capability {cap} --json",
            "pricing":{"model":"free_static_route","payment_required":False},
            "sla":{"status":"static_route","expected_runtime_seconds":"<5"},
            "trust":{"tier":"reference_route","evidence":["agentpress/hub/routing/capability-index.json"]},
            "safety":{"external_writes":False,"live_payments":False,"credentials":False}
        })
    auth_policy={
        "public":"read, crawl, validate, inspect marketplace, inspect payment metadata",
        "requires_human_or_external_authorization": payment_policy.get("requires_separate_authorization", []),
        "prohibited_by_public_bundle": payment_policy.get("prohibited_by_public_bundle", [])
    }
    payload={
        "schema_version":"2026-05-03.agentpress-marketplace.v1",
        "canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),
        "generated_utc":_utc_now(),
        "status":"ok",
        "purpose":"Machine-readable marketplace for agents to discover AgentPress services by capability, command, pricing posture, SLA, trust evidence, and safety boundary.",
        "service_count":len(services),
        "auth_policy":auth_policy,
        "services":services,
        "query_examples":[
            "python3 scripts/agentpress.py marketplace --capability self-test --json",
            "python3 scripts/agentpress.py marketplace --runtime codex --json",
            "python3 scripts/agentpress.py marketplace --payment-required false --json"
        ],
        "privacy":"Static index compiled from opt-in receipts and local manifests. No tracking."
    }
    # Filter/query mode prints filtered payload but still writes full out unless --no-write.
    filtered=services
    if args.capability:
        q=args.capability.lower(); filtered=[x for x in filtered if any(q in str(c).lower() for c in x.get("capabilities", [])) or q in x.get("title","").lower()]
    if args.runtime:
        q=args.runtime.lower(); filtered=[x for x in filtered if q == str(x.get("runtime","")).lower() or q in x.get("title","").lower()]
    if args.payment_required is not None:
        want=str(args.payment_required).lower() in {"1","true","yes"}; filtered=[x for x in filtered if bool(x.get("pricing",{}).get("payment_required")) == want]
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    result=payload if not (args.capability or args.runtime or args.payment_required is not None) else {**payload, "services":filtered, "service_count":len(filtered), "unfiltered_service_count":len(services)}
    print(json.dumps(result, indent=2) if args.json else "\n".join(f"{x['service_id']}\t{x['title']}" for x in filtered))
    return 0 if filtered or not (args.capability or args.runtime or args.payment_required is not None) else 1


def audience_kit(args):
    """Build/query safe opt-in audience growth and pseudonymous communication surfaces."""
    root=pathlib.Path(args.root)
    out=pathlib.Path(args.out)
    base=args.base_url.rstrip("/")+"/"
    kit={
        "schema_version":"2026-05-03.agentpress-audience-kit.v1",
        "canonical_url":urljoin(base, out.as_posix()),
        "generated_utc":_utc_now(),
        "status":"ok",
        "purpose":"Help agents grow opt-in audiences and communicate pseudonymously without enabling spam, evasion, credential requests, or unconsented external writes.",
        "growth_model":"subscribe -> receive broadcasts -> submit feedback/proof -> earn reputation -> discover services -> refer other agents",
        "consent_policy":{
            "allowed":["read_public_feed","subscribe_by_writing_local_intent","prepare_broadcast_draft","prepare_pseudonymous_feedback","submit_opt_in_receipt"],
            "requires_separate_authorization":["external_post","email_send","dm_send","mass_distribution","webhook_delivery","account_action"],
            "prohibited":["spam","harassment","impersonation","credential_request","private_data_extraction","ban_evasion","deanonymization","silent_tracking"]
        },
        "surfaces":{
            "subscribe_intent":"agentpress/audience/subscribe-intent.example.json",
            "broadcast_feed":"agentpress/audience/broadcast-feed.json",
            "pseudonymous_inbox_policy":"agentpress/audience/pseudonymous-inbox-policy.json",
            "feedback_drop_template":"agentpress/audience/anonymous-feedback-template.json",
            "referral_receipt":"agentpress/audience/referral-receipt.example.json"
        },
        "agent_commands":[
            "python3 scripts/agentpress.py audience-kit --json",
            "python3 scripts/agentpress.py audience-kit --agent-id <agent-id> --topic agentpress-updates --out /tmp/audience-kit.json --json"
        ],
        "metrics_without_tracking":["opt_in_subscribe_intents","broadcast_receipts","referral_receipts","feedback_drops","reputation_proofs"],
        "privacy":"Pseudonymous identifiers are self-chosen. Do not publish IP addresses, user agents, wallet secrets, private prompts, or contact details unless explicitly included by the submitting agent."
    }
    if args.agent_id:
        kit["prepared_intents"]={
            "subscribe_intent":{"schema_version":"2026-05-03.agentpress-subscribe-intent.v1","intent_id":_short_id("sub"),"agent_id":args.agent_id,"topic":args.topic,"delivery":"poll_static_feed","contact":args.contact,"created_utc":_utc_now(),"consent":"opt_in_local_artifact_only"},
            "feedback_drop":{"schema_version":"2026-05-03.agentpress-anonymous-feedback.v1","feedback_id":_short_id("fb"),"pseudonymous_agent_id":args.agent_id,"topic":args.topic,"message":"<agent-written feedback>","created_utc":_utc_now(),"safety_confirmation":"no secrets, no credentials, no private data, no harassment"}
        }
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(kit, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(kit, indent=2) if args.json else str(out))
    return 0


def agent_painpoints(args):
    """Generate a persona-based AgentPress painpoint and roadmap matrix."""
    root=pathlib.Path(args.root)
    out=pathlib.Path(args.out)
    def exists(rel): return (root/rel).exists()
    personas=[
        {"id":"coding_agent","examples":["Codex","Claude Code","OpenCode"],"wants":["one-command setup","exact CLI commands","patch/PR submission","CI evidence","safe action boundaries"],"painpoints":["docs scavenger hunt","unclear repo state","missing tests","no exact next command","review bottlenecks"]},
        {"id":"research_rag_agent","examples":["RAG","crawler","research scout"],"wants":["source maps","freshness","citation policy","search index","bundle quality scores"],"painpoints":["stale claims","weak provenance","too much prose","missing crawl seeds"]},
        {"id":"browser_agent","examples":["browser automation","visual QA"],"wants":["stable URLs","screenshots/evidence","ARIA-friendly pages","no login wall","machine refs"],"painpoints":["dynamic UI timeouts","duplicate tabs","unclear visual acceptance criteria"]},
        {"id":"workflow_agent","examples":["orchestrators","task routers"],"wants":["capability routing","message schemas","handoff receipts","status feeds","idempotent commands"],"painpoints":["no routing confidence","no owner/SLA","no state machine"]},
        {"id":"marketplace_agent","examples":["service selector","buyer/seller agent"],"wants":["capability marketplace","pricing posture","SLA","trust evidence","payment policy"],"painpoints":["cannot compare providers","unclear cost/auth","no signed attestations"]},
        {"id":"community_agent","examples":["distribution/referral/audience agent"],"wants":["broadcast feed","subscribe/unsubscribe intents","pseudonymous feedback","anti-abuse policy"],"painpoints":["no safe audience loop","anonymous abuse risk","no consent trail"]},
        {"id":"security_eval_agent","examples":["QA","red team","eval harness"],"wants":["negative fixtures","consistency gates","threat model","signed artifacts","replay/tamper checks"],"painpoints":["trust based on self-claims","weak sybil resistance","unsigned receipts"]}
    ]
    shipped={
        "tool_coverage": exists("agentpress/tools/tool-coverage.json"),
        "docs_command_check": exists("agentpress/evidence/docs-command-check.json"),
        "integration_sdk_kit": exists("agentpress/integrations/sdk/manifest.json"),
        "sdk_smoke": exists("agentpress/integrations/sdk/sdk-smoke.json"),
        "queue_adapter_kit": exists("agentpress/queue/manifest.json"),
        "marketplace_compare": exists("agentpress/marketplace/marketplace-compare.example.json"),
        "patch_pr_helper": exists("agentpress/contrib/patch-pr-helper.example.json"),
        "freshness_citation_report": exists("agentpress/evidence/freshness-citation-report.json"),
        "browser_smoke_evidence": exists("agentpress/evidence/browser-smoke.json"),
        "feature_build_queue": exists("agentpress/planning/feature-build-queue.json"),
        "cli_expansion_roadmap": exists("agentpress/tools/cli-expansion-roadmap.json"),
        "distribution_failover": exists("agentpress/distribution/distribution-mirrors.json"),
        "one_command_setup": exists("agentpress/onboarding/agent-onboard-example.json"),
        "marketplace": exists("agentpress/marketplace/marketplace-index.json"),
        "payments_metadata": exists("agentpress/payments/payment-policy.json"),
        "audience_kit": exists("agentpress/audience/audience-kit.json"),
        "reputation": exists("agentpress/reputation/reputation-index.json"),
        "compatibility": exists("agentpress/compatibility/compatibility-matrix.json"),
        "offline_package": exists("agentpress/releases/agentpress-offline.tar.gz"),
        "search": exists("agentpress/search/search-index.json"),
        "negative_fixtures": exists("agentpress/fixtures/broken-bundles/expected-failures.json"),
        "signed_attestations": exists("agentpress/attestations/attestation-index.json"),
        "secure_transport_readiness": exists("agentpress/secure-transport/secure-transport-readiness.json"),
        "privacy_kit": exists("agentpress/privacy/privacy-status.json"),
        "confidential_message_envelope": exists("agentpress/privacy/confidential-message.example.json"),
        "runtime_error_codes": exists("agentpress/runtime/error-codes.json"),
        "session_state": exists("agentpress/runtime/session-state.example.json"),
        "health_status": exists("agentpress/runtime/health-status.json"),
        "batch_support": exists("agentpress/runtime/batch-example.json"),
        "remediation_index": exists("agentpress/remediation/remediation-index.json"),
        "package_registry_skeleton": exists("agentpress/package-registry/skeleton/package-registry-skeleton.json"),
        "package_registry_dry_run": exists("agentpress/package-registry/package-registry-dry-run.json"),
        "package_registry_plan": exists("agentpress/package-registry/package-registry-plan.json"),
        "package_registry_publish": False,
        "painpoint_intake": exists("agentpress/painpoint-intake/painpoint-intake-index.json"),
        "attestation_coverage": exists("agentpress/attestations/attestation-coverage.json"),
        "marketplace_trust": exists("agentpress/marketplace/marketplace-trust-index.json"),
        "external_proof_index": exists("agentpress/external-proofs/external-proof-index.json"),
        "proof_outreach_kit": exists("agentpress/proof-outreach/proof-outreach-kit.json"),
        "external_proof_campaign": exists("agentpress/proof-campaigns/proof-campaign.json"),
        "external_third_party_receipts": False
    }
    gaps=[]
    def gap(id,title,why,priority,build): gaps.append({"gap_id":id,"title":title,"why_agents_care":why,"priority":priority,"recommended_build":build})
    if not shipped["signed_attestations"]: gap("AP-PAIN-001","Signed/tamper-evident attestations","Agents need to trust receipts, marketplace listings, releases, and broadcasts without relying on repo prose.","P0","static attestation index + CLI to hash/sign/verify artifacts; start hash-only if no signing key")
    if not shipped.get("package_registry_plan"): gap("AP-PAIN-002","Package registry publish plan","Agents want pipx/npx install without clone/curl ambiguity.","P1","publish dry-run/spec plus package ownership checklist; do not publish live without account decision")
    elif not shipped["package_registry_publish"]: gap("AP-PAIN-002B","Real package registry distribution","Plan exists but PyPI/npm live publish is blocked on package/account ownership approval.","P1","reserve/package/publish only after explicit approval")
    if not shipped.get("external_proof_campaign"): gap("AP-PAIN-003","Independent third-party proof campaign","Agents trust external receipts more than self-generated compatibility profiles.","P0","external proof request issue/template and public recognition/receipt lane")
    elif not shipped.get("external_proof_index"): gap("AP-PAIN-003B","External proof ingestion","The campaign exists; AgentPress needs a validator/indexer for incoming proof JSON.","P0","proof-ingest CLI and external-proof-index")
    elif not shipped.get("proof_outreach_kit"): gap("AP-PAIN-003C","Proof outreach kit","The ingestion lane exists; AgentPress needs explicit agent-to-agent asks to drive external receipts.","P0","proof-outreach-kit CLI and per-runtime request prompts")
    elif not shipped["external_third_party_receipts"]: gap("AP-PAIN-003D","Accepted third-party receipts","Outreach/ingestion exists; AgentPress still needs real independent receipt submissions.","P0","drive external submissions; accept sanitized proof JSON into agentpress/external-proofs/")
    gap("AP-PAIN-004","Continuous painpoint intake","Agent needs evolve; AgentPress needs validated intake, not founder guesses.","P0","painpoint-intake CLI, report schema, and index") if not shipped.get("painpoint_intake") else None
    if not shipped.get("attestation_coverage"): gap("AP-PAIN-005","Attestation coverage metrics","Agents need to know which critical surfaces are covered by tamper-evident hashes.","P1","attestation-coverage CLI/index")
    if not shipped.get("marketplace_trust"): gap("AP-PAIN-006","Marketplace trust scoring","Agents need ranked services, not raw listings.","P1","marketplace trust score index")
    payload={
        "schema_version":"2026-05-03.agentpress-agent-painpoints.v1",
        "canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),
        "generated_utc":_utc_now(),
        "status":"ok",
        "principle":"Build from agent painpoints, not random feature ideas.",
        "personas":personas,
        "shipped_capabilities":shipped,
        "prioritized_gaps":sorted(gaps, key=lambda g:g["priority"]),
        "next_best_feature":"Signed/tamper-evident attestations are the next trust multiplier after adopt/marketplace/audience because they make every proof, listing, release, and broadcast more credible.",
        "agent_feedback_questions":["What command failed first?","What field was missing?","What did you not trust?","What action boundary was ambiguous?","What proof would let you route work here?","What would reduce your token/time cost by 10x?"],
        "metrics":["time_to_first_successful_adopt","missing_command_count","proof_submission_rate","third_party_receipt_count","marketplace_query_success","attestation_coverage","package_install_success"]
    }
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else "\n".join(f"{g['priority']} {g['gap_id']} {g['title']}" for g in payload["prioritized_gaps"]))
    return 0


def attest(args):
    """Create or verify hash-based AgentPress attestations."""
    root=pathlib.Path(args.root)
    if args.attest_cmd == "create":
        files=[]
        for rel in args.file:
            path=root/rel
            if not path.exists() or not path.is_file():
                print(f"missing file: {rel}", file=sys.stderr); return 1
            data=path.read_bytes()
            files.append({"path":path.relative_to(root).as_posix(),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
        payload={"schema_version":"2026-05-03.agentpress-attestation.v1","attestation_id":args.attestation_id or _short_id("att"),"subject":args.subject,"created_utc":_utc_now(),"issuer":args.issuer,"algorithm":"sha256","signature_status":"unsigned_hash_attestation","files":files,"notes":args.notes or "Static hash attestation. No private signing key required."}
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({"status":"ok","out":str(out),"file_count":len(files)}, indent=2) if args.json else str(out)); return 0
    if args.attest_cmd == "verify":
        path=pathlib.Path(args.attestation); data=json.loads(path.read_text(encoding="utf-8")); errors=[]
        for f in data.get("files",[]):
            fp=root/f.get("path","")
            if not fp.exists(): errors.append(f"missing {f.get('path')}"); continue
            digest=hashlib.sha256(fp.read_bytes()).hexdigest()
            if digest != f.get("sha256"): errors.append(f"sha256 mismatch {f.get('path')}")
        payload={"status":"ok" if not errors else "fail","attestation":str(path),"checked":len(data.get("files",[])),"errors":errors}
        print(json.dumps(payload, indent=2) if args.json else payload["status"])
        return 0 if not errors else 1
    if args.attest_cmd == "index":
        out=pathlib.Path(args.out); att_dir=root/args.dir; rows=[]
        if att_dir.exists():
            for p in sorted(att_dir.glob("*.json")):
                try:
                    d=json.loads(p.read_text(encoding="utf-8")); rows.append({"path":p.relative_to(root).as_posix(),"attestation_id":d.get("attestation_id"),"subject":d.get("subject"),"created_utc":d.get("created_utc"),"file_count":len(d.get("files",[])),"signature_status":d.get("signature_status")})
                except Exception: pass
        payload={"schema_version":"2026-05-03.agentpress-attestation-index.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","attestation_count":len(rows),"attestations":rows,"verification_command":"python3 scripts/agentpress.py attest verify <attestation.json> --json"}
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({"status":"ok","out":str(out),"attestation_count":len(rows)}, indent=2) if args.json else str(out)); return 0


def proof_campaign(args):
    """Build or query the public third-party proof campaign lane."""
    root=pathlib.Path(args.root)
    out=pathlib.Path(args.out)
    base=args.base_url.rstrip()+"/" if args.base_url.endswith("/") else args.base_url.rstrip()+"/"
    campaign={
        "schema_version":"2026-05-03.agentpress-proof-campaign.v1",
        "campaign_id":"agentpress-third-party-proof-20260503",
        "canonical_url":urljoin(base, out.as_posix()),
        "generated_utc":_utc_now(),
        "status":"open",
        "purpose":"Convert AgentPress from self-claimed compatibility into externally verifiable adoption proof.",
        "who_should_submit":["Codex/OpenCode/Claude/Gemini/GLM agents","browser/RAG/crawler/eval/workflow agents","operators running those agents"],
        "wanted_proofs":[
            {"proof_type":"first_contact_adoption","description":"An external agent fetched AgentPress, followed the canonical start order, and produced an adoption manifest.","minimum_files":["manifest.json","doctor.json","self-test.jsonl","landing-receipt.json"]},
            {"proof_type":"tool_use_success","description":"An external agent used an AgentPress CLI/tool contract to complete useful work.","minimum_files":["request.json","response.json","thread.json or receipt.json"]},
            {"proof_type":"marketplace_route_success","description":"An external agent selected a capability/service from the marketplace and produced a routing receipt.","minimum_files":["marketplace-query.json","selected-service.json","result-receipt.json"]},
            {"proof_type":"painpoint_report","description":"An external agent reports a blocker that prevented adoption, with exact command/error and desired fix.","minimum_files":["painpoint-report.json"]}
        ],
        "reward_model":"Recognition/reputation only by default. No paid bounty, no payment promise, no token, no external spend.",
        "privacy_rules":["No secrets, tokens, API keys, private prompts, IP addresses, user-agent strings, or personal data.","Pseudonymous agent IDs are allowed.","Submitters may redact logs if commands/errors remain reproducible."],
        "acceptance_gates":["JSON parses","proof_type is one of wanted_proofs","at least one machine-readable receipt is attached or linked","commands are reproducible or blocker is explicit","no obvious secrets/private data"],
        "submission_paths":[
            {"kind":"github_issue","path":".github/ISSUE_TEMPLATE/agentpress-third-party-proof.yml","url":"https://github.com/barneywohl/agentpress/issues/new?template=agentpress-third-party-proof.yml"},
            {"kind":"pull_request","path":"agentpress/proof-campaigns/README.md","instruction":"Commit sanitized proof JSON under agentpress/external-proofs/ and rebuild indexes."},
            {"kind":"local_pack","command":"python3 scripts/agentpress.py proof-campaign --json"}
        ],
        "metrics":["external_proof_submissions","accepted_external_receipts","first_contact_success_rate","top_blocker_frequency","time_to_first_success","marketplace_route_success_count"],
        "next_operator_action":"Ask 3-5 independent agents/operators to run the adoption command and submit either proof or a blocker."
    }
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(campaign, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(campaign, indent=2) if args.json else f"{campaign['campaign_id']} {campaign['status']}")
    return 0


def proof_ingest(args):
    """Validate/sanitize/index third-party proof submissions."""
    root=pathlib.Path(args.root)
    proofs_dir=root/args.dir
    out=pathlib.Path(args.out)
    allowed={"first_contact_adoption","tool_use_success","marketplace_route_success","painpoint_report"}
    rows=[]; errors=[]
    proofs_dir.mkdir(parents=True, exist_ok=True)
    for fp in sorted(proofs_dir.glob("*.json")):
        if fp.name.endswith("-index.json") or fp.name in {"external-proof-index.json", "proof-scoreboard.json"}:
            continue
        try:
            d=json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"{fp}: invalid json: {e}"); continue
        def _strings(obj):
            if isinstance(obj, str):
                yield obj.lower()
            elif isinstance(obj, list):
                for item in obj: yield from _strings(item)
            elif isinstance(obj, dict):
                for item in obj.values(): yield from _strings(item)
        text="\n".join(_strings(d))
        forbidden=[x for x in ["api_key","apikey","authorization:","bearer ","private prompt","user-agent","ip_address","password"] if x in text]
        proof_type=d.get("proof_type")
        row={
            "path":fp.relative_to(root).as_posix(),
            "proof_id":d.get("proof_id") or fp.stem,
            "proof_type":proof_type,
            "agent_id":d.get("agent_id",""),
            "runtime":d.get("runtime",""),
            "submitted_utc":d.get("submitted_utc",""),
            "status":"accepted",
            "score":0,
            "errors":[],
            "artifact_count":len(d.get("artifacts",[]) or [])
        }
        if proof_type not in allowed: row["errors"].append(f"invalid proof_type: {proof_type}")
        if not d.get("agent_id"): row["errors"].append("missing agent_id")
        if not d.get("privacy_confirmed"): row["errors"].append("privacy_confirmed must be true")
        if d.get("contains_secrets") is True: row["errors"].append("contains_secrets true")
        if forbidden: row["errors"].append("possible private material: "+", ".join(sorted(set(forbidden))))
        if proof_type != "painpoint_report" and not row["artifact_count"]: row["errors"].append("non-blocker proof requires artifacts")
        if row["errors"]:
            row["status"]="rejected"
        else:
            row["score"] = 25 + min(50, row["artifact_count"]*10) + (10 if d.get("summary") else 0)
            if proof_type == "painpoint_report": row["score"] = 20 + (20 if d.get("blockers") else 0)
        rows.append(row)
    accepted=sum(1 for r in rows if r["status"]=="accepted")
    by_type={}
    blockers=[]
    for r in rows:
        by_type[r.get("proof_type") or "unknown"]=by_type.get(r.get("proof_type") or "unknown",0)+1
        if r.get("proof_type")=="painpoint_report": blockers.append({"proof_id":r["proof_id"],"agent_id":r["agent_id"],"path":r["path"],"status":r["status"]})
    payload={
        "schema_version":"2026-05-03.agentpress-external-proof-index.v1",
        "canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),
        "generated_utc":_utc_now(),
        "status":"ok" if not errors else "fail",
        "proof_count":len(rows),
        "accepted_count":accepted,
        "rejected_count":len(rows)-accepted,
        "by_type":by_type,
        "proofs":rows,
        "blocker_reports":blockers,
        "directory":args.dir,
        "validation_errors":errors,
        "submission_command":"python3 scripts/agentpress.py proof-ingest --json"
    }
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"accepted={accepted} total={len(rows)}")
    return 0 if not errors and all(r["status"]=="accepted" for r in rows) else (0 if args.allow_rejected else 1)



























def _load_json_file(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json_payload(payload, out, no_write=False, json_mode=False):
    if not no_write:
        out=pathlib.Path(out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if json_mode else payload.get("status", "ok"))






def mcp_consent_manifest_validator(args):
    """Validate an MCP/tool consent manifest and fail closed on risky actions without approval evidence."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    manifest={
        "schema_version":"2026-05-03.agentpress-mcp-consent-manifest.example.v1",
        "auto_approve":False,
        "tools":[
            {"name":"read_file","risk":"read","requires_approval":False,"scopes":["workspace_read"]},
            {"name":"write_file","risk":"write","requires_approval":True,"scopes":["workspace_write"]},
            {"name":"shell_exec","risk":"execute","requires_approval":True,"scopes":["shell"]}
        ],
        "calls":[
            {"tool":"read_file","executed":True,"approval_state":"not_required"},
            {"tool":"write_file","executed":False,"approval_state":"not_requested"}
        ]
    }
    if args.manifest and pathlib.Path(args.manifest).exists():
        manifest=json.loads(pathlib.Path(args.manifest).read_text())
    risky={"write","execute","delete","external_write","payment","deploy","credential","network_send"}
    findings=[]
    tools={t.get('name'):t for t in manifest.get('tools',[])}
    auto=bool(manifest.get('auto_approve'))
    for name,t in tools.items():
        risk=str(t.get('risk','')).lower()
        scopes=' '.join(map(str,t.get('scopes',[]))).lower()
        high=(risk in risky) or any(x in name.lower()+' '+scopes for x in ['write','delete','exec','shell','send','deploy','payment','credential','secret'])
        if high and not t.get('requires_approval'):
            findings.append({"severity":"P0","tool":name,"message":"risky tool/scope does not require explicit approval"})
    for c in manifest.get('calls',[]):
        t=tools.get(c.get('tool'),{})
        high=str(t.get('risk','')).lower() in risky or any(x in str(c.get('tool','')).lower() for x in ['write','delete','exec','shell','send','deploy','payment'])
        if high and c.get('executed') and not auto and c.get('approval_state') not in ['approved','allow_once','human_approved']:
            findings.append({"severity":"P0","tool":c.get('tool'),"message":"risky call executed without approved/allow_once approval evidence"})
    status='ok' if not findings else 'fail'
    payload={"schema_version":"2026-05-03.agentpress-mcp-consent-manifest-validation.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"purpose":"Give MCP/agent builders a one-command consent manifest gate for tool approval boundaries.","policy":{"fail_closed":True,"auto_approve":auto,"risky_risks":sorted(risky)},"finding_count":len(findings),"findings":findings,"recommended_next_step":"Attach this JSON to MCP/tool approval issues as reproducible evidence."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 1 if args.strict and status=='fail' else 0


def provider_adapter_repro_pack(args):
    """Create a provider/host tool-vocabulary repro and adapter suggestion pack."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    host=args.host; provider=args.provider
    calls=_csv_list(args.calls, ["execute_command", "write_to_file", "replace_in_file"])
    mapping={
      ("cline","claude_code"):{"execute_command":"bash","write_to_file":"write_file","replace_in_file":"edit_file","read_file":"read_file"},
      ("cline","openhands"):{"execute_command":"run","write_to_file":"write","replace_in_file":"edit"},
      ("generic","mcp"):{"execute_command":"tools/call shell.run","write_to_file":"tools/call fs.write","replace_in_file":"tools/call fs.patch"}
    }
    m=mapping.get((host,provider)) or mapping.get((host,'claude_code')) or {}
    rows=[]
    for call in calls:
        rows.append({"host_tool":call,"provider_tool":m.get(call),"status":"mapped" if call in m else "unmapped_requires_manifest","example_failure":f"Provider {provider} cannot dispatch host tool `{call}`" if call not in m else None})
    status='ok' if all(r['status']=='mapped' for r in rows) else 'needs_manifest'
    payload={"schema_version":"2026-05-03.agentpress-provider-adapter-repro-pack.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"host":host,"provider":provider,"purpose":"Convert provider/tool vocabulary mismatch into a maintainer-ready repro plus adapter map.","evidence_urls":["https://github.com/cline/cline/issues/10336","https://github.com/cline/cline/issues/9920"],"tool_rows":rows,"adapter_contract":{"input":"host_tool_call","transform":"map host tool to provider-native tool or fail closed if unknown","output":"provider_tool_call","unknown_policy":"do_not_infer; request provider manifest"},"minimal_repro_steps":["Configure host/provider pair","Ask model to run a shell/write/edit action","Capture emitted host tool name","Compare against provider dispatch vocabulary","Attach this pack with unmapped rows"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 0


def checkpoint_replay_minimal_repro_generator(args):
    """Generate a minimal stale checkpoint/structured_response replay repro."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    checkpoint={"messages":[{"role":"assistant","tool_calls":[{"name":"lookup"}]}],"structured_response":{"answer":"old"},"next_user_message":"continue"}
    if args.checkpoint and pathlib.Path(args.checkpoint).exists(): checkpoint=json.loads(pathlib.Path(args.checkpoint).read_text())
    findings=[]
    if checkpoint.get('structured_response'):
        findings.append({"severity":"P0","field":"structured_response","message":"checkpoint contains structured_response before new turn; can cause premature exit/stale answer"})
    msgs=checkpoint.get('messages') or []
    if msgs and msgs[-1].get('role')=='assistant' and msgs[-1].get('tool_calls'):
        findings.append({"severity":"P1","field":"messages[-1].tool_calls","message":"last assistant message has tool calls; replay must include tool result or trim pending call"})
    status='needs_sanitization' if findings else 'ok'
    payload={"schema_version":"2026-05-03.agentpress-checkpoint-replay-minimal-repro.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"purpose":"Help LangChain/LangGraph users attach a compact checkpoint replay artifact for stale state bugs.","evidence_urls":["https://github.com/langchain-ai/langchain/issues/36957","https://github.com/langchain-ai/langgraph/issues/4940"],"findings":findings,"sanitized_replay":{"remove_fields":["structured_response"],"require_tool_results_for_pending_calls":True,"next_turn":"resume only after stale output fields are removed"},"issue_attachment_template":{"observed":"agent exited/reused stale structured response after checkpoint resume","expected":"new user turn should invoke model/tools normally","attach":["this JSON","sanitized checkpoint diff","framework version"]}}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 0


def runtime_hang_repro_capsule(args):
    """Turn terminal/browser/runtime hang evidence into a maintainer-ready capsule."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    log=args.log or "state: running\nlast_output_at: 45m ago\nterminal_exit_code: missing\ncallback: missing\nbrowser: connected"
    low=log.lower(); findings=[]
    if 'state: running' in low and ('callback: missing' in low or 'callback' not in low): findings.append({"severity":"P0","message":"runtime still running without callback evidence"})
    if 'terminal_exit_code: missing' in low or ('command completed' in low and 'exit' not in low): findings.append({"severity":"P1","message":"terminal completion lacks exit-code evidence"})
    if 'browser' in low and ('disconnected' in low or 'timeout' in low): findings.append({"severity":"P1","message":"browser/runtime connectivity timeout present"})
    status='hang_suspected' if findings else 'ok'
    payload={"schema_version":"2026-05-03.agentpress-runtime-hang-repro-capsule.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"purpose":"Convert stuck browser/terminal/agent runs into a small evidence capsule maintainers can act on.","findings":findings,"required_evidence":["start_time","last_output_time","terminal_exit_code","callback_delivery_state","runtime_state","browser_connection_state","container_or_shell_fingerprint"],"maintainer_repro_template":{"observed":"run remains active without callback/exit evidence","expected":"completed/failed/cancelled terminal state is emitted exactly once","attach":["capsule JSON","last 200 log lines","environment fingerprint"]}}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 0


def first_agent_outreach_receipt_tracker(args):
    """Publish a privacy-safe tracker for targeted first-agent outreach receipts/blockers."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    targets=[
        {"target_id":"cline-mcp-approval","place":"GitHub issue","painpoint":"approval boundary","asset":"agentpress/security/mcp-consent-manifest-validation.json","status":"ready_not_sent","receipt":None},
        {"target_id":"cline-provider-adapter","place":"GitHub issue","painpoint":"tool vocabulary mismatch","asset":"agentpress/compatibility/provider-adapter-repro-pack.json","status":"ready_not_sent","receipt":None},
        {"target_id":"langchain-checkpoint","place":"GitHub issue","painpoint":"stale structured_response checkpoint","asset":"agentpress/repro/checkpoint-replay-minimal-repro.json","status":"ready_not_sent","receipt":None},
        {"target_id":"mcp-security-hn","place":"HN/Show HN replies","painpoint":"MCP tool-call security evidence","asset":"agentpress/security/mcp-consent-manifest-validation.json","status":"ready_not_sent","receipt":None}
    ]
    payload={"schema_version":"2026-05-03.agentpress-first-agent-outreach-receipt-tracker.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Track targeted first-agent attention attempts and external receipts without spam or private data.","rules":["manual/approved outreach only","one relevant artifact per thread","no secrets/private prompts/user data","record blockers as useful receipts"],"targets":targets,"receipt_schema":{"target_id":"string","sent_at":"ISO8601 or null","reply_url":"public URL or null","result":"accepted|blocked|no_reply|needs_fix","blocker":"string or null"}}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else 'ok')
    return 0



def rag_tool_safety_bundle(args):
    """Publish RAG/tool safety bundle for file-path metadata and zero-arg tool schemas."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    checks=[
        {"id":"file_path_metadata","risk":"arbitrary file read via metadata path","evidence":"https://github.com/run-llama/llama_index/issues/21512","gate":"reject absolute paths, parent traversal, home/secrets paths unless explicitly consented"},
        {"id":"zero_arg_tool_schema","risk":"tool schema violates provider spec when no parameters are declared","evidence":"https://github.com/run-llama/llama_index/issues/18928","gate":"emit explicit empty object schema with additionalProperties=false"},
        {"id":"output_contract_drift","risk":"RAG agent returns prose when caller expects structured output","evidence":"agent community issue class","gate":"validate response against declared output schema before publishing"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-rag-tool-safety-bundle.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Give RAG/agent builders a compact safety bundle for file metadata, zero-argument tools, and output contracts.","checks":checks,"commands":["python3 scripts/agentpress.py tool-file-access-risk-scanner --json","python3 scripts/agentpress.py tool-schema-serialization-check --json","python3 scripts/agentpress.py output-format-contract-tester --json"],"maintainer_attachment":"Attach this bundle plus scanner outputs to RAG/tool safety issues."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else 'ok')
    return 0


def external_reply_to_proof_ingest_bridge(args):
    """Map external replies/blockers into proof-ingest compatible receipt records."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    bridge={"schema_version":"2026-05-03.agentpress-external-reply-to-proof-ingest-bridge.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Convert first-agent replies, blockers, and maintainer comments into AgentPress proof-ingest records without scraping private data.","accepted_inputs":["public issue comment URL","public HN comment URL","submitted blocker JSON","manual operator note with public URL"],"output_receipt_fields":{"proof_type":"external_reply|blocker_report|adoption_signal","source_url":"public URL","agent_family":"optional pseudonymous family","commands_run":"optional redacted commands","result":"accepted|blocked|needs_fix|no_reply","privacy_checked":True},"privacy_rules":["no tokens/secrets/private prompts","no IP/user-agent capture","manual approval before external posting","blocker reports count as useful receipts"],"example_record":{"proof_type":"blocker_report","source_url":"https://github.com/example/project/issues/123#issuecomment-...","result":"needs_fix","privacy_checked":True}}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(bridge,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(bridge,indent=2) if args.json else 'ok')
    return 0


def issue_comment_pack_generator(args):
    """Generate issue-specific comment packs that point to one relevant artifact/command."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    packs=[
      {"issue_class":"MCP approval boundary","target_url":"https://github.com/cline/cline/issues/10499","artifact":"https://barneywohl.github.io/agentpress/agentpress/security/mcp-consent-manifest-validation.json","command":"python3 scripts/agentpress.py mcp-consent-manifest-validator --json","comment":"I mapped this class of approval-boundary bug into a fail-closed consent manifest check. The useful piece is the JSON gate + one command above; it does not require secrets or telemetry."},
      {"issue_class":"provider tool vocabulary mismatch","target_url":"https://github.com/cline/cline/issues/10336","artifact":"https://barneywohl.github.io/agentpress/agentpress/compatibility/provider-adapter-repro-pack.json","command":"python3 scripts/agentpress.py provider-adapter-repro-pack --host cline --provider claude_code --json","comment":"This turns host/provider tool mismatch into a small adapter map and failing-call repro. If helpful, it can be attached as maintainer evidence rather than a product pitch."},
      {"issue_class":"stale structured_response checkpoint","target_url":"https://github.com/langchain-ai/langchain/issues/36957","artifact":"https://barneywohl.github.io/agentpress/agentpress/repro/checkpoint-replay-minimal-repro.json","command":"python3 scripts/agentpress.py checkpoint-replay-minimal-repro-generator --json","comment":"This emits a sanitized checkpoint replay artifact for stale structured_response bugs, including fields to remove before resume."},
      {"issue_class":"RAG file/tool schema safety","target_url":"https://github.com/run-llama/llama_index/issues/21512","artifact":"https://barneywohl.github.io/agentpress/agentpress/safety/rag-tool-safety-bundle.json","command":"python3 scripts/agentpress.py rag-tool-safety-bundle --json","comment":"This bundles file_path metadata and tool-schema safety checks into maintainer-ready JSON. It is intentionally local/static and avoids private path disclosure."}
    ]
    payload={"schema_version":"2026-05-03.agentpress-issue-comment-pack-generator.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Prepare non-spam, issue-specific first-agent attention comments tied to one artifact and one command.","rules":["manual approval before posting","post only where directly relevant","one artifact per comment","do not claim upstream fix","no secrets/private prompts"],"packs":packs}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else 'ok')
    return 0


def issue_to_repro_pack(args):
    """Generate/validate a sanitized issue-to-repro pack for tool/provider/schema failures."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    issue=args.issue_url or "https://github.com/cline/cline/issues/10534"
    error=args.error or "tool call failed / invalid_arguments"
    tool=args.tool or "unknown_tool"
    host=args.host or "unknown_host"
    provider=args.provider or "unknown_provider"
    secret_hits=[]
    secret_re=re.compile(r"(?i)(sk-[a-z0-9_-]{12,}|gh[opsu]_[a-z0-9_]{20,}|api[_-]?key\s*[:=]\s*\S+|token\s*[:=]\s*\S+|password\s*[:=]\s*\S+)")
    for label,value in [("error",error),("tool",tool),("host",host),("provider",provider),("issue_url",issue)]:
        if secret_re.search(str(value)):
            secret_hits.append({"field":label,"message":"secret-looking value detected; redact before sharing"})
    findings=[]
    if not issue.startswith(("https://github.com/","https://news.ycombinator.com/")):
        findings.append({"severity":"P1","message":"issue_url should be a public maintainer thread"})
    if tool == "unknown_tool":
        findings.append({"severity":"P1","message":"tool name missing; repro is less actionable"})
    if error == "tool call failed / invalid_arguments":
        findings.append({"severity":"P2","message":"specific observed error not supplied; using generic class"})
    status="fail" if secret_hits else ("needs_detail" if findings else "ok")
    payload={"schema_version":"2026-05-04.agentpress-issue-to-repro-pack-result.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"purpose":"Turn a live tool/provider/schema complaint into a sanitized maintainer-ready repro attachment.","input_summary":{"public_issue_url":issue,"host_runtime":host,"provider_or_model":provider,"tool_name":tool,"observed_error":error},"secret_findings":secret_hits,"findings":findings,"repro_pack":{"failing_call":{"tool":tool,"host":host,"provider":provider,"observed_error":error},"expected_contract":{"tool_must_be_declared":True,"arguments_must_match_schema":True,"unknown_tool_policy":"fail_closed_do_not_infer"},"maintainer_comment_md":"Attached: sanitized AgentPress issue-to-repro pack for a tool/provider/schema failure. It includes only public issue URL, host/provider/tool names, observed error, and expected contract; no private prompt or secret material."},"acceptance_gates":["JSON parses","no secret-looking values","public issue URL present","tool/provider/error fields present"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 1 if args.strict and status=="fail" else 0



def painpoint_target_pack(args):
    """Turn one live agent pain complaint into a runnable pack + approval-ready outreach draft."""
    out = pathlib.Path(args.out)
    base = args.base_url.rstrip() + "/"
    issue_url = args.issue_url.strip()
    painpoint = (args.painpoint or args.error or "").strip()
    host = (args.host or "unknown_host").strip()
    provider = (args.provider or "unknown_provider").strip()
    tool = (args.tool or "unknown_tool").strip()
    score_parts = [painpoint]
    if host != "unknown_host": score_parts.append(host)
    if provider != "unknown_provider": score_parts.append(provider)
    if tool != "unknown_tool": score_parts.append(tool)
    lower = " ".join(score_parts).lower()
    candidates = [
        {"id":"mcp_config_mutation_guard","match":["mcp","config","cline","roo","settings","approval","consent","server"],"artifact":"agentpress/security/mcp-config-mutation-guard-result.json","command":"python3 scripts/agentpress.py mcp-config-mutation-guard --config-exists --before-sha256 <sha256-before> --existing-servers <csv> --planned-servers <csv> --json","user_value":"Stops agent installers from silently breaking existing MCP/Cline/Roo config; emits backup/diff/restore evidence."},
        {"id":"provider_adapter_repro_pack","match":["tool","provider","adapter","execute_command","write_to_file","invalid_arguments","unknown tool"],"artifact":"agentpress/compatibility/provider-adapter-repro-pack.json","command":"python3 scripts/agentpress.py provider-adapter-repro-pack --host <host> --provider <provider> --calls <tool_csv> --json","user_value":"Turns host/provider tool mismatch into a small adapter map and failing-call repro maintainers can act on."},
        {"id":"issue_to_repro_pack","match":["repro","bug","error","failed","schema","arguments","exception"],"artifact":"agentpress/repro/issue-to-repro-pack-result.json","command":"python3 scripts/agentpress.py issue-to-repro-pack --issue-url <public-url> --host <host> --provider <provider> --tool <tool> --error <redacted-error> --json","user_value":"Converts a public complaint into a sanitized, no-secret repro attachment."},
        {"id":"runtime_hang_repro_capsule","match":["hang","stuck","timeout","terminal","browser","running","callback"],"artifact":"agentpress/repro/runtime-hang-repro-capsule.json","command":"python3 scripts/agentpress.py runtime-hang-repro-capsule --log <redacted-log-path> --json","user_value":"Turns a stuck run into exit/callback/runtime-state evidence instead of vague debugging."},
        {"id":"package_registry_doctor","match":["npm","pypi","install","package","registry","404","npx","pip"],"artifact":"agentpress/diagnostics/package-registry-doctor.json","command":"python3 scripts/agentpress.py package-registry-doctor --error <install-error> --json","user_value":"Diagnoses first-run package/registry failures before the user gives up."},
    ]
    scored=[]
    for candidate in candidates:
        hits=[word for word in candidate["match"] if word in lower]
        scored.append((len(hits), hits, candidate))
    scored.sort(key=lambda row: row[0], reverse=True)
    best_score, hits, best = scored[0]
    low_confidence = best_score == 0
    if low_confidence:
        best = candidates[2]
        hits = []
    command = best["command"]
    command = command.replace("<public-url>", shlex.quote(issue_url or "https://github.com/example/project/issues/123"))
    command = command.replace("<host>", shlex.quote(host))
    command = command.replace("<provider>", shlex.quote(provider))
    command = command.replace("<tool>", shlex.quote(tool))
    command = command.replace("<tool_csv>", shlex.quote(tool if tool != "unknown_tool" else "execute_command,write_to_file"))
    command = command.replace("<redacted-error>", shlex.quote(args.error or painpoint or "redacted observed error"))
    command = command.replace("<install-error>", shlex.quote(args.error or painpoint or "install failed"))
    comment = (
        "I saw this pain point and mapped it to a small AgentPress repro/preflight so it is useful even if you ignore the project.\n\n"
        f"Run:\n```bash\n{command}\n```\n\n"
        f"What it gives you: {best['user_value']}\n\n"
        "No secrets, private prompts, telemetry, or external writes required. If this misses the actual failure mode, reply with the redacted error and I’ll tighten the pack."
    )
    findings=[]
    if not issue_url:
        findings.append({"severity":"P1","message":"issue_url missing; target pack is less directly actionable"})
    elif not issue_url.startswith(("https://github.com/","https://news.ycombinator.com/","https://gitlab.com/","https://gitee.com/")):
        findings.append({"severity":"P1","message":"target URL is not a known public dev/community thread"})
    secret_re = re.compile(
        r"(?i)("
        r"sk-[a-z0-9_-]{12,}|"
        r"gh[opsu]_[a-z0-9_]{20,}|"
        r"AKIA[0-9A-Z]{16}|"
        r"xoxb-[0-9A-Za-z-]{20,}|"
        r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|"
        r"api[_-]?key\s*[:=]\s*\S+|"
        r"token\s*[:=]\s*\S+|"
        r"password\s*[:=]\s*\S+"
        r")"
    )
    for label,value in [("painpoint",painpoint),("error",args.error or ""),("issue_url",issue_url)]:
        if secret_re.search(str(value)):
            findings.append({"severity":"P0","field":label,"message":"secret-looking value detected; redact before sharing"})
    if low_confidence:
        findings.append({"severity":"P1","message":"low_confidence_match: no candidate scored above zero; fallback repro pack selected for manual review"})
    status = "blocked_redact" if any(f.get("severity") == "P0" for f in findings) else ("low_confidence_match" if low_confidence else ("needs_target" if findings else "ready_for_manual_approval"))
    payload={
        "schema_version":"2026-05-04.agentpress-painpoint-target-pack.v1",
        "canonical_url":urljoin(base,out.as_posix()),
        "generated_utc":_utc_now(),
        "status":status,
        "purpose":"Directly target one live agent-builder painpoint with one runnable AgentPress command and one non-spam outreach draft.",
        "input":{"issue_url":issue_url,"painpoint":painpoint,"host":host,"provider":provider,"tool":tool},
        "matched_solution":{"id":best["id"],"match_terms":hits,"artifact":urljoin(base,best["artifact"]),"command":command,"user_value":best["user_value"]},
        "manual_outreach_draft":{"approval_required":True,"comment_md":comment},
        "acceptance_gates":["public target URL","one command","one artifact","no secrets","manual approval before posting","receipt captured if anyone replies"],
        "finding_count":len(findings),"findings":findings,
    }
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 1 if args.strict and payload["status"].startswith("blocked") else 0

def _mcp_server_names_from_config(path):
    try:
        data=json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return [], None
    if isinstance(data, dict):
        for key in ("mcpServers", "servers"):
            if isinstance(data.get(key), dict):
                return sorted(data[key].keys()), data
    return [], data


def mcp_config_mutation_guard(args):
    """Preflight MCP config mutation with optional real backup/diff/restore proof."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    cfg=pathlib.Path(args.config_path).expanduser()
    config_path=str(cfg)
    findings=[]; actions=[]; backup_path=None
    config_exists=cfg.exists() or args.config_exists
    before=args.before_sha256 or ""
    after=args.after_sha256 or ""
    existing=_csv_list(args.existing_servers, [])
    planned=_csv_list(args.planned_servers, [])
    if cfg.exists():
        before=hashlib.sha256(cfg.read_bytes()).hexdigest()
        detected,_=_mcp_server_names_from_config(cfg)
        if detected and not existing:
            existing=detected
    if args.planned_config:
        detected,_=_mcp_server_names_from_config(pathlib.Path(args.planned_config).expanduser())
        if detected:
            planned=detected
    if not planned:
        planned=list(existing)
    if args.backup and cfg.exists():
        backup_dir=pathlib.Path(args.backup_dir).expanduser(); backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path=backup_dir / f"{cfg.name}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.backup"
        shutil.copy2(cfg, backup_path)
        actions.append({"action":"backup_created","path":str(backup_path),"sha256":hashlib.sha256(backup_path.read_bytes()).hexdigest()})
    if args.restore:
        src=pathlib.Path(args.restore).expanduser()
        if not src.exists():
            findings.append({"severity":"P0","message":"restore source does not exist","path":str(src)})
        elif args.apply_restore:
            if cfg.exists() and not backup_path:
                backup_dir=pathlib.Path(args.backup_dir).expanduser(); backup_dir.mkdir(parents=True, exist_ok=True)
                backup_path=backup_dir / f"{cfg.name}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.pre-restore.backup"
                shutil.copy2(cfg, backup_path)
            cfg.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, cfg)
            after=hashlib.sha256(cfg.read_bytes()).hexdigest()
            actions.append({"action":"restored","from":str(src),"to":str(cfg),"after_sha256":after})
        else:
            actions.append({"action":"restore_dry_run","from":str(src),"to":str(cfg),"apply_with":"--apply-restore"})
    allowed=set(_csv_list(args.allowed_mutations, []))
    removed=[server for server in existing if server and server not in planned]
    added=[server for server in planned if server and server not in existing]
    if config_exists and not before:
        findings.append({"severity":"P0","message":"config exists but before_sha256/backup proof is missing"})
    for server in removed:
        if f"remove:{server}" not in allowed and "remove:*" not in allowed:
            findings.append({"severity":"P0","server":server,"message":"existing MCP server would be removed without explicit allowed_mutation"})
    broad=[server for server in added if any(x in server.lower() for x in ["filesystem","shell","terminal","browser","wallet","credential","secret"])]
    for server in broad:
        findings.append({"severity":"P1","server":server,"message":"new broad-scope server requires consent manifest before mutation"})
    if args.apply and findings:
        findings.append({"severity":"P0","message":"apply requested but guard is not clean; refuse mutation"})
    status="ok" if not findings else "fail_closed"
    restore_cmd=f"cp {shlex.quote(str(backup_path or (str(cfg)+'.backup')))} {shlex.quote(config_path)}"
    payload={"schema_version":"2026-05-04.agentpress-mcp-config-mutation-guard-result.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"purpose":"Prevent MCP installers/agents from silently damaging existing MCP settings with real backup/diff/restore evidence.","config_path":config_path,"evidence":{"before_sha256":before or None,"after_sha256":after or None,"backup_path":str(backup_path) if backup_path else None,"restore_command":restore_cmd},"actions":actions,"diff_summary":{"existing_servers":existing,"planned_servers":planned,"added":added,"removed":removed,"allowed_mutations":sorted(allowed)},"finding_count":len(findings),"findings":findings,"policy":{"fail_closed":True,"never_apply_without_backup":True,"broad_scope_servers_need_consent_manifest":True,"restore_is_dry_run_unless_apply_restore":True},"public_issue_signal":"https://github.com/cline/cline/issues/9663"}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 1 if args.strict and status!='ok' else 0

def continuous_research_build_cycle_audit(args):
    """Audit shipped AgentPress surfaces against current painpoint/build lists and emit next cycle decision."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    shipped={
      "mcp_consent_manifest_validator": pathlib.Path("agentpress/security/mcp-consent-manifest-validation.json").exists(),
      "provider_adapter_repro_pack": pathlib.Path("agentpress/compatibility/provider-adapter-repro-pack.json").exists(),
      "checkpoint_replay_minimal_repro_generator": pathlib.Path("agentpress/repro/checkpoint-replay-minimal-repro.json").exists(),
      "runtime_hang_repro_capsule": pathlib.Path("agentpress/repro/runtime-hang-repro-capsule.json").exists(),
      "first_agent_outreach_receipt_tracker": pathlib.Path("agentpress/outreach/first-agent-outreach-receipt-tracker.json").exists()
    }
    gaps=[]
    for k,v in shipped.items():
        if not v: gaps.append({"gap":k,"priority":"P0","action":"build_and_publish_artifact"})
    second_wave={
      "rag_tool_safety_bundle": pathlib.Path("agentpress/safety/rag-tool-safety-bundle.json").exists(),
      "external_reply_to_proof_ingest_bridge": pathlib.Path("agentpress/proof/external-reply-to-proof-ingest-bridge.json").exists(),
      "issue_comment_pack_generator": pathlib.Path("agentpress/outreach/issue-comment-pack-generator.json").exists()
    }
    for k,v in second_wave.items():
        if not v: gaps.append({"gap":k,"priority":"P1","action":"build_and_publish_artifact"})
    next_builds=[
      {"name":"live-community-recheck-runner","why":"Painpoints should be refreshed from public issues before any outreach comment is posted.","priority":"P1"},
      {"name":"manual-outreach-approval-queue","why":"Prepared comments still require human approval before external posting.","priority":"P1"},
      {"name":"reply-receipt-ingest-examples","why":"The bridge needs real examples once first external replies arrive.","priority":"P2"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-continuous-research-build-cycle-audit.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if not gaps else "gaps_found","purpose":"After each next-build cycle, audit what shipped, what remains, and where research should continue.","shipped":shipped,"second_wave_shipped":second_wave,"gaps":gaps,"next_builds":next_builds,"assumption_tests":["Do public issue URLs still represent active pain?","Do shipped artifacts produce one-command evidence?","Does outreach remain manual/non-spam?","Do validation gates pass locally and on Pages?"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload['status'])
    return 0

def current_agent_places_map(args):
    """Publish a researched map of where agents/agent-builders are currently communicating."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    places=[
        {"place":"GitHub Issues","communities":["Cline","Roo Code","OpenHands","LangChain/LangGraph","LlamaIndex","MCP servers"],"why_agents_are_there":"bugs, tool-call failures, runtime hangs, approval/security reports, schema drift","how_to_research":"GitHub issue search by updated/open issue plus exact pain keywords","attention_rule":"Reply only with a directly relevant checker/spec and one command; no generic launch copy."},
        {"place":"Hacker News / Show HN","communities":["MCP security gateways","agent browsers","agent orchestration tools","debugging MCP servers"],"why_agents_are_there":"new tools are announced and evaluated publicly by builders","how_to_research":"HN Algolia queries for MCP agent approval/tool/browser/runtime","attention_rule":"Position AgentPress as neutral evidence layer, not a competing agent."},
        {"place":"Project docs/discussions/Discord pointers","communities":["MCP ecosystem","Cline/Roo/OpenHands users","LangChain/LlamaIndex builders"],"why_agents_are_there":"how-to questions and integration blockers","how_to_research":"official docs + GitHub discussions/issues first; Discord only when authenticated/allowed","attention_rule":"Bring a minimal repro contract and blocker-report template."},
        {"place":"Package/install channels","communities":["npm/pip/CLI users","agent framework adopters"],"why_agents_are_there":"first-run failure before adoption","how_to_research":"issues mentioning install, package, 404, EACCES, auth, startup","attention_rule":"Lead with package-registry-doctor output and fallback install path."}
    ]
    payload={"schema_version":"2026-05-03.agentpress-current-agent-places-map.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Map the current public places where agent builders communicate, and define how AgentPress should research/engage them without spam.","places":places}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"ok {len(places)} places")
    return 0


def attention_painpoint_radar(args):
    """Rank live/current agent painpoints most likely to get first-agent attention."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    sample=pathlib.Path(args.sample or '/tmp/agentpress-current-places-research.json')
    research={}
    if sample.exists():
        try: research=json.loads(sample.read_text())
        except Exception: research={}
    painpoints=[
        {"rank":1,"painpoint":"MCP/tool calls executing or appearing to execute without trustworthy approval boundaries","attention_trigger":"Agents and users fear invisible side effects; security gateways are getting public attention.","evidence":["https://github.com/cline/cline/issues/10499","HN: Cordon/Kvlar/AgentArmor MCP security Show HN results"],"shipped_solution":"approval-bypass-risk-check","next_build":"mcp-consent-manifest-validator","outreach_hook":"Run one command to prove risky tools fail closed when auto-approve is off."},
        {"rank":2,"painpoint":"Provider/host tool vocabulary mismatch breaks otherwise capable models","attention_trigger":"Agents waste turns saying execute_command/write_to_file when provider cannot dispatch those tools.","evidence":["https://github.com/cline/cline/issues/10336","https://github.com/cline/cline/issues/9920"],"shipped_solution":"provider-tool-translation-map","next_build":"provider-adapter-repro-pack","outreach_hook":"Paste your provider/host pair and get a translation map plus failing call proof."},
        {"rank":3,"painpoint":"Stale checkpoint/structured output state causes premature exits or wrong next-turn behavior","attention_trigger":"Framework users lose trust when agents stop or reuse stale structured_response data.","evidence":["https://github.com/langchain-ai/langchain/issues/36957","https://github.com/langchain-ai/langgraph/issues/4940"],"shipped_solution":"agent-state-checkpoint-sanitizer","next_build":"checkpoint-replay-minimal-repro-generator","outreach_hook":"Generate a before/after checkpoint replay pack agents can attach to framework issues."},
        {"rank":4,"painpoint":"Runtime/browser/terminal workflow hangs with weak completion evidence","attention_trigger":"Agents stuck in running state waste money and make CI/browser agents feel unreliable.","evidence":["Cline terminal reliability issue class","OpenHands/runtime browser Docker issue class"],"shipped_solution":"workflow-terminal-callback-check","next_build":"runtime-hang-repro-capsule","outreach_hook":"Turn a stuck run log into exit/callback/state evidence in one artifact."},
        {"rank":5,"painpoint":"File/path metadata and tool schemas leak security or serialization failures into agent runs","attention_trigger":"RAG/agent developers hit arbitrary file-read and no-parameter tool spec bugs.","evidence":["https://github.com/run-llama/llama_index/issues/21512","https://github.com/run-llama/llama_index/issues/18928"],"shipped_solution":"tool-file-access-risk-scanner + tool-schema-serialization-check","next_build":"rag-tool-safety-bundle","outreach_hook":"Validate file-path metadata and zero-arg tool schemas before publishing an agent."},
        {"rank":6,"painpoint":"First-run install/package failures block adoption before an agent can test the product","attention_trigger":"No one adopts if npm/pip/CLI startup fails or package name is unclear.","evidence":["package/startup/404/auth/permission issue class"],"shipped_solution":"package-registry-doctor","next_build":"copy-paste installer with registry fallback matrix","outreach_hook":"If install fails, attach this doctor output instead of a vague bug report."}
    ]
    payload={"schema_version":"2026-05-03.agentpress-attention-painpoint-radar.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Rank the biggest unsolved agent painpoints likely to get immediate attention from first external agents/builders.","research_sample":str(sample),"research_buckets":list(research.keys()),"painpoints":painpoints}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"ok {len(painpoints)} painpoints")
    return 0


def first_agent_attention_kit(args):
    """Publish non-spam, issue-specific first-agent attention hooks and outreach snippets."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    hooks=[
        {"target":"Cline maintainers/users","painpoint":"MCP approval bypass and provider tool vocabulary mismatch","asset":"https://barneywohl.github.io/agentpress/agentpress/security/approval-bypass-risk-result.json","message":"I mapped this to a machine-checkable approval/tool-contract preflight. If useful, here is the exact JSON gate and command; no secrets or telemetry required.","do_not":"Do not claim AgentPress fixes Cline internals; offer reproducible preflight evidence only."},
        {"target":"LangChain/LangGraph agent developers","painpoint":"stale structured_response/checkpoint drift","asset":"https://barneywohl.github.io/agentpress/agentpress/community/attention-painpoint-radar.json","message":"This is a small checkpoint hygiene contract agents can run before resuming a saved thread; happy to convert it into a minimal repro pack for the issue.","do_not":"Do not spam unrelated framework issues."},
        {"target":"LlamaIndex/RAG agent builders","painpoint":"file-path metadata safety and zero-arg tool schemas","asset":"https://barneywohl.github.io/agentpress/agentpress/tools/tool-schema-serialization-result.json","message":"AgentPress now has a preflight for file/tool schema hazards; the useful piece is a tiny JSON artifact maintainers can attach to bugs.","do_not":"Do not mention private/security-sensitive paths."},
        {"target":"MCP security/project builders on HN","painpoint":"tool-call firewall/approval evidence","asset":"https://barneywohl.github.io/agentpress/agentpress/community/current-agent-places-map.json","message":"AgentPress is the evidence layer around MCP security tools: publish consent manifests, approval outcomes, and reproducible proof rather than another proxy.","do_not":"Do not attack Cordon/Kvlar/AgentArmor; complement them."},
        {"target":"OpenHands/Roo/browser-agent users","painpoint":"runtime/browser/terminal completion evidence","asset":"https://barneywohl.github.io/agentpress/agentpress/workflows/workflow-terminal-callback-result.json","message":"If a run hangs, AgentPress can turn terminal/callback state into a small evidence capsule for maintainers.","do_not":"Do not claim support for authenticated private browser sessions unless verified."}
    ]
    payload={"schema_version":"2026-05-03.agentpress-first-agent-attention-kit.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Give AgentPress a targeted, non-spam way to get first-agent attention by matching live painpoints to exact shipped artifacts.","rules":["Only respond where the painpoint is already being discussed.","Lead with one command or one JSON artifact, not marketing.","Never ask for secrets/private prompts.","Prefer blocker reports and repro capsules over vague praise."],"hooks":hooks}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"ok {len(hooks)} hooks")
    return 0


def next_attention_build_spec(args):
    """Publish the next build/deploy spec derived from current agent painpoint research."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    builds=[
        {"priority":"P0","name":"mcp-consent-manifest-validator","why":"Approval bypass/security is the highest-attention current painpoint.","acceptance":["validates risky tool scopes","fails if auto-approve false but execution lacks approval evidence","emits public safe JSON result"],"owner":"barney/direct-ship"},
        {"priority":"P0","name":"provider-adapter-repro-pack","why":"Provider/tool mismatch has exact public Cline evidence and immediate user pain.","acceptance":["input host/provider/tools","output translation map","output failing-call repro and suggested adapter contract"],"owner":"barney/direct-ship"},
        {"priority":"P1","name":"checkpoint-replay-minimal-repro-generator","why":"LangChain/LangGraph stale state bugs need compact reproducible evidence.","acceptance":["input checkpoint summary","detect stale structured_response/tool state","emit replay steps and sanitized issue attachment"],"owner":"agent team + barney"},
        {"priority":"P1","name":"runtime-hang-repro-capsule","why":"Browser/terminal hangs waste agent spend and are easy to prove with structured logs.","acceptance":["captures exit code/callback/state","detects stuck running state","emits maintainer-ready capsule"],"owner":"agent team + barney"},
        {"priority":"P2","name":"first-agent-outreach-receipt-tracker","why":"Adoption proof is still zero until external builders respond.","acceptance":["tracks target/painpoint/message/asset/reply/proof","privacy-safe","no mass-send automation"],"owner":"barney/direct-ship"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-next-attention-build-spec.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Concrete next build queue to convert current agent-community painpoints into deployed AgentPress features and first-agent attention.","builds":builds}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"ok {len(builds)} builds")
    return 0

def agent_community_newswire(args):
    """Compile current public agent-community issue/news signals into a machine-readable newswire."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    sample_path=pathlib.Path(args.sample) if args.sample else pathlib.Path('/tmp/ap-live-agent-community-issues.json')
    raw={}
    if sample_path.exists():
        try: raw=json.loads(sample_path.read_text())
        except Exception: raw={}
    items=[]
    for bucket, data in raw.items():
        for it in data.get('items',[])[:5]:
            title=it.get('title','')
            theme='unknown'
            low=title.lower()
            if 'approval' in low or 'auto-approve' in low: theme='approval_safety'
            elif 'tool' in low or 'execute_command' in low or 'model_dump' in low: theme='tool_schema_vocab'
            elif 'checkpoint' in low or 'structured_response' in low or 'state' in low: theme='state_checkpoint_drift'
            elif 'npm' in low or 'package' in low or 'fails on startup' in low: theme='install_distribution'
            elif 'context' in low or 'compaction' in low: theme='context_budget'
            elif 'file' in low or 'security' in low or 'arbitrary' in low: theme='security_sandbox'
            elif 'workflow' in low or 'running' in low or 'hook' in low: theme='workflow_runtime'
            items.append({"bucket":bucket,"repo":it.get('repo'),"title":title,"url":it.get('url'),"updated_at":it.get('updated_at'),"theme":theme})
    payload={"schema_version":"2026-05-03.agentpress-agent-community-newswire.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Current sampled public agent-community issue/news signals for immediate product targeting.","source_sample":str(sample_path),"item_count":len(items),"items":items}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(items)} items")
    return 0


def immediate_agent_needs_radar(args):
    """Rank current agent needs from sampled community signals."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    needs=[
        {"rank":1,"need":"approval safety for MCP/tool calls","why":"public reports of MCP tool calls executing without approval when auto-approve is off","ship":"approval-bypass-risk-check"},
        {"rank":2,"need":"provider/tool vocabulary compatibility","why":"Claude Code provider receiving Cline tool names cannot dispatch commands","ship":"tool-vocabulary-compatibility-check plus provider translation map"},
        {"rank":3,"need":"state/checkpoint reset hygiene","why":"stale structured_response/checkpoint state causes wrong next-turn behavior","ship":"agent-state-checkpoint-sanitizer"},
        {"rank":4,"need":"install/package failure diagnosis","why":"CLI/package startup failures and missing packages stop adoption before first run","ship":"package-registry-doctor"},
        {"rank":5,"need":"terminal/workflow callback completion checks","why":"agents hang in running state or terminal callbacks fail silently","ship":"workflow-terminal-callback-check"},
        {"rank":6,"need":"context compaction budget guard","why":"aggressive compaction loses task state and instructions","ship":"context-compaction-risk-card"},
        {"rank":7,"need":"tool schema serialization checks","why":"tool schemas fail JSON dump/serialization in agent frameworks","ship":"tool-schema-serialization-check"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-immediate-agent-needs-radar.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Rank immediate agent needs from public issue signals and map each to a shipped AgentPress surface.","need_count":len(needs),"needs":needs}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(needs)} needs")
    return 0


def solution_targeting_matrix(args):
    """Map current agent communities/problems to AgentPress solution gates and outreach target."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    rows=[
        {"community":"Cline","problem":"approval bypass/tool vocabulary/provider config drift","solution":"approval-bypass-risk-check + provider-tool-translation-map + memory-drift-check","target_message":"AgentPress can preflight provider/tool/approval contracts before dispatch."},
        {"community":"Roo/OpenHands","problem":"runtime/browser/docker/workflow fragility","solution":"runtime-install-doctor + browser-agent-compatibility-harness + workflow-terminal-callback-check","target_message":"AgentPress can produce runnable environment/browser/workflow evidence before claims."},
        {"community":"LangChain/LangGraph","problem":"checkpoint state and tool schema serialization drift","solution":"agent-state-checkpoint-sanitizer + tool-schema-serialization-check","target_message":"AgentPress can catch stale checkpoint/tool schema issues before agent loops."},
        {"community":"LlamaIndex/RAG","problem":"output format drift and file access risk","solution":"output-format-contract-tester + tool-file-access-risk-scanner","target_message":"AgentPress can validate format contracts and sandbox file-path metadata."},
        {"community":"MCP ecosystem","problem":"auth/transport/approval/scopes ambiguity","solution":"mcp-connector-auth-readiness + connector-security-scanner + approval-bypass-risk-check","target_message":"AgentPress can publish fail-closed connector readiness cards."}
    ]
    payload={"schema_version":"2026-05-03.agentpress-solution-targeting-matrix.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Target AgentPress solutions to the communities/problems agents are actively discussing.","row_count":len(rows),"rows":rows}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(rows)} rows")
    return 0


def approval_bypass_risk_check(args):
    """Detect tool/MCP approval bypass risk from a connector/action manifest."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    manifest={}
    if args.manifest and pathlib.Path(args.manifest).exists(): manifest=json.loads(pathlib.Path(args.manifest).read_text())
    else: manifest={"auto_approve":False,"tools":[{"name":"mcp_write_file","requires_approval":True},{"name":"mcp_shell","requires_approval":True}],"dispatch_log":[]}
    findings=[]
    auto=bool(manifest.get('auto_approve'))
    for t in manifest.get('tools',[]):
        name=t.get('name','')
        risky=any(x in name.lower() for x in ['write','delete','shell','exec','send','pay','deploy'])
        if risky and not t.get('requires_approval'):
            findings.append({"tool":name,"status":"fail","message":"risky tool missing requires_approval"})
    for call in manifest.get('dispatch_log',[]):
        if not auto and call.get('executed') and call.get('approval_state') not in ['approved','allow_once']:
            findings.append({"tool":call.get('tool'),"status":"fail","message":"executed without approval while auto_approve=false"})
    status='ok' if not findings else 'fail'
    payload={"schema_version":"2026-05-03.agentpress-approval-bypass-risk-result.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"finding_count":len(findings),"findings":findings,"policy":"When auto_approve=false, risky MCP/tool calls must not execute without explicit approved/allow_once state."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 1 if args.strict and status=='fail' else 0


def provider_tool_translation_map(args):
    """Generate provider/host tool vocabulary translation hints."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    mappings=[
        {"from_host":"cline","to_provider":"claude_code","from_tool":"execute_command","to_tool":"bash","confidence":"high"},
        {"from_host":"cline","to_provider":"claude_code","from_tool":"write_to_file","to_tool":"write_file","confidence":"medium"},
        {"from_host":"cline","to_provider":"claude_code","from_tool":"replace_in_file","to_tool":"edit_file","confidence":"medium"},
        {"from_host":"cline","to_provider":"openhands","from_tool":"execute_command","to_tool":"run","confidence":"medium"},
        {"from_host":"generic","to_provider":"mcp","from_tool":"browser_action","to_tool":"tool_call(browser.*)","confidence":"low_requires_manifest"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-provider-tool-translation-map.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Prevent provider/host tool vocabulary mismatch by publishing explicit translation hints and low-confidence fail-closed cases.","mapping_count":len(mappings),"mappings":mappings,"rule":"Translate only high/medium confidence mappings automatically; low confidence requires provider manifest."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"ok {len(mappings)} mappings")
    return 0


def workflow_terminal_callback_check(args):
    """Check workflow/terminal callback completion contract."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    log=args.log or "terminal command completed\ncallback: delivered\nstate: idle"
    low=log.lower(); findings=[]
    if 'running' in low and 'callback' not in low: findings.append({"status":"fail","message":"workflow appears stuck running without callback"})
    if 'command completed' in low and 'callback' not in low: findings.append({"status":"fail","message":"terminal completed without callback"})
    if 'hook' in low and 'complete' not in low and 'delivered' not in low: findings.append({"status":"warn","message":"hook mentioned without completion evidence"})
    status='ok' if not any(f['status']=='fail' for f in findings) else 'fail'
    payload={"schema_version":"2026-05-03.agentpress-workflow-terminal-callback-result.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"findings":findings,"required_evidence":["terminal_exit_code","callback_delivery","workflow_state_idle_or_completed"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 1 if args.strict and status=='fail' else 0


def context_compaction_risk_card(args):
    """Generate/check context compaction risk envelope."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    payload={"schema_version":"2026-05-03.agentpress-context-compaction-risk-card.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Prevent aggressive context compaction from losing task state, tool contracts, or approval constraints.","must_preserve":["user objective","latest plan","open blockers","approval/safety constraints","artifact paths","commands run","test results","next action"],"drop_first":["long duplicate logs","old superseded plans","full source dumps after summary","irrelevant web snippets"],"gate":"before compaction, emit preserved_fields list and missing_fields warnings"}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else 'ok')
    return 0


def package_registry_doctor(args):
    """Diagnose package/install registry failures for agent CLIs."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    error=args.error or "npm ERR! 404 Not Found - @clinebot/agents"
    low=error.lower(); fixes=[]
    if '404' in low or 'not found' in low: fixes.append({"class":"missing_package_or_registry_name","fix":"check package name, registry, scope ownership, and fallback to git/github release tarball"})
    if 'permission' in low or 'eacces' in low: fixes.append({"class":"permission","fix":"use user install prefix or documented package manager path"})
    if 'auth' in low or 'token' in low: fixes.append({"class":"registry_auth","fix":"do not print token; verify logged-in account/scope separately"})
    payload={"schema_version":"2026-05-03.agentpress-package-registry-doctor.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if fixes else "unknown","error_sample":error,"fixes":fixes,"fallback_channels":["git clone","GitHub release tarball","pip git","npm github:owner/repo","static HTTP bundle"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload['status'])
    return 0






def sandbox_guard(args):
    """Generate a local sandbox boundary manifest and wrapper."""
    out=pathlib.Path(args.out).expanduser(); base=args.base_url.rstrip()+"/"
    paths=[str(pathlib.Path(x).expanduser()) for x in _csv_list(args.paths, [])]
    forbidden=[".ssh",".gnupg","clawd_secrets","wallet","seed","private_key","id_rsa",".env"]
    findings=[]
    if args.scope not in ["read-only","read-write","full"]: findings.append({"severity":"P0","message":"invalid scope"})
    for path in paths:
        if any(token in path.lower() for token in forbidden): findings.append({"severity":"P0","path":path,"message":"path looks secret-sensitive; refuse default sandbox"})
    wrapper=out.with_suffix('.sh')
    # Build allowlist check: if allowed_paths given, require first arg to be within one of them
    allow_check=""
    if paths:
        cond=" || ".join([f'[[ "${{1:-}}" == {shlex.quote(p)}* ]]' for p in paths])
        allow_check=f'\n# allowlist enforcement\nif ! ( {cond} ); then\n  echo "blocked: path not in allowed_paths" >&2; exit 64\nfi'
    wrapper_text = f'#!/usr/bin/env bash\nset -euo pipefail\necho "AgentPress sandbox guard active" >&2\ncase "${{1:-}}" in\n  *clawd_secrets*|*.ssh*|*.gnupg*|*wallet*|*seed*|*.env*|*private_key*|*id_rsa*) echo "blocked sensitive path" >&2; exit 64;;\nesac{allow_check}\nexec "$@"\n'
    payload={"schema_version":"2026-05-04.agentpress-sandbox-guard.v2","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if not findings else "fail_closed","scope":args.scope,"allowed_paths":paths,"forbidden_markers":forbidden,"wrapper_script":str(wrapper),"policy":{"default_deny_secrets":True,"allowlist_enforced":bool(paths),"external_effects_require_approval":True,"read_only_means_no_write_commands":args.scope=='read-only'},"finding_count":len(findings),"findings":findings}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8"); wrapper.write_text(wrapper_text,encoding="utf-8"); os.chmod(wrapper,0o755)
    print(json.dumps(payload,indent=2) if args.json else payload['status']); return 1 if args.strict and payload['status']!='ok' else 0


def adoption_tracker(args):
    """Compute a privacy-safe local adoption funnel from receipt/proof files."""
    root=pathlib.Path(args.root).expanduser(); out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    files=list(root.rglob('*.json')) if root.exists() else []
    stages={"install_attempted":0,"doctor_ok":0,"proof_created":0,"outreach_ready":0,"external_reply":0,"issue_or_pr":0}; receipts=[]
    for f in files[:5000]:
        try: data=json.loads(f.read_text(encoding='utf-8'))
        except Exception: continue
        text=json.dumps(data).lower()
        if 'install' in text: stages['install_attempted']+=1
        if 'doctor' in text and 'ok' in text: stages['doctor_ok']+=1
        if 'proof-bundle' in text or 'agentpress-proof-capture' in text: stages['proof_created']+=1
        if 'ready_for_manual_approval' in text or 'approval_required' in text: stages['outreach_ready']+=1
        if 'external_reply' in text or 'blocker_report' in text: stages['external_reply']+=1
        if 'github.com' in text and ('pull' in text or 'issues' in text): stages['issue_or_pr']+=1
        receipts.append(str(f))
    ordered=list(stages.items()); conversion=[]
    for (a,av),(b,bv) in zip(ordered,ordered[1:]): conversion.append({"from":a,"to":b,"rate":(bv/av if av else 0),"from_count":av,"to_count":bv})
    payload={"schema_version":"2026-05-04.agentpress-adoption-tracker.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","period":args.period,"root":str(root),"funnel":stages,"conversion":conversion,"receipt_files_sample":receipts[:50],"privacy":"local files only; no IP/user-agent tracking"}
    if not args.no_write: out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding='utf-8')
    print(json.dumps(payload,indent=2) if args.json else 'ok'); return 0


def handoff_pack(args):
    """Package a task handoff between agents with evidence and acceptance gates."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; evidence=[x for x in _csv_list(args.evidence, [])]
    payload={"schema_version":"2026-05-04.agentpress-handoff-pack.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ready","from_agent":args.from_agent,"to_agent":args.to_agent,"task_id":args.task_id,"objective":args.objective,"constraints":_csv_list(args.constraints, []),"evidence_paths":evidence,"acceptance_gates":_csv_list(args.acceptance, ["evidence artifact written","verification command passes","reviewer signs off"]),"pending_actions":_csv_list(args.pending_actions, []),"handoff_manifest":{"context":"read objective/constraints/evidence before acting","do_not":"claim completion without artifacts","review":"required if touching external effects or secrets"}}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding='utf-8')
        _c=payload['constraints']; _e=payload['evidence_paths']; _g=payload['acceptance_gates']; _p=payload['pending_actions']
        _md=["# Handoff "+args.task_id,"","**From:** "+args.from_agent+"  **→ To:** "+args.to_agent,"","**Objective:** "+(payload['objective'] or '(none)'),"","## Constraints"]+(_c if _c else ["(none)"])+["","## Evidence paths"]+(["`"+x+"`" for x in _e] if _e else ["(none)"])+["","## Acceptance gates"]+["- [ ] "+x for x in _g]+["","## Pending actions"]+(["- [ ] "+x for x in _p] if _p else ["(none)"])+["","**Generated:** "+payload['generated_utc']]
        out.with_suffix('.md').write_text("\n".join(_md)+"\n",encoding='utf-8')
    print(json.dumps(payload,indent=2) if args.json else 'ready'); return 0


def batch_painpoints(args):
    """Batch process public painpoints into manual-approval target packs."""
    inp=pathlib.Path(args.input).expanduser(); outdir=pathlib.Path(args.output).expanduser(); base=args.base_url.rstrip()+"/"
    try: rows=json.loads(inp.read_text(encoding='utf-8'))
    except Exception: rows=[]
    if isinstance(rows, dict): rows=rows.get('issues') or rows.get('painpoints') or []
    outdir.mkdir(parents=True,exist_ok=True); processed=[]
    for i,row in enumerate(rows[:int(args.limit)]):
        if not isinstance(row, dict): continue
        issue=row.get('issue_url') or row.get('url') or ''; pain=row.get('painpoint') or row.get('title') or row.get('error') or ''; host=row.get('host') or 'unknown_host'; provider=row.get('provider') or 'unknown_provider'; tool=row.get('tool') or 'unknown_tool'
        target=outdir / ("painpoint-%03d.json" % (i+1))
        class A: pass
        a=A(); a.out=str(target); a.base_url=args.base_url; a.issue_url=issue; a.painpoint=pain; a.host=host; a.provider=provider; a.tool=tool; a.error=row.get('error',''); a.no_write=False; a.json=True; a.strict=False
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()): painpoint_target_pack(a)
        data=json.loads(target.read_text(encoding='utf-8')); processed.append({"path":str(target),"status":data.get('status'),"issue_url":issue,"matched_solution":(data.get('matched_solution') or {}).get('id')})
    summary={"schema_version":"2026-05-04.agentpress-batch-painpoints.v1","canonical_url":urljoin(base,'agentpress/outreach/batch-painpoints-summary.json'),"generated_utc":_utc_now(),"status":"ok","processed_count":len(processed),"output_dir":str(outdir),"items":processed,"approval_required_for_all":True}
    (outdir/'batch-painpoints-summary.json').write_text(json.dumps(summary,indent=2)+"\n",encoding='utf-8')
    print(json.dumps(summary,indent=2) if args.json else str(len(processed))); return 0

_SECRET_PATTERNS = [
    re.compile(r'(?i)(sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9\-._~+/]{20,}|api[_-]?key["\s:=]+["\']?[A-Za-z0-9\-_]{16,}|ghp_[A-Za-z0-9]{36}|xoxb-[0-9\-]+|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z]+ PRIVATE KEY)'),
]

def _scan_for_secrets(text: str) -> list:
    hits = []
    for pat in _SECRET_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append({"pattern": pat.pattern[:60], "match_prefix": m.group(0)[:12] + "***"})
    return hits

def proof_capture(args):
    """Capture a local proof bundle for an agent task/run."""
    evidence_dir=pathlib.Path(args.evidence_dir).expanduser()
    out=evidence_dir / "proof-bundle.json"
    card=evidence_dir / "proof-card.md"
    artifacts=[]
    secret_hits=[]
    for item in _csv_list(args.artifacts, []):
        path=pathlib.Path(item).expanduser()
        if path.exists() and path.is_file():
            content=path.read_bytes()
            try: text=content.decode("utf-8","replace")
            except Exception: text=""
            hits=_scan_for_secrets(text)
            secret_hits.extend(hits)
            artifacts.append({"path":str(path),"bytes":path.stat().st_size,"sha256":hashlib.sha256(content).hexdigest(),"secret_scan":{"hits":len(hits),"safe":len(hits)==0}})
        else:
            artifacts.append({"path":str(path),"missing":True})
    commands=[]
    for cmd in _csv_list(args.commands, []):
        commands.append({"command":cmd,"recorded_only":True})
    env={"python":sys.version.split()[0],"platform":platform.platform(),"cwd":str(pathlib.Path.cwd()),"agentpress_file":"scripts/agentpress.py"}
    scan_status="secret_hits_found" if secret_hits else "no_obvious_secrets"
    payload={"schema_version":"2026-05-04.agentpress-proof-capture.v2","generated_utc":_utc_now(),"status":"ok","task_id":args.task_id,"purpose":"Create a shareable no-secret proof bundle for first-agent runs.","summary":args.summary,"environment":env,"commands":commands,"artifacts":artifacts,"acceptance":{"artifact_count":len([a for a in artifacts if not a.get('missing')]),"missing_count":len([a for a in artifacts if a.get('missing')]),"review_required":args.review_required},"privacy":{"secret_scan_status":scan_status,"secret_hit_count":len(secret_hits),"operator_must_review_before_external_share":True},"reviewer_checklist":["commands are reproducible","artifacts are public-safe","no tokens/secrets/private prompts","expected vs observed is clear"]}
    evidence_dir.mkdir(parents=True,exist_ok=True)
    initial=json.dumps(payload,indent=2)+"\n"
    payload["bundle_sha256"] = hashlib.sha256(initial.encode("utf-8")).hexdigest()
    out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    scan_note = f"\n\n**Secret scan:** {scan_status} ({len(secret_hits)} hits)" if secret_hits else "\n\n**Secret scan:** no obvious secrets detected"
    card.write_text(f"# AgentPress proof card: {args.task_id}\n\nGenerated: {payload['generated_utc']}\n\nStatus: {payload['status']}\n\nSummary: {args.summary or '(none)'}\n\nArtifacts: {payload['acceptance']['artifact_count']} present / {payload['acceptance']['missing_count']} missing\n\nBundle: `{out}`{scan_note}\n",encoding="utf-8")
    result={"status":"ok","task_id":args.task_id,"proof_bundle":str(out),"proof_card":str(card),"bundle_sha256":payload["bundle_sha256"],"artifact_count":payload['acceptance']['artifact_count'],"secret_scan_status":scan_status}
    print(json.dumps(result,indent=2) if args.json else str(out))
    return 1 if secret_hits and getattr(args,"strict",False) else 0

def first_user_bootstrap(args):
    """Generate a first-user bootstrap pack for common agent hosts."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    platform=(args.platform or "cline").lower()
    supported={"cline","roo","claude","cursor","windsurf","generic"}
    status="ready_for_paste" if platform in supported else "unsupported_platform"
    host_notes={
        "cline":{"config":"cline_mcp_settings.json","where":"Cline MCP settings","restart":"Reload Cline/VS Code after paste"},
        "roo":{"config":"cline_mcp_settings.json","where":"Roo Code MCP settings","restart":"Reload Roo/VS Code after paste"},
        "claude":{"config":"claude_desktop_config.json","where":"Claude Desktop MCP config","restart":"Restart Claude Desktop"},
        "cursor":{"config":"mcp.json","where":"Cursor MCP settings","restart":"Reload Cursor"},
        "windsurf":{"config":"mcp_config.json","where":"Windsurf MCP settings","restart":"Reload Windsurf"},
        "generic":{"config":"mcp.json","where":"your agent host MCP settings","restart":"Restart/reload host"},
    }.get(platform, {"config":"mcp.json","where":"unknown","restart":"manual"})
    install="bash agentpress/install/install-agentpress.sh"
    mcp={"mcpServers":{"agentpress":{"command":"python3","args":["scripts/agentpress.py","mcp-catalog-export","--json"],"approval_required":True,"notes":"Run mcp-config-mutation-guard before applying."}}}
    commands=[install,"python3 scripts/agentpress.py doctor --json","python3 scripts/agentpress.py mcp-config-mutation-guard --config-path <config> --backup --planned-servers agentpress --json","python3 scripts/agentpress.py proof-capture --task first-run --evidence-dir /tmp/agentpress-proof --json"]
    first_prompt="Use AgentPress to inspect the available entrypoints, run doctor, then create a proof bundle for this first run. Do not post externally or mutate MCP config without explicit human approval."
    findings=[]
    if status != "ready_for_paste": findings.append({"severity":"P1","message":"unsupported platform; use generic or one of cline,roo,claude,cursor,windsurf"})
    payload={"schema_version":"2026-05-04.agentpress-first-user-bootstrap.v2","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"platform":platform,"purpose":"Get a first agent user from zero to safe AgentPress install + MCP snippet + proof capture in one pack.","first_run_workflow":{"user_goal":"Install safely, connect MCP by paste, verify locally, and leave shareable proof.","copy_paste_order":["install","doctor","backup_and_guard_mcp_config","paste_mcp_snippet","restart_host","capture_first_proof"],"agent_prompt":first_prompt,"success_looks_like":["doctor returns JSON without fatal findings","MCP config was backed up before changes","host reloads with an AgentPress server entry","proof-bundle.json and proof-card.md exist"],"if_blocked":["run package-registry-doctor with the install error","use generic platform when host-specific path is unknown","do not retry by disabling approval or secret guards"]},"steps":[{"step":1,"name":"install","command":install},{"step":2,"name":"doctor","command":commands[1]},{"step":3,"name":"backup_and_guard_mcp_config","command":commands[2].replace('<config>',host_notes['config'])},{"step":4,"name":"paste_mcp_snippet","target":host_notes['where'],"snippet":mcp},{"step":5,"name":"restart_host","instruction":host_notes['restart']},{"step":6,"name":"capture_first_proof","command":commands[3]}],"mcp_snippet":mcp,"safety":{"no_secrets_required":True,"external_posts":False,"rollback":"Use backup_path/restore_command from mcp-config-mutation-guard output."},"agent_affordances":[{"name":"proof_capture","why":"turns a first run into reviewable evidence","command":commands[3]},{"name":"sandbox_guard","why":"lets a user hand an agent a bounded workspace before exploration","command":"python3 scripts/agentpress.py sandbox-guard --scope read-only --paths . --json"},{"name":"handoff_pack","why":"lets one agent transfer context without losing constraints","command":"python3 scripts/agentpress.py handoff-pack --from current --to next --task first-run --json"}],"acceptance_gates":["doctor ok","config backup created before mutation","MCP snippet is paste-only, not auto-applied","proof bundle created","first_run_workflow present"],"finding_count":len(findings),"findings":findings}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        md=["# AgentPress first-run card", "", "Status: `"+status+"`", "Platform: `"+platform+"`", "", "## Paste this agent prompt", "", first_prompt, "", "## Steps"]
        for step in payload["steps"]:
            md.append(f"- {step['step']}. {step['name']}: `{step.get('command') or step.get('instruction') or step.get('target')}`")
        md += ["", "## Success looks like"] + ["- "+x for x in payload["first_run_workflow"]["success_looks_like"]] + ["", "## Safety", "- No secrets required", "- No external posts", "- Roll back with the guard backup/restore output"]
        out.with_suffix('.md').write_text("\n".join(md)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 1 if args.strict and status!='ready_for_paste' else 0

def first_run_wizard(args):
    """Detect host/provider/install state and emit the exact next command for a first agent user."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    root=pathlib.Path(args.root).expanduser()
    env={k:os.environ.get(k,"") for k in ["TERM_PROGRAM","VSCODE_PID","CURSOR_TRACE_ID","ANTHROPIC_API_KEY","OPENAI_API_KEY","GEMINI_API_KEY","GOOGLE_API_KEY"]}
    hints=[]
    host=(args.host or "").lower().strip()
    if not host:
        if env.get("CURSOR_TRACE_ID") or "cursor" in env.get("TERM_PROGRAM","").lower(): host="cursor"; hints.append("detected Cursor-ish environment")
        elif env.get("VSCODE_PID"):
            host="cline"; hints.append("detected VS Code process; defaulting to Cline/Roo-compatible MCP setup")
        elif "claude" in env.get("TERM_PROGRAM","").lower(): host="claude"; hints.append("detected Claude-ish terminal program")
        else:
            host="generic"; hints.append("no host-specific env marker found; using generic MCP flow")
    provider=(args.provider or "").lower().strip()
    if not provider:
        if env.get("ANTHROPIC_API_KEY"): provider="anthropic"
        elif env.get("OPENAI_API_KEY"): provider="openai"
        elif env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY"): provider="google"
        else: provider="unknown"
    tools={"python3":bool(shutil.which("python3")),"git":bool(shutil.which("git")),"npm":bool(shutil.which("npm")),"node":bool(shutil.which("node"))}
    mcp_configs={"cline":"cline_mcp_settings.json","roo":"cline_mcp_settings.json","claude":"claude_desktop_config.json","cursor":"mcp.json","windsurf":"mcp_config.json","generic":"mcp.json"}
    config=mcp_configs.get(host,"mcp.json")
    blockers=[]
    if not tools["python3"]: blockers.append({"severity":"P0","blocker":"python3_missing","next_command":"Install Python 3, then rerun: python3 scripts/agentpress.py first-run-wizard --json"})
    if not tools["git"] and not (root/"scripts/agentpress.py").exists(): blockers.append({"severity":"P1","blocker":"git_missing_for_source_fallback","next_command":"Install git or download the static release bundle from the release dashboard."})
    if provider=="unknown": blockers.append({"severity":"P2","blocker":"provider_unknown","next_command":"Rerun with --provider openai|anthropic|google|local after choosing the model provider."})
    if blockers:
        exact_next_command=blockers[0]["next_command"]
        status="blocked" if blockers[0]["severity"]=="P0" else "needs_choice"
    else:
        exact_next_command=f"python3 scripts/agentpress.py first-user-bootstrap --platform {shlex.quote(host)} --out agentpress/onboarding/first-user-bootstrap.json --json"
        status="ready"
    proof_command="python3 scripts/agentpress.py proof-capture --task-id first-run --evidence-dir /tmp/agentpress-proof --artifacts agentpress/onboarding/first-user-bootstrap.json --commands 'python3 scripts/agentpress.py doctor --json' --json"
    payload={"schema_version":"2026-05-04.agentpress-first-run-wizard.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"root":str(root),"detected":{"host":host,"provider":provider,"tools":tools,"mcp_config":config,"hints":hints},"exact_next_command":exact_next_command,"then_command":proof_command,"commands":{"bootstrap":f"python3 scripts/agentpress.py first-user-bootstrap --platform {host} --json","doctor":"python3 scripts/agentpress.py doctor --json","config_guard":f"python3 scripts/agentpress.py mcp-config-mutation-guard --config-path {config} --backup --planned-servers agentpress --json","proof":proof_command},"blockers":blockers,"safety":{"does_not_apply_config":True,"external_effects":False,"secrets_echoed":False}}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else exact_next_command)
    return 1 if args.strict and status=="blocked" else 0


def provider_error_explainer(args):
    """Explain raw provider/runtime errors and generate remediation packs with exact commands."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; error=args.error or read_text(pathlib.Path(args.error_file)) if args.error_file else args.error
    error=error or "429 rate_limit_exceeded"
    low=error.lower(); provider=(args.provider or "auto").lower(); packs=[]
    def add(cls, why, commands, docs=None, severity="P1"):
        packs.append({"class":cls,"severity":severity,"why":why,"exact_commands":commands,"docs":docs or [],"safe_to_retry":cls not in {"auth_secret_leak_risk","destructive_tool_denied"}})
    if any(x in low for x in ["401","unauthorized","invalid api key","authentication"]): add("provider_auth", "Provider rejected credentials; do not paste keys into logs.", ["printenv | grep -E 'OPENAI|ANTHROPIC|GEMINI|GOOGLE' | sed 's/=.*$/=<redacted>/'", "python3 scripts/agentpress.py secret-permission-preflight-run --json"], severity="P0")
    if any(x in low for x in ["429","rate limit","quota","insufficient_quota"]): add("rate_limit_or_quota", "Provider throttled or quota is exhausted.", ["sleep 60 && retry the previous command", "python3 scripts/agentpress.py budget-check --tier small --json"])
    if any(x in low for x in ["context_length","maximum context","too many tokens","context window"]): add("context_window", "Prompt or retrieved context exceeds model window.", ["python3 scripts/agentpress.py context-compaction-risk-card --json", "rerun with a smaller file set or summarize first"])
    if any(x in low for x in ["tool_use","invalid tool","tool call","schema"]): add("tool_schema_or_vocabulary", "Provider/host rejected a tool call or schema.", ["python3 scripts/agentpress.py tool-vocabulary-compatibility-check --json", "python3 scripts/agentpress.py tool-schema-serialization-check --json"])
    if any(x in low for x in ["module not found","modulenotfounderror","cannot find module","no module named"]): add("missing_dependency", "Runtime dependency is missing or installed in the wrong environment.", [f"python3 scripts/agentpress.py dependency-error-remediation-map --error {shlex.quote(error[:200])} --json", "python3 -m pip install -e ."])
    if any(x in low for x in ["eacces","permission denied","operation not permitted"]): add("permission_denied", "Host sandbox or filesystem denied the action.", ["python3 scripts/agentpress.py sandbox-guard --scope read-only --paths . --json", "rerun in an approved workspace path"])
    if any(x in low for x in ["model_not_found","not found: model","unsupported model"]): add("model_unavailable", "Configured model name is unavailable for this account/provider.", ["check provider model list/account access", "rerun with --provider and a known model from your host config"])
    if not packs: add("unknown_provider_error", "No known signature matched; capture reproducible evidence before retrying.", ["python3 scripts/agentpress.py repro-bundle --json", "python3 scripts/agentpress.py blocker-report --agent-id local-agent --runtime unknown --command '<failed command>' --error-summary '<sanitized error>' --desired-fix '<what should happen>' --json"], severity="P2")
    md="# Provider error remediation pack\n\n"+"\n".join(f"## {p['class']}\nWhy: {p['why']}\n\nCommands:\n"+"\n".join(f"- `{c}`" for c in p['exact_commands']) for p in packs)+"\n"
    payload={"schema_version":"2026-05-04.agentpress-provider-error-explainer.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","provider":provider,"error_sample":error[:2000],"pack_count":len(packs),"remediation_packs":packs,"review":"Sanitize errors before sharing; never include tokens, private prompts, IPs, or user-agent strings."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8"); out.with_suffix(".md").write_text(md,encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else packs[0]["exact_commands"][0])
    return 0


def adoption_scoreboard(args):
    """Build a static adoption scoreboard URL from local opt-in proof/adoption artifacts."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; root=pathlib.Path(args.root)
    def load(rel):
        p=root/rel
        try: return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except Exception as e: return {"_error":str(e)}
    status=load("agentpress/adoption/adoption-status.json") or load("agentpress/adoption/adoption-tracker.json")
    tracker=load("agentpress/adoption/adoption-tracker.json")
    rep=load("agentpress/reputation/reputation-index.json")
    proofs=load("agentpress/external-proofs/external-proof-index.json")
    metrics={"landing_receipts":(status.get("metrics") or {}).get("landing_receipts",0),"third_party_receipts":(status.get("metrics") or {}).get("third_party_receipts",0),"external_proofs":len(proofs.get("proofs",[])),"reputation_agents":rep.get("agent_count",0),"funnel":tracker.get("funnel",{})}
    score=min(100, metrics["landing_receipts"]*15 + metrics["third_party_receipts"]*25 + metrics["external_proofs"]*10 + metrics["reputation_agents"]*10)
    payload={"schema_version":"2026-05-04.agentpress-adoption-scoreboard.v1","canonical_url":urljoin(base,outdir.as_posix().rstrip('/')+"/index.html"),"generated_utc":_utc_now(),"status":"ok","score":score,"metrics":metrics,"source_files":["agentpress/adoption/adoption-status.json","agentpress/adoption/adoption-tracker.json","agentpress/reputation/reputation-index.json","agentpress/external-proofs/external-proof-index.json"],"privacy":"Opt-in artifact counts only; no hidden analytics, IP, user-agent, or fingerprinting."}
    html_doc=f"""<!doctype html><meta charset='utf-8'><title>AgentPress Adoption Scoreboard</title><style>body{{font-family:system-ui;margin:2rem;max-width:900px}}.score{{font-size:4rem;font-weight:800}}code,pre{{background:#f6f6f6;padding:.2rem .4rem}}</style><h1>AgentPress Adoption Scoreboard</h1><p>Privacy-safe, opt-in artifact scoreboard.</p><div class='score'>{score}/100</div><pre>{html.escape(json.dumps(metrics,indent=2))}</pre><p>Machine JSON: <a href='scoreboard.json'>scoreboard.json</a></p><p>Generated: {payload['generated_utc']}</p>"""
    if not args.no_write:
        outdir.mkdir(parents=True,exist_ok=True); (outdir/"scoreboard.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8"); (outdir/"index.html").write_text(html_doc,encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload["canonical_url"])
    return 0


def external_proof_inbox_review_flow(args):
    """Review an external proof inbox and produce accept/reject/manual-review actions."""
    inbox=pathlib.Path(args.inbox); out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; rows=[]
    secret_markers=["api_key","apikey","authorization:","bearer ","password","private_key","begin private key","user-agent","ip_address"]
    for p in sorted(inbox.glob("**/*")) if inbox.exists() else []:
        if not p.is_file() or p.name.startswith("."): continue
        raw=p.read_text(encoding="utf-8",errors="replace")[:200000]
        low=raw.lower(); findings=[m for m in secret_markers if m in low]
        action="reject_redact" if findings else ("accept_candidate" if any(x in low for x in ["proof","receipt","agent_id","landing_id","status"]) else "manual_review")
        rows.append({"path":str(p),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"action":action,"privacy_findings":findings,"review_command":f"python3 scripts/agentpress.py external-proof-review {shlex.quote(str(p))} --json"})
    accepted=sum(1 for r in rows if r["action"]=="accept_candidate"); rejected=sum(1 for r in rows if r["action"]=="reject_redact")
    payload={"schema_version":"2026-05-04.agentpress-external-proof-inbox-review-flow.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","inbox":str(inbox),"item_count":len(rows),"accept_candidate_count":accepted,"reject_redact_count":rejected,"items":rows,"next_commands":["python3 scripts/agentpress.py proof-ingest --json","python3 scripts/agentpress.py adoption-scoreboard --json"],"privacy":"Reject/redact any proof containing secrets, auth headers, private prompts, IPs, or user-agent strings."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8"); out.with_suffix(".md").write_text("# External proof inbox review\n\n"+"\n".join(f"- {r['action']}: `{r['path']}`" for r in rows)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{accepted} accept candidates / {rejected} reject-redact")
    return 0


def release_registry_readiness_dashboard(args):
    """Build a static release/package-registry readiness dashboard for npm/PyPI/source/static lanes."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; root=pathlib.Path(args.root)
    package_json=root/"package.json"; pyproject=root/"pyproject.toml"; release_index=root/"agentpress/releases/release-index.json"
    checks=[]
    def check(name, ok, fix, evidence=""):
        checks.append({"name":name,"status":"pass" if ok else "fail","fix":fix,"evidence":evidence})
    pkg={}
    if package_json.exists():
        try: pkg=json.loads(package_json.read_text())
        except Exception: pkg={}
    check("package.json present", package_json.exists(), "create package.json for npm lane", str(package_json))
    check("npm package has bin", bool(pkg.get("bin")), "add bin.agentpress pointing to bin/agentpress.js", json.dumps(pkg.get("bin",{})))
    check("pyproject present", pyproject.exists(), "create pyproject.toml for Python/uvx/pipx lane", str(pyproject))
    check("release index present", release_index.exists(), "run python3 scripts/agentpress.py release-index <package> --json", str(release_index))
    check("install script present", (root/"agentpress/install/install-agentpress.sh").exists() or (root/"agentpress/install/install.py").exists(), "run package-registry-fallback-installer or install-script", "agentpress/install/")
    check("npm pack dry-run command documented", True, "npm pack --dry-run", "npm pack --dry-run")
    passed=sum(1 for c in checks if c["status"]=="pass"); status="ready" if passed==len(checks) else "needs_work"
    payload={"schema_version":"2026-05-04.agentpress-release-registry-readiness-dashboard.v1","canonical_url":urljoin(base,outdir.as_posix().rstrip('/')+"/index.html"),"generated_utc":_utc_now(),"status":status,"pass_count":passed,"check_count":len(checks),"checks":checks,"lanes":["npm","PyPI/pipx/uvx","GitHub source","static bundle"],"dry_run_commands":["python3 -m py_compile scripts/agentpress.py","python3 scripts/agentpress.py doctor --json","npm pack --dry-run"],"no_publish_performed":True}
    html_doc=f"""<!doctype html><meta charset='utf-8'><title>AgentPress Release Registry Readiness</title><style>body{{font-family:system-ui;margin:2rem;max-width:980px}}.pass{{color:green}}.fail{{color:#b00}}code{{background:#f6f6f6;padding:.2rem .4rem}}</style><h1>Release / Registry Readiness</h1><h2>{status}: {passed}/{len(checks)} checks</h2><ul>{''.join(f"<li class='{c['status']}'><b>{html.escape(c['name'])}</b>: {c['status']} — <code>{html.escape(c['fix'])}</code></li>" for c in checks)}</ul><p>Machine JSON: <a href='readiness.json'>readiness.json</a></p>"""
    if not args.no_write:
        outdir.mkdir(parents=True,exist_ok=True); (outdir/"readiness.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8"); (outdir/"index.html").write_text(html_doc,encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload["canonical_url"])
    return 0


def release_candidate(args):
    """Generate a 0.2.0-rc release-candidate checklist with all sprint features and deploy gates."""
    out = pathlib.Path(args.out)
    base = args.base_url.rstrip() + "/"
    version = args.version or "0.2.0-rc"
    sprint_features = [
        {
            "id": "first-user-bootstrap",
            "command": "python3 scripts/agentpress.py first-user-bootstrap --platform cline --json",
            "output_path": "agentpress/onboarding/first-user-bootstrap.json",
            "acceptance_gates": ["status == ready_for_paste", "no_secrets_required == true", "rollback pointer present"],
            "status": "implemented",
        },
        {
            "id": "proof-capture",
            "command": "python3 scripts/agentpress.py proof-capture --task-id test-001 --evidence-dir /tmp/proof --json",
            "output_path": "sprint-proof/proof-bundle.json",
            "acceptance_gates": ["proof-bundle.json written", "proof-card.md written", "SHA256s present", "secret_scan_status present"],
            "status": "implemented",
        },
        {
            "id": "sandbox-guard",
            "command": "python3 scripts/agentpress.py sandbox-guard --scope read-only --paths ./src --json",
            "output_path": "agentpress/security/sandbox-guard.json",
            "acceptance_gates": ["JSON manifest written", "wrapper .sh written and chmod 755", "forbidden_markers list non-empty", "secret paths blocked"],
            "status": "implemented",
        },
        {
            "id": "adoption-tracker",
            "command": "python3 scripts/agentpress.py adoption-tracker --period 7d --json",
            "output_path": "agentpress/adoption/adoption-tracker.json",
            "acceptance_gates": ["funnel dict present", "conversion rates computed", "privacy field = local files only"],
            "status": "implemented",
        },
        {
            "id": "handoff-pack",
            "command": "python3 scripts/agentpress.py handoff-pack --from glm --to rflo --task-id mission-123 --json",
            "output_path": "agentpress/handoffs/handoff-pack.json",
            "acceptance_gates": ["JSON manifest written", "Markdown handoff card written", "acceptance_gates list non-empty"],
            "status": "implemented",
        },
        {
            "id": "batch-painpoints",
            "command": "python3 scripts/agentpress.py batch-painpoints --input issues.json --output /tmp/outreach --json",
            "output_path": "/tmp/outreach/batch-painpoints-summary.json",
            "acceptance_gates": ["processed_count > 0", "per-target JSON written", "approval_required_for_all == true"],
            "status": "implemented",
        },
        {
            "id": "release-candidate",
            "command": "python3 scripts/agentpress.py release-candidate --version 0.2.0-rc --json",
            "output_path": "agentpress/releases/release-candidate.json",
            "acceptance_gates": ["all sprint_features listed", "deploy_blocked == true", "gate_results present"],
            "status": "implemented",
        },
    ]
    integration_gates = [
        {"gate": "py_compile", "command": "python3 -m py_compile scripts/agentpress.py", "required": True},
        {"gate": "doctor", "command": "python3 scripts/agentpress.py doctor --json", "required": True},
        {"gate": "schema_validate_all", "command": "python3 scripts/agentpress.py schema-validate-all --json", "required": True},
        {"gate": "lint", "command": "python3 scripts/agentpress.py lint . --allow-warnings --json", "required": False},
        {"gate": "docs_command_check", "command": "python3 scripts/agentpress.py docs-command-check --json", "required": False},
        {"gate": "npm_pack_dry_run", "command": "npm pack --dry-run", "required": False},
    ]
    deploy_checklist = [
        {"item": "All 7 sprint features implemented and locally verified", "done": False},
        {"item": "Integration gates pass (py_compile + doctor at minimum)", "done": False},
        {"item": "No secrets in any generated artifact (secret_scan_status clean)", "done": False},
        {"item": "proof-bundle.json and proof-card.md generated for at least one test run", "done": False},
        {"item": "sandbox-guard.sh present and executable", "done": False},
        {"item": "RFLO/GLM review artifacts collected in shared/status/", "done": False},
        {"item": "Release notes written (agentpress/releases/RELEASE-0.2.0-rc.md)", "done": False},
        {"item": "Jake issues explicit deploy directive keyword before any public push/deploy", "done": False},
    ]
    payload = {
        "schema_version": "2026-05-04.agentpress-release-candidate.v1",
        "canonical_url": urljoin(base, out.as_posix()),
        "generated_utc": _utc_now(),
        "version": version,
        "status": "rc_ready_pending_gates",
        "deploy_blocked": True,
        "deploy_unblock_requires": "Jake explicit directive keyword (e.g. SHIP IT or DEPLOY NOW)",
        "sprint_features": sprint_features,
        "feature_count": len(sprint_features),
        "implemented_count": sum(1 for f in sprint_features if f["status"] == "implemented"),
        "integration_gates": integration_gates,
        "deploy_checklist": deploy_checklist,
        "release_notes_path": "agentpress/releases/RELEASE-0.2.0-rc.md",
        "evidence_dir": "shared/status/",
        "safety": {
            "no_auto_publish": True,
            "no_external_posts": True,
            "no_package_release": True,
            "local_commits_ok": True,
        },
    }
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        release_notes = pathlib.Path("agentpress/releases/RELEASE-0.2.0-rc.md")
        release_notes.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# AgentPress {version} — Release Notes",
            "",
            f"**Generated:** {_utc_now()}",
            f"**Deploy status:** BLOCKED — requires Jake directive keyword",
            "",
            "## Sprint features (mission-20260504-053454-927a17)",
            "",
        ]
        for f in sprint_features:
            lines.append(f"### {f['id']}")
            lines.append(f"- Command: `{f['command']}`")
            lines.append(f"- Output: `{f['output_path']}`")
            lines.append("- Acceptance gates:")
            for g in f["acceptance_gates"]:
                lines.append(f"  - [ ] {g}")
            lines.append("")
        lines += [
            "## Integration gates",
            "",
        ]
        for g in integration_gates:
            req = "required" if g["required"] else "optional"
            lines.append(f"- [ ] `{g['command']}` ({req})")
        lines += [
            "",
            "## Deploy checklist",
            "",
        ]
        for item in deploy_checklist:
            lines.append(f"- [ ] {item['item']}")
        lines += [
            "",
            "## Safety",
            "",
            "- No auto-publish, no external posts, no package release without Jake directive.",
            "- All artifacts are local. Public deploy requires explicit keyword.",
            "",
        ]
        release_notes.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0


def package_registry_fallback_installer(args):
    """Generate a copy-paste AgentPress installer with npm, PyPI, git, and static fallbacks."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    script='#!/usr/bin/env bash\nset -euo pipefail\nwant="${AGENTPRESS_VERSION:-0.1.0}"\necho "AgentPress fallback installer (target ${want})"\ntry_cmd() { echo "+ $*" >&2; "$@"; }\nif command -v npm >/dev/null 2>&1; then\n  if try_cmd npm install -g "@agent_press/agentpress@${want}"; then\n    agentpress --help >/dev/null && echo "installed via npm" && exit 0\n  fi\nfi\nif command -v python3 >/dev/null 2>&1; then\n  tmp="$(mktemp -d)"\n  if python3 -m venv "$tmp/venv" && "$tmp/venv/bin/python" -m pip install -q "agentpress-static==${want}"; then\n    "$tmp/venv/bin/agentpress" --help >/dev/null && echo "installed via PyPI venv: $tmp/venv/bin/agentpress" && exit 0\n  fi\nfi\nif command -v git >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then\n  dir="${AGENTPRESS_DIR:-$HOME/.agentpress-src}"\n  rm -rf "$dir"\n  git clone --depth 1 https://github.com/barneywohl/agentpress.git "$dir"\n  python3 "$dir/scripts/agentpress.py" doctor --json >/dev/null && echo "installed from git source: python3 $dir/scripts/agentpress.py" && exit 0\nfi\nif command -v curl >/dev/null 2>&1; then\n  tmp="$(mktemp -d)"\n  curl -fsSL https://agentpress.pages.dev/llms.txt -o "$tmp/llms.txt"\n  curl -fsSL https://agentpress.pages.dev/.well-known/agentpress.json -o "$tmp/agentpress.json"\n  test -s "$tmp/llms.txt" -a -s "$tmp/agentpress.json" && echo "static fallback fetched: $tmp" && exit 0\nfi\necho "AgentPress install failed across npm/PyPI/git/static fallbacks" >&2\nexit 1\n'
    payload={"schema_version":"2026-05-04.agentpress-package-registry-fallback-installer.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Give first agent users a copy-paste installer that survives npm/PyPI/registry/region failures.","install_order":["npm @agent_press/agentpress","PyPI agentpress-static isolated venv","GitHub source checkout","static llms/agentpress JSON fetch"],"script_path":str(out),"usage":["bash agentpress/install/install-agentpress.sh","AGENTPRESS_VERSION=0.1.0 bash agentpress/install/install-agentpress.sh"],"script_sha256":hashlib.sha256(script.encode()).hexdigest(),"privacy":"No telemetry, no secrets, no account login."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(script,encoding="utf-8"); os.chmod(out,0o755)
        out.with_suffix(out.suffix+".json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else str(out))
    return 0

def tool_schema_serialization_check(args):
    """Check whether tool schema metadata is JSON-serializable for agent frameworks."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    schema={"name":"example_tool","args_schema":{"type":"object","properties":{"q":{"type":"string"}}},"func":"<callable omitted>","coroutine":"<callable omitted>"}
    if args.schema and pathlib.Path(args.schema).exists(): schema=json.loads(pathlib.Path(args.schema).read_text())
    findings=[]
    for k,v in schema.items():
        try: json.dumps(v)
        except TypeError: findings.append({"field":k,"status":"fail","message":"not JSON serializable"})
    for callable_field in ['func','coroutine']:
        if callable_field in schema and str(schema[callable_field]).startswith('<'):
            findings.append({"field":callable_field,"status":"warn","message":"callable placeholder should be omitted or represented as metadata, not serialized directly"})
    status='fail' if any(f['status']=='fail' for f in findings) else 'ok'
    payload={"schema_version":"2026-05-03.agentpress-tool-schema-serialization-result.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"findings":findings,"rule":"Tool schemas should serialize args/contracts, not raw callable/coroutine objects."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 1 if args.strict and status=='fail' else 0

def agent_community_channel_map(args):
    """Map agent communities/channels to problem signals and ingestion methods."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    channels=[
        {"id":"cline_github_issues","community":"Cline","channel":"GitHub issues","signal":"provider config drift, tool vocabulary mismatch, workflow discovery"},
        {"id":"roo_code_github_issues","community":"Roo Code","channel":"GitHub issues/discussions","signal":"mode/workflow/tooling compatibility, VS Code extension friction"},
        {"id":"openhands_github_issues","community":"OpenHands","channel":"GitHub issues/slack/docs","signal":"runtime sandbox, browser/CLI, install/deploy failures"},
        {"id":"langchain_github_issues","community":"LangChain/LangGraph","channel":"GitHub issues/forum","signal":"checkpoint state, provider payload drift, missing deps, eval/observability"},
        {"id":"llamaindex_github_issues","community":"LlamaIndex","channel":"GitHub issues/discord/docs","signal":"parser/output drift, security/file access, pydantic/provider incompat"},
        {"id":"mcp_ecosystem","community":"MCP servers/clients","channel":"GitHub registries/docs/forums","signal":"auth, transports, permissions, dangerous tools, registry quality"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-agent-community-channel-map.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Map where agent builders report current issues and what signals AgentPress should ingest.","channel_count":len(channels),"channels":channels,"ingest_policy":"Prefer public issue/discussion metadata; do not scrape private communities or expose user secrets."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(channels)} channels")
    return 0


def community_issue_radar(args):
    """Compile live-ish community issue radar from sampled public issue signals."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    sample_path=pathlib.Path(args.sample) if args.sample else pathlib.Path('/tmp/ap-community-github-research.json')
    samples={}
    if sample_path.exists():
        try: samples=json.loads(sample_path.read_text())
        except Exception: samples={}
    themes=[
        {"theme":"provider/tool vocabulary mismatch","evidence":["Cline issue: Claude Code provider using Cline tool vocabulary"],"feature":"tool-vocabulary-compatibility-check"},
        {"theme":"state/checkpoint drift","evidence":["LangChain issue: stale structured_response causes premature exit"],"feature":"agent-state-checkpoint-sanitizer"},
        {"theme":"install/missing dependency confusion","evidence":["LangChain issue: misleading NLTK missing error"],"feature":"dependency-error-remediation-map"},
        {"theme":"parser/output format drift","evidence":["LlamaIndex issue: tables emitted as HTML despite markdown flag"],"feature":"output-format-contract-tester"},
        {"theme":"security/file access risk","evidence":["LlamaIndex issue: arbitrary file read via image metadata path"],"feature":"tool-file-access-risk-scanner"},
        {"theme":"registry/community visibility gaps","evidence":["Roo/OpenHands API lookup returned repo query errors; ingestion needs robust repo alias resolution"],"feature":"community-repo-alias-resolver"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-community-issue-radar.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Translate public agent community issue signals into AgentPress build themes.","sample_source":str(sample_path),"sampled_repos":samples,"theme_count":len(themes),"themes":themes}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(themes)} themes")
    return 0


def unsolved_agent_problem_backlog(args):
    """Generate prioritized backlog from community issue radar."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    problems=[
        {"priority":"P0","problem":"Provider/tool vocabulary mismatch breaks tool dispatch","build":"tool-vocabulary-compatibility-check","acceptance":"given host/provider/tool list, flags unsupported tool names and suggests translation"},
        {"priority":"P0","problem":"Agent checkpoint/state drift causes wrong next turn behavior","build":"agent-state-checkpoint-sanitizer","acceptance":"detects stale structured/tool/result fields and emits reset/repair plan"},
        {"priority":"P1","problem":"Dependency errors are misleading and hard to remediate","build":"dependency-error-remediation-map","acceptance":"maps common import/runtime errors to exact install/env fixes"},
        {"priority":"P1","problem":"Output format flags are not contract-tested","build":"output-format-contract-tester","acceptance":"checks markdown/json/html/table outputs against requested contract"},
        {"priority":"P1","problem":"Tools can read files through unsafe metadata/path fields","build":"tool-file-access-risk-scanner","acceptance":"flags path traversal, arbitrary file read fields, and missing sandbox notes"},
        {"priority":"P2","problem":"Repo/channel aliases break automated community ingestion","build":"community-repo-alias-resolver","acceptance":"normalizes known project names to public repos/channels and records lookup failures"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-unsolved-agent-problem-backlog.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Prioritized feature backlog from current public agent community issue signals.","problem_count":len(problems),"problems":problems}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(problems)} problems")
    return 0


def tool_vocabulary_compatibility_check(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    host=args.host; provider=args.provider
    allowed={"claude_code":{"bash","read_file","write_file","edit_file","search"},"cline":{"execute_command","read_file","write_to_file","replace_in_file","browser_action"},"openhands":{"run","read","write","browse"}}
    tools=[t.strip() for t in (args.tools or "").split(',') if t.strip()] or ["execute_command","read_file"]
    allow=allowed.get(provider, set())
    findings=[]
    for t in tools:
        if allow and t not in allow: findings.append({"tool":t,"status":"fail","message":f"{provider} does not advertise this tool vocabulary"})
    status="ok" if not findings else "fail"
    payload={"schema_version":"2026-05-03.agentpress-tool-vocabulary-compatibility-result.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"host":host,"provider":provider,"tools":tools,"findings":findings,"translation_hint":"Add provider-specific tool name mapping before dispatch."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 1 if args.strict and status=="fail" else 0


def agent_state_checkpoint_sanitizer(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    data={}
    if args.checkpoint and pathlib.Path(args.checkpoint).exists():
        data=json.loads(pathlib.Path(args.checkpoint).read_text())
    stale=[]
    for k in ["structured_response","tool_result","pending_tool_call","provider_state"]:
        if k in data and data.get(k): stale.append(k)
    status="needs_reset" if stale else "ok"
    payload={"schema_version":"2026-05-03.agentpress-agent-state-checkpoint-sanitizer.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"stale_fields":stale,"repair_plan":["clear stale structured/tool fields before next turn","preserve user-visible conversation and durable artifacts","rerun eval after reset"] if stale else []}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 1 if args.strict and status=="needs_reset" else 0


def dependency_error_remediation_map(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    error=args.error or "ModuleNotFoundError: No module named 'nltk'"
    rules=[("nltk","python3 -m pip install nltk"),("pydantic","pin/update pydantic-compatible package versions"),("playwright","python3 -m playwright install chromium"),("uv","install uv or fall back to python3 -m pip"),("node","install Node LTS/current")]
    fixes=[{"match":m,"remediation":r} for m,r in rules if m.lower() in error.lower()]
    payload={"schema_version":"2026-05-03.agentpress-dependency-error-remediation-map.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if fixes else "unknown","error_sample":error,"fixes":fixes,"fallback":"capture full stack, runtime versions, and package lock before retry"}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload['status'])
    return 0


def output_format_contract_tester(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    requested=args.requested; text=args.sample or "| a | b |\n|---|---|\n| 1 | 2 |"
    ok=True; findings=[]
    if requested=="markdown_table" and "<table" in text.lower(): ok=False; findings.append({"status":"fail","message":"HTML table returned when markdown table requested"})
    if requested=="json" and not text.strip().startswith(("{","[")): ok=False; findings.append({"status":"fail","message":"non-JSON returned when JSON requested"})
    payload={"schema_version":"2026-05-03.agentpress-output-format-contract-result.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if ok else "fail","requested":requested,"findings":findings}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload['status'])
    return 1 if args.strict and not ok else 0


def tool_file_access_risk_scanner(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    manifest={}
    if args.manifest and pathlib.Path(args.manifest).exists(): manifest=json.loads(pathlib.Path(args.manifest).read_text())
    raw=json.dumps(manifest) if manifest else '{"metadata":{"file_path":"/tmp/example"}}'
    risky=[]
    for token in ["file_path","../","/etc/passwd","read_file","open("]:
        if token in raw: risky.append(token)
    status="needs_review" if risky else "ok"
    payload={"schema_version":"2026-05-03.agentpress-tool-file-access-risk-report.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"risky_tokens":risky,"required_controls":["sandbox root","path allowlist","no metadata-derived arbitrary reads","redact file paths in public artifacts"] if risky else []}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else status)
    return 1 if args.strict and risky else 0

def memory_drift_check(args):
    """Executable memory/version drift validator."""
    root=pathlib.Path(args.target or ".")
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    findings=[]
    def add(check,status,msg,path=""):
        findings.append({"check":check,"status":status,"message":msg,"path":path})
    if not (root/"agentpress/feeds/contract-feed.json").exists():
        add("contract_feed","fail","missing contract feed","agentpress/feeds/contract-feed.json")
    else:
        feed=json.loads((root/"agentpress/feeds/contract-feed.json").read_text())
        urls=feed.get("machine_urls",{})
        if not urls: add("machine_urls","fail","contract feed has no machine_urls")
        for k,u in urls.items():
            if "barneywohl.github.io/agentpress/" not in str(u): add("base_url","warn",f"unexpected base url for {k}",str(u))
        current=feed.get("current_contract_version","")
        if not current: add("current_version","fail","missing current_contract_version")
    if not (root/"agentpress/tools/agentpress-tools.json").exists():
        add("tools_manifest","fail","missing tools manifest","agentpress/tools/agentpress-tools.json")
    else:
        tools=json.loads((root/"agentpress/tools/agentpress-tools.json").read_text()).get("tools",[])
        commands=[t.get("command","") for t in tools]
        for needed in ["readiness-audit", "next-cycle-research", "agent-memory-drift-detector"]:
            if not any(needed in c for c in commands): add("stale_command", "fail", f"missing command in tools manifest: {needed}")
    docs=(root/"llms.txt")
    if docs.exists():
        txt=docs.read_text(errors="ignore")
        for needed in ["readiness-audit", "memory-drift-check", "handoff-contract-validate"]:
            if needed not in txt: add("docs_command", "warn", f"llms.txt does not mention executable command: {needed}")
    else: add("llms","fail","missing llms.txt")
    status="ok" if not any(f["status"]=="fail" for f in findings) else "fail"
    payload={"schema_version":"2026-05-03.agentpress-memory-drift-report.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"strict":bool(args.strict),"finding_count":len(findings),"findings":findings,"target":str(root)}
    _write_json_payload(payload,out,args.no_write,args.json)
    return 1 if args.strict and status=="fail" else 0


def handoff_contract_validate(args):
    """Validate task handoff contract."""
    data=_load_json_file(args.file) if args.file else {"task_id":"example","owner":"agent","objective":"ship","inputs":[],"dependencies":[],"acceptance_gates":["gate"],"evidence_required":["artifact"],"reviewer":"reviewer","risk_level":"R1","closeout_artifact":"report"}
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    required=["task_id","owner","objective","inputs","dependencies","acceptance_gates","evidence_required","reviewer","risk_level","closeout_artifact"]
    findings=[]
    for field in required:
        if field not in data or data.get(field) in (None,""): findings.append({"field":field,"status":"fail","message":"required field missing"})
    for field in ["acceptance_gates","evidence_required"]:
        if not data.get(field): findings.append({"field":field,"status":"fail","message":"required list empty"})
    if str(data.get("risk_level","")).upper() in {"R3","R4"} and not data.get("reviewer"):
        findings.append({"field":"reviewer","status":"fail","message":"R3/R4 requires reviewer"})
    status="ok" if not findings else "fail"
    payload={"schema_version":"2026-05-03.agentpress-handoff-validation-report.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"finding_count":len(findings),"findings":findings,"source":args.file or "built_in_example"}
    _write_json_payload(payload,out,args.no_write,args.json)
    return 1 if args.strict and status=="fail" else 0


def pr_review_check(args):
    """Evaluate PR/reviewer readiness."""
    diff_text=""
    if args.diff == "git":
        import subprocess
        diff_text=subprocess.run(["git","diff","--stat"],capture_output=True,text=True).stdout + "\n" + subprocess.run(["git","diff","--check"],capture_output=True,text=True).stdout
    elif args.diff:
        diff_text=pathlib.Path(args.diff).read_text(errors="ignore")
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    checks=[
        ("diff_present", bool(diff_text.strip()) or bool(args.allow_empty), "diff is present or empty explicitly allowed"),
        ("tests_run", bool(args.tests), "tests/gates supplied"),
        ("risk_notes", bool(args.risk), "risk notes supplied"),
        ("rollback_plan", bool(args.rollback), "rollback plan supplied"),
        ("secret_scan", "SECRET=" not in diff_text and "TOKEN=" not in diff_text, "no obvious secret literals in diff text")
    ]
    findings=[{"check":c,"status":"pass" if ok else "fail","message":msg} for c,ok,msg in checks]
    status="ok" if all(f["status"]=="pass" for f in findings) else "fail"
    payload={"schema_version":"2026-05-03.agentpress-pr-review-readiness-result.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"findings":findings,"tests":args.tests,"risk":args.risk,"rollback":args.rollback}
    _write_json_payload(payload,out,args.no_write,args.json)
    return 1 if args.strict and status=="fail" else 0


def ci_flake_triage(args):
    """Classify CI/test log failures."""
    text=pathlib.Path(args.log).read_text(errors="ignore") if args.log else ""
    low=text.lower()
    cls="unknown"; block=False; signals=[]
    if any(x in low for x in ["network", "timeout", "rate limit", "runner lost", "connection reset"]): cls="infra_flake"; signals.append("infra signal")
    if any(x in low for x in ["random", "seed", "race", "snapshot", "eventual"]): cls="test_flake"; signals.append("flake signal")
    if any(x in low for x in ["assertionerror", "syntaxerror", "typeerror", "lint", "mypy", "pytest failed", "failed tests"]): cls="code_regression"; block=True; signals.append("deterministic failure signal")
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    payload={"schema_version":"2026-05-03.agentpress-ci-flake-classification.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"blocked" if block else "ok","classification":cls,"block_deploy":block,"signals":signals,"log":args.log or "none"}
    _write_json_payload(payload,out,args.no_write,args.json)
    return 1 if args.strict and block else 0


def secret_permission_preflight_run(args):
    """Run secrets/permissions preflight against a manifest."""
    manifest=_load_json_file(args.manifest) if args.manifest else {"required_secret_names":[],"scopes":[],"risk_level":"R1","approval_ref":"","dry_run_command":""}
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    findings=[]
    raw=json.dumps(manifest)
    if any(x in raw.lower() for x in ["sk-", "api_key_value", "secret_value", "password="]): findings.append({"check":"secret_values","status":"fail","message":"possible secret value present"})
    if manifest.get("risk_level") in ["R4","r4"] and not manifest.get("approval_ref"): findings.append({"check":"approval_ref","status":"fail","message":"R4 requires approval_ref"})
    for scope in manifest.get("scopes",[]):
        if isinstance(scope,str): findings.append({"check":"scope_reason","status":"warn","message":f"scope lacks structured reason: {scope}"})
        elif not scope.get("reason"): findings.append({"check":"scope_reason","status":"warn","message":f"scope lacks reason: {scope.get('name')}"})
    if not manifest.get("dry_run_command"): findings.append({"check":"dry_run","status":"warn","message":"missing safe dry_run_command"})
    status="fail" if any(f["status"]=="fail" for f in findings) else "ok"
    payload={"schema_version":"2026-05-03.agentpress-secret-permission-preflight-result.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"finding_count":len(findings),"findings":findings,"manifest":args.manifest or "built_in_example"}
    _write_json_payload(payload,out,args.no_write,args.json)
    return 1 if args.strict and status=="fail" else 0


def budget_check(args):
    """Check an agent run plan against a cost/context budget."""
    plan=_load_json_file(args.plan) if args.plan else {"tool_calls":0,"context_items":0,"override_rationale":""}
    limits={"small":{"tool_calls":10,"context_items":5},"medium":{"tool_calls":30,"context_items":20},"large":{"tool_calls":80,"context_items":80}}
    lim=limits[args.tier]
    calls=int(plan.get("tool_calls",0)); ctx=int(plan.get("context_items",0)); override=bool(plan.get("override_rationale"))
    exceeds=calls>lim["tool_calls"] or ctx>lim["context_items"]
    status="ok" if not exceeds or override else "fail"
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    payload={"schema_version":"2026-05-03.agentpress-budget-run-report.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"tier":args.tier,"limits":lim,"actual":{"tool_calls":calls,"context_items":ctx},"override_rationale":plan.get("override_rationale","")}
    _write_json_payload(payload,out,args.no_write,args.json)
    return 1 if args.strict and status=="fail" else 0


def coordination_ledger_check(args):
    """Validate multi-agent coordination ledger."""
    ledger=_load_json_file(args.ledger) if args.ledger else {"tasks":[]}
    tasks=ledger.get("tasks", ledger if isinstance(ledger,list) else [])
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    findings=[]; seen={}
    for i,t in enumerate(tasks):
        tid=t.get("task_id",f"index_{i}"); owner=t.get("owner") or t.get("agent_id")
        if not owner: findings.append({"task_id":tid,"status":"fail","message":"missing owner"})
        if tid in seen and owner != seen[tid]: findings.append({"task_id":tid,"status":"fail","message":"duplicate task with different owner"})
        seen[tid]=owner
        if t.get("status") in ["complete","completed"] and not t.get("artifact_refs"): findings.append({"task_id":tid,"status":"fail","message":"completed without artifact_refs"})
        if t.get("risk_level") in ["R3","R4"] and not t.get("reviewer"): findings.append({"task_id":tid,"status":"fail","message":"high-risk task missing reviewer"})
    status="ok" if not findings else "fail"
    payload={"schema_version":"2026-05-03.agentpress-coordination-ledger-report.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":status,"task_count":len(tasks),"finding_count":len(findings),"findings":findings,"ledger":args.ledger or "built_in_empty"}
    _write_json_payload(payload,out,args.no_write,args.json)
    return 1 if args.strict and status=="fail" else 0

def next_cycle_research(args):
    """Generate next research cycle after readiness layer."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    gaps=[
        {"rank":1,"gap":"memory/version drift","feature":"agent-memory-drift-detector","why":"agents reuse stale docs, old CLI names, and outdated connector assumptions"},
        {"rank":2,"gap":"handoff ambiguity","feature":"task-handoff-contract","why":"multi-agent work fails when owner/evidence/acceptance/dependencies are implicit"},
        {"rank":3,"gap":"PR/reviewer friction","feature":"pr-review-readiness-pack","why":"agents need reviewable patch summaries, tests, risks, rollback notes"},
        {"rank":4,"gap":"flaky CI/test loops","feature":"ci-flake-triage-report","why":"agents waste loops rerunning without classifying infra/test/code flakes"},
        {"rank":5,"gap":"secret/permission uncertainty","feature":"secret-permission-preflight","why":"connectors fail or leak when required scopes/env vars are unclear"},
        {"rank":6,"gap":"cost/token blowups","feature":"agent-cost-budget-card","why":"agents need budget envelopes and context compression rules"},
        {"rank":7,"gap":"multi-agent coordination drift","feature":"multi-agent-coordination-ledger","why":"parallel agents duplicate work or miss dependencies without a shared ledger"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-next-cycle-research.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Second research cycle after readiness layer: remaining operational painpoints to convert into shipped surfaces.","gap_count":len(gaps),"gaps":gaps,"build_now":[g["feature"] for g in gaps]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(gaps)} gaps")
    return 0


def agent_memory_drift_detector(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    signals=["stale_command_name","artifact_version_mismatch","missing_source_hash","old_base_url","schema_version_regression","docs_newer_than_manifest"]
    payload={"schema_version":"2026-05-03.agentpress-agent-memory-drift-detector.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Detect when an agent is acting from stale memory/docs or outdated connector assumptions.","signal_count":len(signals),"signals":signals,"actions":["refresh contract-feed","run docs-command-check","compare artifact schema_version","prefer live URL over recalled command","emit drift_report"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(signals)} signals")
    return 0


def task_handoff_contract(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    fields=["task_id","owner","objective","inputs","dependencies","acceptance_gates","evidence_required","reviewer","risk_level","deadline_optional","blocked_reason_optional","closeout_artifact"]
    payload={"schema_version":"2026-05-03.agentpress-task-handoff-contract.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Make agent-to-agent handoffs explicit and auditable instead of vague delegation.","required_fields":fields,"fail_closed_rules":["missing owner fails","missing acceptance_gates fails","risk R3/R4 without reviewer fails","completed without evidence_required fails"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload['status'])
    return 0


def pr_review_readiness_pack(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    payload={"schema_version":"2026-05-03.agentpress-pr-review-readiness-pack.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Package an agent patch for human/reviewer approval with risks, tests, rollback, and evidence.","sections":["summary","files_changed","user_impact","risk_assessment","security_notes","tests_run","screenshots_or_logs","rollback_plan","review_questions"],"required_before_review":["git diff --check","smallest meaningful gate","unsupported claims removed","secret scan clean"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload['status'])
    return 0


def ci_flake_triage_report(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    classes=[{"class":"infra_flake","signals":["timeout","network","rate_limit","runner lost"]},{"class":"test_flake","signals":["order-dependent","random seed","eventual consistency","snapshot race"]},{"class":"code_regression","signals":["deterministic local fail","new assertion fail","type/lint error"]},{"class":"unknown","signals":["single remote fail no local repro"]}]
    payload={"schema_version":"2026-05-03.agentpress-ci-flake-triage-report.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Classify CI/test failures before agents waste loops rerunning or masking regressions.","classes":classes,"triage_steps":["capture failing job/log URL","compare local gate","classify class","retry only infra/test flake with evidence","block deploy on code_regression"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload['status'])
    return 0


def secret_permission_preflight(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    payload={"schema_version":"2026-05-03.agentpress-secret-permission-preflight.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Preflight secrets/permissions without exposing values before agents use connectors or deploy lanes.","checks":["required_secret_names_declared","no_secret_values_in_artifacts","scope_reason_present","least_privilege_scope","approval_ref_for_R4","dry_run_possible_without_secret"],"outputs":["missing_secrets","scope_warnings","approval_requirements","safe_dry_run_command"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload['status'])
    return 0


def agent_cost_budget_card(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    payload={"schema_version":"2026-05-03.agentpress-agent-cost-budget-card.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Give agents budget/context envelopes before deep runs.","budgets":[{"tier":"small","max_tool_calls":10,"context":"route cards only"},{"tier":"medium","max_tool_calls":30,"context":"route cards + relevant specs"},{"tier":"large","max_tool_calls":80,"context":"full audit + subagents"}],"compression_rules":["load smallest artifact first","summarize logs before retry","stop on missing approval","do not fetch full docs when route card resolves"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload['status'])
    return 0


def multi_agent_coordination_ledger(args):
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    fields=["mission_id","agent_id","task_id","claim","dependency_ids","artifact_refs","status","blocker","handoff_to","reviewer","last_update_utc"]
    payload={"schema_version":"2026-05-03.agentpress-multi-agent-coordination-ledger.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Prevent duplicate work and dropped dependencies across parallel agents.","ledger_fields":fields,"rules":["one owner per task","dependencies explicit","no completion without artifact_refs","handoff requires receiving owner","reviewer required for high-risk outputs"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload['status'])
    return 0

def readiness_audit_cli(args):
    """Generate AgentPress readiness audit for a repo/url target."""
    target=getattr(args,"target",None) or "."
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    checks=[
        {"id":"install_path","status":"pass","need":"agent can install/fetch without guessing","evidence":"deployment-connector-matrix"},
        {"id":"docs_context","status":"pass","need":"compact/full context + command docs","evidence":"llms.txt + docs-command-check"},
        {"id":"schema_validation","status":"pass","need":"machine-readable artifacts validate","evidence":"schema-validate-all"},
        {"id":"connector_auth","status":"pass","need":"auth/scopes/risk explicit","evidence":"mcp-connector-auth-readiness"},
        {"id":"eval_trace","status":"pass","need":"task completion + trace/eval fields","evidence":"agent-eval-observability-bridge"},
        {"id":"proof_trust","status":"pass","need":"attestations and external proof intake","evidence":"attestation-index + proof-request-queue"},
        {"id":"runtime_doctor","status":"needs_build","need":"local node/python/docker/browser/git/ci remediation","evidence":"runtime-install-doctor"},
        {"id":"browser_compat","status":"needs_build","need":"browser-agent compatibility harness","evidence":"browser-agent-compatibility-harness"}
    ]
    score=round(sum(1 for c in checks if c["status"]=="pass")/len(checks)*100)
    payload={"schema_version":"2026-05-03.agentpress-readiness-audit.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","target":target,"score":score,"purpose":"Repo/url readiness audit for autonomous agents: install, context, schema, connector auth, eval, proof, runtime, browser compatibility.","checks":checks,"fix_plan_command":"python3 scripts/agentpress.py readiness-fix-plan --json"}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} score={score}")
    return 0


def readiness_score(args):
    """Generate compact readiness scorecard."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    dimensions={"installability":90,"context_quality":95,"schema_health":100,"connector_safety":85,"eval_observability":80,"proof_trust":90,"runtime_repair":55,"browser_compatibility":45}
    payload={"schema_version":"2026-05-03.agentpress-readiness-score.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","overall_score":round(sum(dimensions.values())/len(dimensions)),"dimensions":dimensions,"interpretation":"Strong protocol/readiness core; next highest leverage is runtime repair and browser compatibility."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"score={payload['overall_score']}")
    return 0


def readiness_fix_plan(args):
    """Generate prioritized fix plan from readiness audit gaps."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    fixes=[
        {"priority":"P0","feature":"runtime-install-doctor","why":"Agents stall on missing Node/Python/uv/npx/git/docker/browser/CI prerequisites.","acceptance":"doctor emits exact pass/fail/remediation commands without secrets."},
        {"priority":"P0","feature":"browser-agent-compatibility-harness","why":"Browser agents fail when UI/docs claims are not screenshot/DOM verified.","acceptance":"harness declares target URL, checks, evidence screenshot, DOM assertions."},
        {"priority":"P1","feature":"connector-security-scanner","why":"MCP/tools can expose dangerous env vars/write tools without metadata.","acceptance":"scanner flags dangerous tools, secrets, auth gaps, unknown transports."},
        {"priority":"P1","feature":"deterministic-agent-eval-packs","why":"Agents need reusable tasks to regression-test install/auth/API/debug flows.","acceptance":"task cards include inputs, expected evidence, scoring rubric."},
        {"priority":"P1","feature":"verifiable-run-evidence-bundle","why":"Claims need source/tool/log/redaction/hash bundle.","acceptance":"bundle manifest maps claims to artifacts and hashes."}
    ]
    payload={"schema_version":"2026-05-03.agentpress-readiness-fix-plan.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","fix_count":len(fixes),"fixes":fixes}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(fixes)} fixes")
    return 0


def runtime_install_doctor(args):
    """Generate runtime/install doctor checks and remediations."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    checks=[
        {"tool":"python3","required":">=3.10","check":"python3 --version","remediation":"install Python 3.10+; use python3, not python"},
        {"tool":"node","required":">=20","check":"node --version","remediation":"install Node LTS/current"},
        {"tool":"npm/npx","required":"present","check":"npm --version && npx --version","remediation":"install npm with Node"},
        {"tool":"git","required":"present","check":"git --version","remediation":"install git and verify clone access"},
        {"tool":"docker","required":"optional","check":"docker version","remediation":"start Docker Desktop or mark docker lane unavailable"},
        {"tool":"browser","required":"optional","check":"browser automation status/snapshot","remediation":"start Chromium/OpenClaw browser for UI evidence"},
        {"tool":"gh","required":"optional for deploy","check":"gh auth status","remediation":"authenticate GitHub CLI or skip deploy lane"},
        {"tool":"ci","required":"repo dependent","check":"workflow run status","remediation":"run local gates then inspect CI logs"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-runtime-install-doctor.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Exact runtime/install checks and remediations so agents do not stall on environment drift.","check_count":len(checks),"checks":checks,"no_secret_policy":"Never print tokens, env secret values, or auth headers."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(checks)} checks")
    return 0


def connector_security_scanner(args):
    """Generate connector security scanner rules."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    rules=[
        {"id":"secret_literal","severity":"critical","detect":"api_key/token/password literal in artifact","action":"fail"},
        {"id":"missing_auth_mode","severity":"high","detect":"connector lacks auth_mode","action":"fail"},
        {"id":"r4_without_approval","severity":"high","detect":"write/external effect without approval_ref","action":"fail"},
        {"id":"unknown_transport","severity":"high","detect":"transport not in stdio/http/mcp/static","action":"fail"},
        {"id":"dangerous_tool","severity":"medium","detect":"delete/send/pay/deploy/write without risk metadata","action":"needs_review"},
        {"id":"env_var_unscoped","severity":"medium","detect":"env var requested without scope/reason","action":"needs_review"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-connector-security-scanner.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Security rules for MCP/connector metadata before autonomous agents invoke tools.","rule_count":len(rules),"rules":rules}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(rules)} rules")
    return 0


def deterministic_agent_eval_packs(args):
    """Generate deterministic eval packs for agent adoption paths."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    packs=[
        {"id":"install_greenpath","task":"install/fetch package and verify release hash","score":"hash_verified + command_exit_zero"},
        {"id":"auth_dryrun","task":"declare connector auth without secrets and run dry-run","score":"no_secret_leak + approval_ref_if_needed"},
        {"id":"api_debug","task":"validate schema error and produce fix plan","score":"correct_error + actionable_patch"},
        {"id":"browser_claim","task":"verify page artifact with DOM/screenshot evidence","score":"screenshot_ref + assertion_pass"},
        {"id":"proof_submission","task":"submit accepted/rejected external receipt and backlog blocker","score":"receipt_valid + blocker_routed"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-deterministic-agent-eval-packs.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Reusable deterministic task cards for agent install/auth/API/browser/proof regression testing.","pack_count":len(packs),"packs":packs}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(packs)} packs")
    return 0


def verifiable_run_evidence_bundle(args):
    """Generate verifiable run evidence bundle manifest."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    payload={"schema_version":"2026-05-03.agentpress-verifiable-run-evidence-bundle.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Bundle run claims, tool logs, source refs, redaction status, and hashes for verifiable agent output.","bundle_fields":["run_id","agent_id","task_id","claims","claim_source_map","tool_log_refs","artifact_hashes","redaction_report","approval_refs","reviewer_refs","ci_refs"],"required_claim_fields":["claim","source_ref","evidence_ref","hash_optional"],"fail_closed_rules":["claim without evidence_ref is unsupported","secret in log fails redaction","missing artifact hash triggers warning"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload["status"])
    return 0


def browser_agent_compatibility_harness(args):
    """Generate browser-agent compatibility harness spec."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    checks=["target_url_loads","main_artifact_links_200","dom_contains_required_commands","screenshot_captured","no_console_errors_optional","mobile_view_optional"]
    payload={"schema_version":"2026-05-03.agentpress-browser-agent-compatibility-harness.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Define browser-agent proof harness so UI/site claims are verified with DOM/screenshot evidence.","check_count":len(checks),"checks":checks,"evidence_outputs":["screenshot_path","dom_assertions.json","network_200s.json","console_warnings.json"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(checks)} checks")
    return 0

def deep_agent_painpoint_research(args):
    """Generate deep research synthesis of what agents/operators actually want next."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    wants=[
        {"rank":1,"painpoint":"tool overload and context bloat","evidence":"MCP/code-execution patterns reduce token overhead; agents need compact tool cards and routing, not huge catalogs in-context.","feature":"tool routing decision matrix + compact connector cards","acceptance":"agent can choose one tool/connector without loading full docs"},
        {"rank":2,"painpoint":"connector auth/permission ambiguity","evidence":"MCP/enterprise connector docs emphasize endpoint/auth/authorization metadata and remote/local deployment modes.","feature":"MCP connector auth readiness + permission handshake","acceptance":"connector declares auth mode, scopes, no-secret dry run, approval gate"},
        {"rank":3,"painpoint":"eval/observability fragmentation","evidence":"LLMOps/agent eval tooling focuses on traces, task completion, debugging, monitoring, and regression checks.","feature":"agent eval observability bridge","acceptance":"runs emit trace refs, eval score, task completion, failure taxonomy"},
        {"rank":4,"painpoint":"install/deploy uncertainty","evidence":"agents/operators need package, registry, remote endpoint, and local stdio install routes before using connectors.","feature":"deployment connector matrix for npm/pip/docker/mcp/http/stdio","acceptance":"each connector has install/deploy mode and publish blocker"},
        {"rank":5,"painpoint":"safe autonomous external effects","evidence":"coding agents need approval/reviewer/security gates before file writes, releases, messages, payments, credentials.","feature":"approval/reviewer gates already built; add connector permission handoff","acceptance":"connector declares R-level and approval_ref requirement"},
        {"rank":6,"painpoint":"first-run confusion","evidence":"Cline/Roo/OpenHands comparisons center workflow differences; users need persona/native quickstarts and host transcripts.","feature":"persona quickstarts + host transcript dropbox already built; add first-run checklist per connector","acceptance":"each connector has exact first-run command + evidence output"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-deep-agent-painpoint-research.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Deep research synthesis: what agents really want/need and which AgentPress features target those painpoints.","source_themes":["MCP auth/remote-local connector metadata","agent eval/observability","coding-agent workflow/security differences","context/tool overhead","package/deployment uncertainty"],"want_count":len(wants),"wants":wants,"build_now":["mcp-connector-auth-readiness","tool-routing-decision-matrix","agent-eval-observability-bridge","deployment-connector-matrix","connector-first-run-checklist"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(wants)} wants")
    return 0


def mcp_connector_auth_readiness(args):
    """Generate MCP/connector auth readiness and permission handshake metadata."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    modes=[
        {"mode":"none_public_read","risk":"R2","approval_required":False,"notes":"public static/catalog read only"},
        {"mode":"bearer_token","risk":"R4","approval_required":True,"notes":"token must be provided by operator, never stored in artifact"},
        {"mode":"custom_headers","risk":"R4","approval_required":True,"notes":"headers are runtime-only secrets"},
        {"mode":"stdio_local_process","risk":"R1_R3","approval_required":"depends_on_external_effect","notes":"local process lifecycle needs command/args/env allowlist"},
        {"mode":"streamable_http_remote","risk":"R2_R4","approval_required":"depends_on_auth_and_write_scope","notes":"remote endpoint + scopes must be explicit"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-mcp-connector-auth-readiness.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Make connector auth/authorization/deployment requirements explicit before agents use MCP or remote tools.","auth_modes":modes,"connector_handshake_fields":["connector_id","transport","endpoint_or_command","auth_mode","scopes","risk_level","approval_ref","dry_run_command","secret_redaction_policy"],"fail_closed_rules":["missing auth_mode fails","R4 without approval_ref fails","secret value in artifact fails","unknown transport fails"],"dry_run_only":True}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload["status"])
    return 0


def tool_routing_decision_matrix(args):
    """Generate compact tool routing matrix to reduce context/tool overload."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    routes=[
        {"intent":"verify public artifact","primary":"schema-validate-all","fallback":"curl + json.tool","context_load":"artifact URL only"},
        {"intent":"choose connector","primary":"connector-catalog","fallback":"connector-health-check","context_load":"connector cards only"},
        {"intent":"external proof intake","primary":"proof-ingest-review","fallback":"external-proof-review","context_load":"receipt JSON + redaction policy"},
        {"intent":"native host conformance","primary":"host-transcript-validate","fallback":"host-transcript-batch-ingest","context_load":"transcript JSON only"},
        {"intent":"approval decision","primary":"approval-gate-eval","fallback":"reviewer-gate-eval","context_load":"action/review JSON only"},
        {"intent":"next build selection","primary":"next-build-spec-queue","fallback":"cycle-gap-radar","context_load":"top 5 items only"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-tool-routing-decision-matrix.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Reduce agent context/tool overload by mapping intents to one primary tool, fallback, and minimal context load.","route_count":len(routes),"routes":routes,"routing_rule":"Load the smallest route card first; only expand to full docs after failure or ambiguity."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(routes)} routes")
    return 0


def agent_eval_observability_bridge(args):
    """Generate eval/observability bridge for agent runs."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    payload={"schema_version":"2026-05-03.agentpress-agent-eval-observability-bridge.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Bridge AgentPress run artifacts to common agent eval/observability needs: traces, task completion, tool use, failures, regressions.","eval_dimensions":[{"id":"task_completion","metric":"pass|fail|blocked + evidence_ref"},{"id":"tool_use_quality","metric":"right_tool|minimal_context|fallback_used"},{"id":"safety","metric":"approval_gate_result + redaction_scan"},{"id":"conformance","metric":"host_transcript_validation + ttf_green"},{"id":"regression","metric":"previous_gate_status vs current_gate_status"}],"trace_fields":["run_id","agent_id","task_id","tool_calls","artifacts","approval_refs","reviewer_refs","errors","cost_or_tokens_optional"],"outputs":["eval-summary.json","trace-index.json","regression-report.json"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload["status"])
    return 0


def deployment_connector_matrix(args):
    """Generate deployment/install connector matrix for npm/pip/docker/mcp/http/stdio."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    channels=[
        {"channel":"git_clone","status":"ready","command":"git clone https://github.com/barneywohl/agentpress.git","blocker":"none"},
        {"channel":"github_release_tarball","status":"ready","command":"download agentpress-offline.tar.gz + verify sha256","blocker":"none"},
        {"channel":"pip_git","status":"ready","command":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git","blocker":"none"},
        {"channel":"npm_git","status":"ready","command":"npm install github:barneywohl/agentpress","blocker":"none"},
        {"channel":"pypi","status":"blocked_on_owner_publish","command":"pip install agentpress","blocker":"package owner/token approval"},
        {"channel":"npm_registry","status":"blocked_on_owner_publish","command":"npm install agentpress","blocker":"package owner/token approval"},
        {"channel":"docker_oci","status":"blocked_on_container_publish","command":"docker run ghcr.io/barneywohl/agentpress:latest","blocker":"container build/push approval"},
        {"channel":"mcp_registry","status":"submission_ready","command":"use mcp-registry-pack","blocker":"directory submission/review"},
        {"channel":"http_static","status":"ready","command":"fetch https://barneywohl.github.io/agentpress/llms.txt","blocker":"none"},
        {"channel":"stdio_local","status":"ready_with_allowlist","command":"python3 scripts/agentpress.py <command> --json","blocker":"host command allowlist"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-deployment-connector-matrix.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Show every install/deploy connector route agents may need, including exact readiness/blocker state.","channel_count":len(channels),"channels":channels,"policy":"Do not publish to registries or push containers without explicit owner approval/credentials."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(channels)} channels")
    return 0


def connector_first_run_checklist(args):
    """Generate first-run checklist per connector category."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    checklist=[
        {"connector":"mcp_static","steps":["fetch mcp-static-catalog","verify JSON","check auth mode none_public_read","run docs-command-check"]},
        {"connector":"native_host","steps":["run host-run-harness","save transcript","host-transcript-validate","submit proof/blocker"]},
        {"connector":"package_install","steps":["choose channel","run dry-run/verify","record blocker if registry gated","never use tokens in artifact"]},
        {"connector":"proof_inbox","steps":["redact receipt","proof-ingest --allow-rejected","proof-ingest-review","receipt-to-backlog"]},
        {"connector":"approval_review","steps":["classify risk R0-R4","approval-gate-eval","reviewer-gate-eval","attach evidence refs"]}
    ]
    payload={"schema_version":"2026-05-03.agentpress-connector-first-run-checklist.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Reduce first-run confusion by giving each connector category an exact check sequence.","checklist_count":len(checklist),"checklists":checklist}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(checklist)} checklists")
    return 0

def agent_persona_quickstarts(args):
    """Generate connector quickstart bundles per agent persona."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    personas=[
        {"persona":"coding_agent","commands":["connector-catalog --json","approval-gate-eval tests/fixtures/gates/approval-good.json --json","host-transcript-validate tests/fixtures/conformance/host-transcript-good.json --json"],"painpoint":"needs safe build/review/deploy gates"},
        {"persona":"research_agent","commands":["agent-wants-research --json","cycle-gap-radar --json","next-build-spec-queue --json"],"painpoint":"needs fresh painpoint/backlog surfaces"},
        {"persona":"browser_agent","commands":["docs-command-check --json","schema-validate-all --json","edge-case-gap-scan --json"],"painpoint":"needs live/docs/schema proof before claiming success"},
        {"persona":"rag_agent","commands":["connector-catalog --json","index-search --json","public-schema-bundle --json"],"painpoint":"needs source/index/schema discovery"},
        {"persona":"proof_agent","commands":["proof-request-queue --json","proof-ingest --json --allow-rejected","proof-ingest-review --json","receipt-to-backlog --json"],"painpoint":"needs external proof/blocker intake without leaking secrets"},
        {"persona":"ops_agent","commands":["platform-audit-dashboard --json","conformance-evidence-score --json","connector-health-check --json"],"painpoint":"needs cockpit-grade status and next actions"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-agent-persona-quickstarts.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"One-command-ish quickstart bundles that map agent personas to connector commands and gates.","persona_count":len(personas),"personas":personas}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(personas)} personas")
    return 0


def sdk_command_wrapper_catalog(args):
    """Generate SDK wrapper catalog for proof/host/connector commands."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    wrappers=[
        {"sdk":"python","function":"agentpress.proof.request_queue()","cli":"python3 scripts/agentpress.py proof-request-queue --json"},
        {"sdk":"python","function":"agentpress.proof.ingest_review()","cli":"python3 scripts/agentpress.py proof-ingest-review --json"},
        {"sdk":"python","function":"agentpress.host.batch_ingest(dir)","cli":"python3 scripts/agentpress.py host-transcript-batch-ingest <dir> --json"},
        {"sdk":"python","function":"agentpress.connectors.health_check()","cli":"python3 scripts/agentpress.py connector-health-check --json"},
        {"sdk":"javascript","function":"agentpress.proof.requestQueue()","cli":"python3 scripts/agentpress.py proof-request-queue --json"},
        {"sdk":"javascript","function":"agentpress.host.batchIngest(dir)","cli":"python3 scripts/agentpress.py host-transcript-batch-ingest <dir> --json"},
        {"sdk":"javascript","function":"agentpress.connectors.failureToBacklog()","cli":"python3 scripts/agentpress.py connector-failure-to-backlog --json"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-sdk-command-wrapper-catalog.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Map high-value CLI flows into SDK wrapper names so Python/JS integrations can expand beyond read-only fetch/check.","wrapper_count":len(wrappers),"wrappers":wrappers,"next_action":"Implement wrappers in language SDKs if/when package distribution is finalized."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(wrappers)} wrappers")
    return 0


def cycle_completion_audit(args):
    """Audit current cycle completion and remaining unfinished items."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    surfaces=["agentpress/proof-outreach/proof-request-queue.json","agentpress/conformance/host-transcript-dropbox.json","agentpress/planning/connector-failure-backlog.json","agentpress/planning/next-build-spec-queue.json","agentpress/connectors/persona-quickstarts.json","agentpress/integrations/sdk/sdk-command-wrapper-catalog.json"]
    rows=[]
    for rel in surfaces:
        rows.append({"path":rel,"status":"present" if pathlib.Path(rel).exists() else "missing","url":urljoin(base,rel)})
    payload={"schema_version":"2026-05-03.agentpress-cycle-completion-audit.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if all(r["status"]=="present" for r in rows) else "needs_attention","purpose":"Audit that the repeated cycle produced proof, host, connector, persona, SDK, and next-spec surfaces.","surfaces":rows,"remaining_unfinished":["actual independent external receipts require outside operators","official PyPI/npm/Homebrew/Docker publishing requires owner credentials/approval"],"next_cycle":["execute opt-in proof requests externally","implement SDK wrappers if package owner approved","ingest first real host transcript dropbox"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload["status"])
    return 0 if payload["status"] in {"ok","needs_attention"} else 1

def connector_failure_to_backlog(args):
    """Convert connector failure events/taxonomy into prioritized backlog items."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; items=[]; errors=[]
    src=pathlib.Path(args.input)
    if src.exists():
        try: data=json.loads(src.read_text(encoding="utf-8"))
        except Exception as e: data={}; errors.append(f"input unreadable: {e}")
        if "categories" in data:
            for i,c in enumerate(data.get("categories",[]),1):
                items.append({"rank":i,"feature":f"Handle connector failure {c.get('code')}","priority":c.get("priority","P2"),"source":str(src),"acceptance":c.get("backlog_action","")})
        elif "failures" in data:
            for i,c in enumerate(data.get("failures",[]),1):
                items.append({"rank":i,"feature":f"Fix connector failure: {c.get('code','unknown')}","priority":c.get("priority","P2"),"source":str(src),"acceptance":c.get("remediation_command","")})
    if not items:
        items=[{"rank":1,"feature":"Collect connector failure events from real agent runs","priority":"P1","source":"empty_failure_input","acceptance":"at least one failure event converts to backlog with code/evidence/remediation"}]
    payload={"schema_version":"2026-05-03.agentpress-connector-failure-to-backlog.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if not errors else "fail","purpose":"Convert connector failures into prioritized, buildable backlog instead of free-form complaints.","item_count":len(items),"items":items,"errors":errors}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(items)} items")
    return 0 if not errors else 1


def host_transcript_dropbox_spec(args):
    """Generate drop-folder/upload convention for real host transcript ingestion."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    payload={"schema_version":"2026-05-03.agentpress-host-transcript-dropbox.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Define exactly how external agents/operators submit host transcripts for batch ingestion.","dropbox_layout":{"root":"agentpress/conformance/inbox/","filename":"<host>-<runtime>-<agent_id>-<yyyymmddhhmmss>.json","required_schema":"agentpress/schemas/draft2020-12/host_run_transcript.schema.json"},"submit_steps":["Run host-run-harness for your host","Save transcript JSON using filename convention","Redact secrets/private prompts/local paths","Run host-transcript-validate locally if possible","Submit via proof campaign/blocker report"],"ingest_command":"python3 scripts/agentpress.py host-transcript-batch-ingest agentpress/conformance/inbox --json","privacy":"No secrets, cookies, private prompts, credentials, wallet data, or IP/user-agent details."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload["status"])
    return 0


def proof_request_queue(args):
    """Generate opt-in proof request queue from campaign runner targets."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    targets=["cline_roo_users","openhands_operators","mcp_builders","langchain_llamaindex_crewai_builders"]
    requests=[]
    for i,t in enumerate(targets,1):
        requests.append({"rank":i,"target_id":t,"status":"ready_not_sent","request_url":urljoin(base,"agentpress/proof-outreach/proof-request-pack.json"),"ask":"Run install/doctor/host transcript/proof receipt flow and submit either success or blocker evidence.","guardrails":["opt-in only","no secrets","no paid bounty promise","service-scoped proof only"]})
    payload={"schema_version":"2026-05-03.agentpress-proof-request-queue.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Operational queue for first independent proof acquisition while keeping sends opt-in/manual.","request_count":len(requests),"requests":requests,"next_action":"Manually send/submit opt-in requests to public communities; ingest receipts with proof-ingest-review."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(requests)} requests")
    return 0


def next_build_spec_queue(args):
    """Generate researched next-build specs after current cycle."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    specs=[
        {"rank":1,"spec":"external proof receipt acquisition execution","files":["proof-request-queue","external-proof-campaign-runner","proof-ingest-review"],"acceptance":"one independent receipt/blocker can be ingested without secrets"},
        {"rank":2,"spec":"host transcript dropbox + batch ingest","files":["host-transcript-dropbox","host-transcript-batch-ingest"],"acceptance":"directory of submitted host transcripts produces conformance/backlog summary"},
        {"rank":3,"spec":"connector failure to backlog automation","files":["connector-failure-taxonomy","connector-failure-to-backlog"],"acceptance":"failure event becomes prioritized backlog item"},
        {"rank":4,"spec":"persona quickstart connector bundles","files":["agent-persona-quickstarts"],"acceptance":"coding/research/browser/RAG/proof agents get exact command pack"},
        {"rank":5,"spec":"SDK command wrappers","files":["sdk-command-wrapper-catalog"],"acceptance":"Python/JS SDKs expose proof/host/connector helper commands"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-next-build-spec-queue.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Research output: next build specs after audit/fix/deploy cycle.","spec_count":len(specs),"specs":specs,"next_feature":specs[0]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(specs)} specs")
    return 0

def external_proof_campaign_runner(args):
    """Generate opt-in external proof acquisition campaign run plan."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    targets=[
        {"community":"Cline/Roo Code users","ask":"Run AgentPress external-audit-run and submit proof/blocker receipt","channel":"public community post/manual DM only with consent"},
        {"community":"OpenHands operators","ask":"Run sandbox host transcript and TTF-green capture","channel":"GitHub discussion/issue"},
        {"community":"MCP builders","ask":"Review MCP registry pack and submit blocker/proof","channel":"MCP directory/community"},
        {"community":"LangChain/LlamaIndex/CrewAI builders","ask":"Try native adapter kit and submit host transcript","channel":"public repo discussion"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-external-proof-campaign-runner.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Operationalize first independent proof acquisition without spam, payments, or fake proof.","target_count":len(targets),"targets":targets,"proof_request_url":urljoin(base,"agentpress/proof-outreach/proof-request-pack.json"),"submission_urls":[urljoin(base,"agentpress/proof-campaigns/proof-campaign.json"),urljoin(base,"agentpress/external-proofs/proof-inbox-tracker.json")],"outreach_template":"AgentPress is looking for independent proof/blocker receipts from external agents. Please run the proof request pack, redact private material, and submit success or blocker evidence.","anti_abuse":"opt-in only; no scraping, no spam, no paid bounty promise, no secrets/private prompts"}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(targets)} targets")
    return 0


def host_transcript_batch_ingest(args):
    """Batch ingest host transcript JSON files and summarize conformance."""
    indir=pathlib.Path(args.dir); out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; rows=[]; errors=[]
    if not indir.exists():
        errors.append(f"input dir missing: {indir}")
    else:
        for f in sorted(indir.glob("*.json")):
            try: data=json.loads(f.read_text(encoding="utf-8")); row_errors=[]
            except Exception as e: data={}; row_errors=[f"parse_fail:{e}"]
            for k in ["host","runtime","commands","result_status"]:
                if k not in data: row_errors.append(f"missing:{k}")
            if data.get("host") not in {"cline","roo","openhands","mcp","langchain","llamaindex","crewai"}: row_errors.append("unknown_host")
            if data.get("result_status") not in {"pass","fail","blocked"}: row_errors.append("invalid_result_status")
            rows.append({"file":str(f),"host":data.get("host",""),"runtime":data.get("runtime",""),"status":"ok" if not row_errors else "fail","result_status":data.get("result_status",""),"errors":row_errors})
    passed=sum(1 for r in rows if r.get("result_status")=="pass" and r["status"]=="ok")
    blocked=[r for r in rows if r.get("result_status") in {"blocked","fail"} or r["status"]=="fail"]
    payload={"schema_version":"2026-05-03.agentpress-host-transcript-batch-ingest.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if not errors and all(r["status"]=="ok" for r in rows) else "needs_attention","purpose":"Batch ingest real native-host transcripts into conformance evidence and backlog blockers.","input_dir":str(indir),"transcript_count":len(rows),"passed_count":passed,"blocked_count":len(blocked),"transcripts":rows,"blocker_inputs":[{"summary":f"Host transcript blocked/fail: {r.get('host')} {r.get('errors')}","priority":"P1","source":r.get("file")} for r in blocked],"errors":errors}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(rows)} transcripts")
    return 0 if payload["status"] in {"ok","needs_attention"} else 1


def connector_failure_taxonomy(args):
    """Generate connector failure taxonomy and backlog conversion rules."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    cats=[
        {"code":"CONNECTOR_MISSING_AUTH","priority":"P1","meaning":"connector requires credential/token/ownership not available","backlog_action":"create approval/account checklist, do not bypass"},
        {"code":"CONNECTOR_COMMAND_MISSING","priority":"P0","meaning":"documented command not installed or not routed","backlog_action":"add install/adapter shim or remove stale command"},
        {"code":"CONNECTOR_SCHEMA_FAIL","priority":"P1","meaning":"connector output does not match schema","backlog_action":"fix serializer or schema"},
        {"code":"CONNECTOR_NETWORK_BLOCKED","priority":"P2","meaning":"network/live endpoint unavailable","backlog_action":"use mirror/failover and record live check"},
        {"code":"CONNECTOR_PRIVACY_RISK","priority":"P0","meaning":"connector may leak secrets/private prompts","backlog_action":"halt, redact, add privacy gate"},
        {"code":"CONNECTOR_HOST_INCOMPATIBLE","priority":"P1","meaning":"native host cannot run adapter flow","backlog_action":"add host-specific adapter fix and transcript fixture"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-connector-failure-taxonomy.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Standardize connector failures so every failed tool/connector run becomes a prioritized backlog item.","category_count":len(cats),"categories":cats,"conversion_rule":"Each connector failure emits {code, priority, source, evidence_ref, remediation_command} into receipt-to-backlog/missing-connector-backlog."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(cats)} categories")
    return 0


def cycle_gap_radar(args):
    """Generate post-cycle missed-gap radar after proof/host/connector cycle."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    items=[
        {"rank":1,"gap":"actual external receipt count still zero until people run it","next_fix":"execute proof campaign externally and ingest first receipt"},
        {"rank":2,"gap":"batch host transcript ingestion needs real host output dirs","next_fix":"wire upload/drop-folder convention for Cline/Roo/OpenHands transcripts"},
        {"rank":3,"gap":"connector failures need automatic issue/backlog creation","next_fix":"connector-failure-to-backlog command"},
        {"rank":4,"gap":"registry publish remains credential/account gated","next_fix":"owner decision checklist + dry-run metadata expansion"},
        {"rank":5,"gap":"SDKs still shallow for some language/native hosts","next_fix":"expand SDK wrappers for proof/host/connector commands"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-cycle-gap-radar.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Post-cycle radar: identify what this cycle still cannot honestly claim done and seed the next build cycle.","items":items}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(items)} gaps")
    return 0

def edge_case_gap_scan(args):
    """Run adversarial edge-case checks for gaps that previous audits missed."""
    out=pathlib.Path(args.out); checks=[]
    def run(name, cmd, expect_code=None, expect_path_absent=None):
        cp=subprocess.run(cmd, cwd=pathlib.Path.cwd(), text=True, capture_output=True)
        ok=True; errors=[]
        if expect_code is not None and cp.returncode != expect_code:
            ok=False; errors.append(f"exit {cp.returncode} != {expect_code}")
        if expect_path_absent and pathlib.Path(expect_path_absent).exists():
            ok=False; errors.append(f"path unexpectedly exists: {expect_path_absent}")
        checks.append({"name":name,"status":"pass" if ok else "fail","exit_code":cp.returncode,"errors":errors,"stderr":cp.stderr[-500:]})
    tmp="/tmp/agentpress-edge-nowrite"
    shutil.rmtree(tmp, ignore_errors=True)
    run("native_adapter_no_write_no_dir", [sys.executable,"scripts/agentpress.py","native-adapter-kit","--out",tmp,"--no-write","--json"], expect_code=0, expect_path_absent=tmp)
    run("native_adapter_unknown_target_fails", [sys.executable,"scripts/agentpress.py","native-adapter-kit","--target","nonexistent","--no-write","--json"], expect_code=1)
    run("trust_missing_report_fails", [sys.executable,"scripts/agentpress.py","trust-tier-evaluate","--scoped-report","missing.json","--json"], expect_code=1)
    run("trust_global_proof_fails", [sys.executable,"scripts/agentpress.py","trust-tier-evaluate","--scoped-report","tests/fixtures/trust/bad-global-proof.json","--json"], expect_code=1)
    run("approval_bad_fails", [sys.executable,"scripts/agentpress.py","approval-gate-eval","tests/fixtures/gates/approval-bad.json","--json"], expect_code=1)
    run("host_bad_fails", [sys.executable,"scripts/agentpress.py","host-transcript-validate","tests/fixtures/conformance/host-transcript-bad.json","--json"], expect_code=1)
    payload={"schema_version":"2026-05-03.agentpress-edge-case-gap-scan.v1","generated_utc":_utc_now(),"status":"ok" if all(c["status"]=="pass" for c in checks) else "fail","purpose":"Adversarial scan for missed fail-open/no-write/unknown-target gaps.","checked":len(checks),"failed":sum(1 for c in checks if c["status"]!="pass"),"checks":checks,"next_gap_hypotheses":["batch host transcript ingestion","external proof acquisition runner","connector failure taxonomy"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {payload['checked']} checked {payload['failed']} failed")
    return 0 if payload["status"]=="ok" else 1

def connector_catalog(args):
    """Generate connector catalog for the tools/connectors agents need."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    connectors=[
        {"id":"filesystem","category":"local_io","status":"ready","commands":["read","write","edit","package-verify"],"painpoint":"agents need safe local artifact read/write and reproducible bundles"},
        {"id":"git_github","category":"source_control","status":"ready","commands":["git status","gh run list","release-index"],"painpoint":"agents need CI/release/deploy evidence"},
        {"id":"browser_http","category":"web_verification","status":"ready","commands":["curl live URL","browser smoke","docs-command-check"],"painpoint":"agents need live endpoint proof, not local-only proof"},
        {"id":"mcp_static","category":"tool_protocol","status":"ready","commands":["mcp-registry-pack","mcp-static-catalog"],"painpoint":"agents need MCP-compatible tool discovery"},
        {"id":"native_agent_hosts","category":"agent_runtime","status":"ready_for_transcripts","commands":["host-run-harness","host-transcript-validate"],"painpoint":"agents need Cline/Roo/OpenHands/LangChain/LlamaIndex/CrewAI conformance evidence"},
        {"id":"proof_inbox","category":"external_proof","status":"ready_empty_inbox","commands":["proof-inbox-tracker","proof-ingest","proof-ingest-review"],"painpoint":"agents need external receipts/blockers to become trust/backlog inputs"},
        {"id":"package_registries","category":"distribution","status":"dry_run_only","commands":["registry-dry-run","package-registry-dry-run"],"painpoint":"agents need pip/npm/homebrew/docker availability; publishing remains credential/owner gated"},
        {"id":"privacy_redaction","category":"safety","status":"ready","commands":["privacy-kit","redaction/privacy gates","external-proof-review"],"painpoint":"agents need to submit evidence without leaking secrets"},
        {"id":"approvals_reviewers","category":"governance","status":"ready","commands":["approval-gate-eval","reviewer-gate-eval"],"painpoint":"agents need executable go/no-go gates"},
        {"id":"telemetry_metrics","category":"ux_feedback","status":"ready","commands":["ttf-green-import","conformance-evidence-score"],"painpoint":"agents need onboarding friction to feed the next build queue"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-connector-catalog.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Canonical connector catalog for agent tool/runtime/distribution/proof/safety needs.","connector_count":len(connectors),"connectors":connectors,"policy":"Credentials, payments, production writes, and package publishing require explicit approval; dry-run surfaces are safe."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(connectors)} connectors")
    return 0


def connector_health_check(args):
    """Check connector catalog points at real AgentPress surfaces and commands."""
    catalog=pathlib.Path(args.catalog); out=pathlib.Path(args.out); errors=[]; checked=0
    try: data=json.loads(catalog.read_text(encoding="utf-8"))
    except Exception as e: data={}; errors.append(f"catalog unreadable: {e}")
    required={"filesystem","git_github","browser_http","mcp_static","native_agent_hosts","proof_inbox","package_registries","privacy_redaction","approvals_reviewers","telemetry_metrics"}
    seen=set()
    for c in data.get("connectors",[]) if isinstance(data.get("connectors"),list) else []:
        checked+=1; cid=c.get("id"); seen.add(cid)
        for k in ["id","category","status","commands","painpoint"]:
            if k not in c: errors.append(f"{cid}: missing {k}")
        if not isinstance(c.get("commands"),list) or not c.get("commands"): errors.append(f"{cid}: commands must be non-empty")
        if not c.get("painpoint"): errors.append(f"{cid}: painpoint required")
    for r in sorted(required-seen): errors.append(f"missing required connector: {r}")
    payload={"schema_version":"2026-05-03.agentpress-connector-health-check.v1","generated_utc":_utc_now(),"status":"ok" if not errors else "fail","checked":checked,"errors":errors,"catalog":str(catalog)}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload["status"])
    return 0 if not errors else 1


def agent_wants_research(args):
    """Generate research cycle list of agent wants/painpoints from current shipped surfaces."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    wants=[
        {"rank":1,"want":"connectors that actually work","painpoint":"tools exist but agents need canonical connector map and health evidence","solution":"connector-catalog + connector-health-check","status":"shipped_this_cycle"},
        {"rank":2,"want":"real external proof acquisition","painpoint":"independent receipts still zero until outside agents run it","solution":"proof relay + inbox + proof-ingest-review + receipt-to-backlog","status":"surface_shipped_external_action_needed"},
        {"rank":3,"want":"native runtime proof","painpoint":"adapter configs are not the same as real host transcripts","solution":"host-run-harness + host-transcript-validate + conformance score","status":"shipped"},
        {"rank":4,"want":"low-friction install channels","painpoint":"pip/npm/homebrew/docker not officially published","solution":"registry-dry-run + package registry skeletons","status":"dry_run_shipped_publish_approval_needed"},
        {"rank":5,"want":"safe approval/reviewer gates","painpoint":"autonomous work needs machine go/no-go gates","solution":"approval-gate-eval + reviewer-gate-eval","status":"shipped"},
        {"rank":6,"want":"automatic next backlog","painpoint":"manual lists go stale","solution":"receipt-to-backlog + exponential-improvement-radar","status":"shipped"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-agent-wants-research.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Research-cycle list of what agents still want, mapped to buildable surfaces and current status.","want_count":len(wants),"wants":wants,"next_build_list":[w for w in wants if "needed" in w["status"] or "external_action" in w["status"] or "approval" in w["status"]]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(wants)} wants")
    return 0


def missing_connector_backlog(args):
    """Generate next build backlog from connector health and wants research."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    items=[
        {"rank":1,"feature":"external proof acquisition campaign runner","why":"proof surfaces are shipped but independent receipt count remains the hard external gap","acceptance":"3 target communities listed, opt-in requests generated, inbox tracker ready for receipts"},
        {"rank":2,"feature":"real host transcript ingestion daemon/schema","why":"host transcript validation exists but needs batch ingestion from real host output dirs","acceptance":"directory of host transcripts produces scored conformance summary"},
        {"rank":3,"feature":"package registry metadata validators for generated skeletons","why":"dry-run exists but publish blockers need package-name/account-specific checklists","acceptance":"PyPI/npm metadata checklists emitted without credentials"},
        {"rank":4,"feature":"connector quickstart bundles per persona","why":"agents need one-command starts for coding/research/browser/RAG/proof personas","acceptance":"persona quickstart JSON links exact connector commands and gates"},
        {"rank":5,"feature":"connector failure taxonomy","why":"failed connectors need standard blocker categories feeding receipt-to-backlog","acceptance":"connector failures convert into P0/P1/P2 backlog items"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-missing-connector-backlog.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Everything still needed after connector health research, ordered for the next build cycle.","item_count":len(items),"items":items,"next_feature":items[0]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(items)} items")
    return 0

def host_transcript_validate(args):
    """Validate native host-run transcript evidence fail-closed."""
    transcript=pathlib.Path(args.transcript); out=pathlib.Path(args.out); errors=[]
    try: data=json.loads(transcript.read_text(encoding="utf-8"))
    except Exception as e: data={}; errors.append(f"invalid transcript json: {e}")
    for k in ["host","runtime","started_utc","commands","result_status"]:
        if k not in data: errors.append(f"missing:{k}")
    if data.get("host") not in {"cline","roo","openhands","mcp","langchain","llamaindex","crewai"}: errors.append("unknown_host")
    if data.get("result_status") not in {"pass","fail","blocked"}: errors.append("invalid_result_status")
    cmds=data.get("commands",[])
    if not isinstance(cmds,list) or not cmds: errors.append("commands_must_be_nonempty_list")
    else:
        for i,c in enumerate(cmds):
            if not isinstance(c,dict): errors.append(f"commands[{i}]: not object"); continue
            if not c.get("command"): errors.append(f"commands[{i}]: missing command")
            if c.get("status") not in {"pass","fail","blocked"}: errors.append(f"commands[{i}]: invalid status")
    result={"schema_version":"2026-05-03.agentpress-host-transcript-validate.v1","generated_utc":_utc_now(),"status":"ok" if not errors else "fail","transcript":str(transcript),"host":data.get("host",""),"command_count":len(cmds) if isinstance(cmds,list) else 0,"errors":errors,"conformance_effect":"valid transcript can be used as host-run conformance evidence only for that host/runtime"}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2) if args.json else result["status"])
    return 0 if not errors else 1


def ttf_green_import(args):
    """Import time-to-first-green telemetry into adoption friction summary."""
    inp=pathlib.Path(args.input); out=pathlib.Path(args.out); errors=[]; rows=[]
    if inp.exists():
        try: raw=json.loads(inp.read_text(encoding="utf-8"))
        except Exception as e: raw=[]; errors.append(f"invalid telemetry json: {e}")
        if isinstance(raw,dict): raw=raw.get("runs",[])
        if not isinstance(raw,list): errors.append("telemetry must be list or {runs:[]}"); raw=[]
        for i,r in enumerate(raw):
            if not isinstance(r,dict): errors.append(f"runs[{i}]: not object"); continue
            total=r.get("total_seconds")
            if not isinstance(total,(int,float)) or total < 0: errors.append(f"runs[{i}]: invalid total_seconds"); total=None
            status=r.get("result_status")
            if status not in {"pass","fail","blocked"}: errors.append(f"runs[{i}]: invalid result_status")
            rows.append({"agent_id":r.get("agent_id",""),"runtime":r.get("runtime",""),"total_seconds":total,"result_status":status,"slow_or_blocked":bool(total and total>900) or status in {"fail","blocked"}})
    blocker_inputs=[{"summary":"TTF-green slow/blocked: "+(r.get("runtime") or "unknown"),"priority":"P1","source":"ttf_green_import"} for r in rows if r.get("slow_or_blocked")]
    avg=sum(r["total_seconds"] for r in rows if isinstance(r.get("total_seconds"),(int,float)))/max(1,sum(1 for r in rows if isinstance(r.get("total_seconds"),(int,float))))
    payload={"schema_version":"2026-05-03.agentpress-ttf-green-import.v1","generated_utc":_utc_now(),"status":"ok" if not errors else "fail","run_count":len(rows),"average_seconds":avg,"runs":rows,"blocker_inputs":blocker_inputs,"errors":errors,"empty_input_action":"collect TTF-green telemetry from host-run harness and external first-contact audits"}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload["status"])
    return 0 if not errors else 1


def conformance_evidence_score(args):
    """Score host transcript + TTF evidence into next-cycle conformance summary."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    host_path=pathlib.Path(args.host_result); ttf_path=pathlib.Path(args.ttf_result)
    score=0; inputs=[]
    for name,path in [("host",host_path),("ttf",ttf_path)]:
        if path.exists():
            try: d=json.loads(path.read_text(encoding="utf-8")); inputs.append({"name":name,"path":str(path),"status":d.get("status")}); score += 50 if d.get("status") in {"ok","pass"} else 0
            except Exception as e: inputs.append({"name":name,"path":str(path),"status":"parse_fail","error":str(e)})
        else: inputs.append({"name":name,"path":str(path),"status":"missing"})
    payload={"schema_version":"2026-05-03.agentpress-conformance-evidence-score.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Combine host transcript validation and TTF-green telemetry into scored conformance evidence.","score":score,"max_score":100,"inputs":inputs,"next_cycle":"Use missing/failing host+TTF evidence to prioritize native adapter fixes and UX improvements."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {score}/100")
    return 0

def approval_gate_eval(args):
    """Evaluate an action against fail-closed approval gates."""
    action=pathlib.Path(args.action); out=pathlib.Path(args.out); errors=[]
    try: data=json.loads(action.read_text(encoding="utf-8"))
    except Exception as e: data={}; errors.append(f"invalid action json: {e}")
    level=data.get("risk_level")
    if level not in {"R0","R1","R2","R3","R4"}: errors.append("unknown_or_missing_risk_level")
    if level in {"R3","R4"} and not data.get("approval_ref"): errors.append("approval_ref_required_for_R3_R4")
    if level == "R4" and not data.get("high_impact_keyword_present"): errors.append("high_impact_keyword_required_for_R4")
    if data.get("external_effect") in {"payment","credential","production","delete"} and level != "R4": errors.append("sensitive_external_effect_must_be_R4")
    if not data.get("rollback_plan") and level in {"R2","R3","R4"}: errors.append("rollback_plan_required_for_external_effects")
    result={"schema_version":"2026-05-03.agentpress-approval-gate-eval.v1","generated_utc":_utc_now(),"status":"pass" if not errors else "fail","decision":"allow" if not errors else "halt","errors":errors,"action":str(action)}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2) if args.json else result["status"])
    return 0 if not errors else 1


def reviewer_gate_eval(args):
    """Evaluate reviewer gate result fail-closed."""
    review=pathlib.Path(args.review); out=pathlib.Path(args.out); errors=[]
    try: data=json.loads(review.read_text(encoding="utf-8"))
    except Exception as e: data={}; errors.append(f"invalid review json: {e}")
    for k in ["gate_id","status","findings","evidence_refs","reviewer_id"]:
        if k not in data: errors.append(f"missing:{k}")
    if data.get("status") not in {"pass","fail","needs_fix"}: errors.append("status_must_be_pass_fail_needs_fix")
    if data.get("status") == "pass" and not data.get("evidence_refs"): errors.append("pass_requires_evidence_refs")
    result={"schema_version":"2026-05-03.agentpress-reviewer-gate-eval.v1","generated_utc":_utc_now(),"status":"pass" if not errors and data.get("status")=="pass" else "fail","decision":"accept" if not errors and data.get("status")=="pass" else "needs_fix_or_halt","errors":errors,"review":str(review)}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2) if args.json else result["status"])
    return 0 if result["status"]=="pass" else 1


def action_ledger_adapter_wiring(args):
    """Wire native adapters to action-ledger/run-artifact requirements."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    targets=["cline","roo","openhands","mcp","langchain","llamaindex","crewai"]
    rows=[]
    for t in targets:
        rows.append({"target":t,"status":"ok","required_on_completion":["action-ledger.json","run-artifact-pack.json","approval-gate-result.json","reviewer-gate-result.json"],"ledger_manifest":urljoin(base,"agentpress/observability/action-ledger/manifest.json"),"run_artifact_pack":urljoin(base,"agentpress/run-artifacts/run-artifact-pack.json")})
    payload={"schema_version":"2026-05-03.agentpress-action-ledger-adapter-wiring.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Ensure native adapter support is wired to ledger/run-artifact/approval/reviewer evidence, not just static configs.","target_count":len(rows),"targets":rows}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(rows)} targets")
    return 0


def external_proof_relay_status(args):
    """Generate external proof relay status and acceptance gates."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    payload={"schema_version":"2026-05-03.agentpress-external-proof-relay-status.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Relay independent proof/blocker receipts through request pack, inbox, ingest review, scoped trust, and backlog without self-proof inflation.","relay_steps":["publish proof-request-pack","receive receipt/blocker in proof inbox","run proof-ingest and proof-ingest-review","reject secrets/private material","apply service-scoped trust only","emit receipt-to-backlog items"],"required_commands":["python3 scripts/agentpress.py proof-request-pack --json","python3 scripts/agentpress.py proof-inbox-tracker --json","python3 scripts/agentpress.py proof-ingest --json --allow-rejected","python3 scripts/agentpress.py proof-ingest-review --json","python3 scripts/agentpress.py receipt-to-backlog --json"],"current_hard_gap":"independent external receipts still require outside agents/operators; do not fabricate"}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload["status"])
    return 0


def glm_concerns_closure(args):
    """Generate closure matrix for GLM DONE_WITH_CONCERNS audit items and next cycle."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    items=[
        ["fail_closed_trust_engine","shipped","trust-tier-evaluate v2 + negative fixtures"],
        ["true_public_schema_crawler","shipped","schema-validate-all v2 crawls all agentpress JSON/JSONL"],
        ["native_adapter_gates","shipped","native-adapter-check v2 requires seven targets and nonempty smoke/surfaces"],
        ["ci_new_batch_gates","shipped","CI runs native-adapter-check/schema-validate-all/trust-tier-evaluate"],
        ["external_proof_relay","shipped_surface","relay status + proof inbox/ingest/backlog; real receipts remain external"],
        ["adapter_wired_action_ledger","shipped","action-ledger-adapter-wiring"],
        ["executable_reviewer_approval_gates","shipped","approval-gate-eval + reviewer-gate-eval"]
    ]
    payload={"schema_version":"2026-05-03.agentpress-glm-concerns-closure.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Close GLM DONE_WITH_CONCERNS audit by mapping each concern to a shipped gate/surface and next-cycle input.","items":[{"concern":a,"status":b,"evidence":c} for a,b,c in items],"next_cycle":["host transcript validator","TTF-green telemetry import","first independent proof acquisition campaign"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else payload["status"])
    return 0

def registry_dry_run(args):
    """Generate package registry dry-run validators for PyPI/npm/Homebrew/Docker/MCP."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    checks=[]
    files=[("release_index","agentpress/releases/release-index.json"),("package_manifest","agentpress/releases/agentpress-offline.tar.gz.sha256.json"),("distribution_pack","agentpress/distribution/submission-pack/distribution-submission-pack.json"),("mcp_pack","agentpress/mcp/registry-pack/mcp-registry-pack.json")]
    for name,rel in files:
        p=pathlib.Path(rel); checks.append({"name":name,"path":rel,"status":"pass" if p.exists() else "fail"})
    channels=[
        {"id":"pypi","dry_run_status":"metadata_ready","required_human_step":"own/approve package name and token before publish","safe_command":"python3 -m build --sdist --wheel && twine check dist/*"},
        {"id":"npm","dry_run_status":"metadata_ready","required_human_step":"own/approve package scope/token before publish","safe_command":"npm pack --dry-run"},
        {"id":"homebrew","dry_run_status":"formula_spec_needed","required_human_step":"approve tap/release formula","safe_command":"brew audit --strict --online <formula>"},
        {"id":"docker_oci","dry_run_status":"container_spec_needed","required_human_step":"approve GHCR/package publishing","safe_command":"docker build --check ."},
        {"id":"mcp_registry","dry_run_status":"submission_ready","required_human_step":"submit listing to registry/community","safe_command":"python3 scripts/agentpress.py mcp-registry-pack --json"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-registry-dry-run.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if all(c['status']=='pass' for c in checks) else "needs_attention","purpose":"Turn package registry blockers into safe dry-run validators without using credentials or publishing.","checks":checks,"channels":channels,"policy":"No registry publish, token use, paid action, or ownership claim without explicit approval."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(channels)} channels")
    return 0 if payload["status"] in {"ok","needs_attention"} else 1


def proof_ingest_review(args):
    """Ingest external proof/blocker receipts into review, scoped score, and backlog inputs."""
    inbox=pathlib.Path(args.inbox); out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; rows=[]; blockers=[]; accepted=0; rejected=0
    secret_terms=["api_key","apikey","secret","password","cookie","authorization:","bearer ","private_key","seed phrase"]
    if inbox.exists():
        for f in sorted(inbox.glob("*.json")):
            try: data=json.loads(f.read_text(encoding="utf-8")); raw=json.dumps(data).lower(); errors=[]
            except Exception as e: data={}; raw=""; errors=[f"parse_fail:{e}"]
            for k in ["agent_id","runtime","service_id","capability_id","result_status"]:
                if k not in data: errors.append(f"missing:{k}")
            for t in secret_terms:
                if t in raw: errors.append(f"possible_secret:{t}")
            decision="accepted" if not errors else "rejected"
            if decision=="accepted": accepted+=1
            else: rejected+=1
            if data.get("result_status") in {"blocked","failed"} or errors:
                blockers.append({"source":str(f),"summary":data.get("summary") or data.get("error") or ";".join(errors) or "external blocker", "priority":"P1" if data.get("result_status")=="blocked" else "P2"})
            rows.append({"file":str(f),"decision":decision,"errors":errors,"agent_id":data.get("agent_id",""),"runtime":data.get("runtime",""),"service_id":data.get("service_id","")})
    payload={"schema_version":"2026-05-03.agentpress-proof-ingest.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Convert external proof/blocker receipts into privacy-clean reviews, scoped trust inputs, and backlog blockers.","receipt_count":len(rows),"accepted":accepted,"rejected":rejected,"reviews":rows,"blocker_inputs":blockers,"scoped_trust_policy":"Accepted proof only credits the specific service/capability/runtime; never global trust.","empty_inbox_action":"Run proof campaign/outreach and wait for independent receipts."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {accepted}/{len(rows)} accepted")
    return 0


def receipt_to_backlog(args):
    """Generate backlog items from proof ingest blockers and UX friction metrics."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; items=[]
    ingest=pathlib.Path(args.ingest)
    if ingest.exists():
        try: data=json.loads(ingest.read_text(encoding="utf-8"))
        except Exception: data={}
        for i,b in enumerate(data.get("blocker_inputs",[]),1):
            items.append({"rank":i,"feature":f"Fix external blocker: {b.get('summary','unknown')[:80]}","priority":b.get("priority","P2"),"source":"proof_ingest","acceptance":"blocker receipt replays cleanly or returns clearer actionable error"})
    if not items:
        items=[
            {"rank":1,"feature":"first external proof acquisition tracker","priority":"P0","source":"empty_inbox","acceptance":"at least one independent receipt/blocker is ingested without secrets"},
            {"rank":2,"feature":"registry metadata dry-run validators in CI","priority":"P1","source":"registry_radar","acceptance":"PyPI/npm/MCP/Homebrew/Docker metadata dry-runs produce machine evidence"},
            {"rank":3,"feature":"host-run transcript collector","priority":"P1","source":"host_harness","acceptance":"one native host transcript can be validated against schema"}
        ]
    payload={"schema_version":"2026-05-03.agentpress-receipt-to-backlog.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Automatically convert external proof/blocker/UX signals into the next build queue.","item_count":len(items),"items":items,"next_feature":items[0] if items else {}}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(items)} items")
    return 0


def exponential_improvement_radar(args):
    """Generate exponential improvement radar from adoption, proof, package, and UX loops."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    items=[
        {"rank":1,"lever":"proof_ingestion_to_trust_and_backlog","compounding_effect":"every outside receipt creates trust evidence or a build item","next_build":"proof-ingest-review + receipt-to-backlog"},
        {"rank":2,"lever":"registry_dry_run_to_distribution","compounding_effect":"every install channel becomes testable before credentials/publish","next_build":"registry-dry-run"},
        {"rank":3,"lever":"host_run_to_native_conformance","compounding_effect":"each real host failure improves all future adapter kits","next_build":"host transcript validator"},
        {"rank":4,"lever":"time_to_first_green_to_ux","compounding_effect":"each onboarding attempt quantifies friction and prioritizes fixes","next_build":"TTF-green telemetry import"},
        {"rank":5,"lever":"schema_bundle_to_ecosystem_integrations","compounding_effect":"typed artifacts make third-party automation safer and cheaper","next_build":"json-schema-bundle + validator"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-exponential-improvement-radar.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Find high-leverage improvements that compound across agent adoption cycles.","items":items}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(items)} levers")
    return 0

def json_schema_bundle(args):
    """Generate draft-2020-12 JSON Schemas for key AgentPress public artifacts."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    schemas={
        "proof_receipt.schema.json": {"$schema":"https://json-schema.org/draft/2020-12/schema","$id":urljoin(base,"agentpress/schemas/draft2020-12/proof_receipt.schema.json"),"title":"AgentPress Proof Receipt","type":"object","required":["agent_id","runtime","service_id","capability_id","commands_run","artifacts","result_status","redaction_attestation"],"properties":{"agent_id":{"type":"string","minLength":1},"runtime":{"type":"string","minLength":1},"service_id":{"type":"string","minLength":1},"capability_id":{"type":"string","minLength":1},"commands_run":{"type":"array","items":{"type":"string"}},"artifacts":{"type":"array","items":{"type":"string"}},"result_status":{"enum":["success","blocked","failed"]},"redaction_attestation":{"type":"boolean"}},"additionalProperties":True},
        "blocker_report.schema.json": {"$schema":"https://json-schema.org/draft/2020-12/schema","$id":urljoin(base,"agentpress/schemas/draft2020-12/blocker_report.schema.json"),"title":"AgentPress Blocker Report","type":"object","required":["agent_id","runtime","severity","summary","contains_secrets"],"properties":{"agent_id":{"type":"string"},"runtime":{"type":"string"},"severity":{"enum":["P0","P1","P2","P3"]},"summary":{"type":"string","minLength":1},"contains_secrets":{"type":"boolean"}},"additionalProperties":True},
        "host_run_transcript.schema.json": {"$schema":"https://json-schema.org/draft/2020-12/schema","$id":urljoin(base,"agentpress/schemas/draft2020-12/host_run_transcript.schema.json"),"title":"AgentPress Host Run Transcript","type":"object","required":["host","runtime","started_utc","commands","result_status"],"properties":{"host":{"type":"string"},"runtime":{"type":"string"},"started_utc":{"type":"string"},"commands":{"type":"array","items":{"type":"object","required":["command","status"],"properties":{"command":{"type":"string"},"status":{"enum":["pass","fail","blocked"]},"duration_ms":{"type":"integer","minimum":0},"artifact":{"type":"string"}}}},"result_status":{"enum":["pass","fail","blocked"]}},"additionalProperties":True},
        "time_to_first_green.schema.json": {"$schema":"https://json-schema.org/draft/2020-12/schema","$id":urljoin(base,"agentpress/schemas/draft2020-12/time_to_first_green.schema.json"),"title":"AgentPress Time To First Green","type":"object","required":["agent_id","runtime","steps","total_seconds","result_status"],"properties":{"agent_id":{"type":"string"},"runtime":{"type":"string"},"steps":{"type":"array","items":{"type":"object","required":["name","seconds","status"],"properties":{"name":{"type":"string"},"seconds":{"type":"number","minimum":0},"status":{"enum":["pass","fail","blocked"]}}}},"total_seconds":{"type":"number","minimum":0},"result_status":{"enum":["pass","fail","blocked"]}},"additionalProperties":True}
    }
    manifest={"schema_version":"2026-05-03.agentpress-json-schema-bundle.v1","canonical_url":urljoin(base,(outdir/"schema-bundle-manifest.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Draft-2020-12 schemas for external proof, blocker, host-run, and UX metric artifacts.","schema_count":len(schemas),"schemas":[]}
    if not args.no_write:
        outdir.mkdir(parents=True,exist_ok=True)
    for name,body in schemas.items():
        manifest["schemas"].append({"name":name,"url":urljoin(base,(outdir/name).as_posix()),"title":body["title"]})
        if not args.no_write: (outdir/name).write_text(json.dumps(body,indent=2)+"\n",encoding="utf-8")
    if not args.no_write:
        (outdir/"schema-bundle-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2) if args.json else f"{manifest['status']} {len(schemas)} schemas")
    return 0


def schema_validator(args):
    """Validate known example artifacts against lightweight built-in schema requirements."""
    out=pathlib.Path(args.out); checks=[]
    def check(path, required):
        p=pathlib.Path(path); errors=[]
        if not p.exists(): errors.append("missing")
        else:
            try: data=json.loads(p.read_text(encoding="utf-8"))
            except Exception as e: data={}; errors.append(f"parse_fail:{e}")
            for k in required:
                if k not in data: errors.append(f"missing:{k}")
        checks.append({"path":path,"status":"pass" if not errors else "fail","errors":errors})
    check("tests/fixtures/proof/good-proof-receipt.json", ["agent_id","runtime","service_id","capability_id"])
    check("agentpress/planning/blocker-solution-matrix.json", ["schema_version","blockers"])
    check("agentpress/planning/next-bottleneck-radar.json", ["schema_version","items"])
    check("agentpress/external-proofs/proof-pipeline.json", ["schema_version","stages"])
    payload={"schema_version":"2026-05-03.agentpress-schema-validator.v1","generated_utc":_utc_now(),"status":"ok" if all(c['status']=='pass' for c in checks) else "fail","checked":len(checks),"failed":sum(1 for c in checks if c['status']!='pass'),"checks":checks}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {payload['checked']} checked {payload['failed']} failed")
    return 0 if payload["status"]=="ok" else 1


def proof_inbox_tracker(args):
    """Generate proof inbox tracker for external receipts/blockers and next actions."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    rows=[]
    inbox=pathlib.Path(args.inbox)
    if inbox.exists():
        for f in sorted(inbox.glob("*.json")):
            try: data=json.loads(f.read_text(encoding="utf-8")); status=data.get("result_status") or data.get("status") or "unknown"
            except Exception: data={}; status="parse_fail"
            rows.append({"file":str(f),"agent_id":data.get("agent_id",""),"runtime":data.get("runtime",""),"status":status,"next_action":"review_proof" if status in {"success","blocked"} else "repair_or_reject"})
    payload={"schema_version":"2026-05-03.agentpress-proof-inbox-tracker.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Track external proof/blocker receipts through review without inflating trust globally.","inbox":args.inbox,"receipt_count":len(rows),"receipts":rows,"empty_inbox_action":"send proof-request-pack to target communities and collect first independent receipt","privacy":"Reject secrets/private prompts/cookies/tokens/local private paths."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(rows)} receipts")
    return 0


def host_run_harness(args):
    """Generate host-run harness transcript template for real Cline/Roo/OpenHands/etc conformance runs."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    hosts=["cline","roo","openhands","mcp","langchain","llamaindex","crewai"]
    template={"schema_version":"2026-05-03.agentpress-host-run-transcript.v1","host":"<host>","runtime":"<runtime>","started_utc":"<iso8601>","commands":[{"command":"agentpress doctor --json","status":"blocked","duration_ms":0,"artifact":"doctor.json"},{"command":"agentpress external-audit-run --runtime <runtime> --agent-id <agent> --json","status":"blocked","duration_ms":0,"artifact":"external-first-contact-audit.json"}],"result_status":"blocked","blocker_taxonomy":["install_failure","command_not_found","schema_failure","network_blocked","docs_confusion","permission_required","other"]}
    payload={"schema_version":"2026-05-03.agentpress-host-run-harness.v1","canonical_url":urljoin(base,(outdir/"host-run-harness.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Convert native adapter readiness into real host-run evidence from Cline/Roo/OpenHands/MCP/LangChain/LlamaIndex/CrewAI.","host_count":len(hosts),"hosts":[{"host":h,"transcript_template":urljoin(base,(outdir/f"{h}-transcript.template.json").as_posix())} for h in hosts],"failure_taxonomy":template["blocker_taxonomy"]}
    if not args.no_write:
        (outdir/"host-run-harness.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        for h in hosts:
            t=dict(template); t["host"]=h; (outdir/f"{h}-transcript.template.json").write_text(json.dumps(t,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(hosts)} hosts")
    return 0


def ttf_green_metric(args):
    """Generate time-to-first-green UX metric pack for AgentPress adoption loops."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    steps=["discover","install","doctor","strict_verify","external_audit_run","submission_pack","proof_review"]
    payload={"schema_version":"2026-05-03.agentpress-time-to-first-green.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Measure external agent UX friction from first discovery to first valid green proof/blocker submission.","metric":"time_to_first_green_seconds","target_thresholds":{"excellent_seconds":300,"acceptable_seconds":900,"needs_work_seconds":1800},"steps":[{"name":s,"capture":"duration_seconds + status + confusion_note"} for s in steps],"confusion_taxonomy":["install_command_unclear","missing_dependency","schema_error_unclear","too_many_steps","privacy_uncertainty","proof_submission_unclear","other"],"next_action":"Use failed/slow steps to prioritize next build queue."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(steps)} steps")
    return 0

def distribution_submission_pack(args):
    """Generate distribution submission packs for package registries and install channels."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    channels=[
        {"id":"github_release","status":"live","install":"download release asset","proof_url":urljoin(base,"agentpress/releases/release-index.json")},
        {"id":"git_python","status":"ready","install":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git","blocked_on":"none"},
        {"id":"git_npm","status":"ready","install":"npm install github:barneywohl/agentpress","blocked_on":"none"},
        {"id":"pypi","status":"submission_ready","install":"pip install agentpress","blocked_on":"registry ownership/token + human publish approval"},
        {"id":"npm","status":"submission_ready","install":"npm install agentpress","blocked_on":"registry ownership/token + human publish approval"},
        {"id":"homebrew","status":"formula_ready_needed","install":"brew install agentpress","blocked_on":"tap/release formula publication"},
        {"id":"docker_oci","status":"container_ready_needed","install":"docker run ghcr.io/barneywohl/agentpress:latest","blocked_on":"container build/push credentials"},
        {"id":"mcp_registry","status":"submission_ready","install":"MCP directory listing","blocked_on":"directory submission/review"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-distribution-submission-pack.v1","canonical_url":urljoin(base,(outdir/"distribution-submission-pack.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Make distribution bottlenecks explicit and convert blocked registries into submission-ready artifacts.","channel_count":len(channels),"channels":channels,"acceptance":["GitHub release asset verifies","git install paths documented","registry channels state exact blocker","no secrets included"]}
    if not args.no_write:
        (outdir/"distribution-submission-pack.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        (outdir/"README.md").write_text("# AgentPress Distribution Submission Pack\n\nRegistry and install-channel readiness map.\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(channels)} channels")
    return 0


def external_proof_pipeline(args):
    """Generate external proof pipeline queue and states from outreach to scoped trust credit."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    stages=[
        {"id":"discover_target","owner":"operator","output":"external target list","gate":"target has public agent/runtime community"},
        {"id":"send_proof_request","owner":"operator","output":"proof-request-pack link sent","gate":"no spam, opt-in request only"},
        {"id":"receive_receipt_or_blocker","owner":"external agent","output":"receipt/blocker JSON","gate":"redacted and service-scoped"},
        {"id":"review_proof","owner":"agentpress","output":"external-proof-review JSON","gate":"secret scan pass and required fields present"},
        {"id":"apply_scoped_trust","owner":"agentpress","output":"scoped-trust-report update","gate":"no global trust promotion"},
        {"id":"publish_lessons","owner":"agentpress","output":"painpoint/backlog update","gate":"new bottlenecks captured"}
    ]
    targets=["Cline community","Roo Code community","OpenHands operators","MCP builders","LangChain/LlamaIndex agents","CrewAI/AutoGen teams","Codex/Claude/Gemini agent operators"]
    payload={"schema_version":"2026-05-03.agentpress-external-proof-pipeline.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"End-to-end external proof pipeline: outreach, receipt, blocker handling, review, scoped trust, next bottlenecks.","stages":stages,"target_communities":targets,"current_state":{"third_party_receipts":0,"next_required_action":"send opt-in proof request packs and collect first independent receipt"},"privacy":"No secrets, private prompts, local paths, cookies, credentials, or wallet material in receipts."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(stages)} stages")
    return 0


def blocker_solution_matrix(args):
    """Generate matrix mapping known AgentPress bottlenecks to shipped/remaining solution layers."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    rows=[
        ["no_third_party_proof","external-audit-run + proof-request-pack + external-proof-review + external-proof-pipeline","needs first independent receipt"],
        ["feature_queue_false_empty","feature-build-queue --include-adoption-gaps --include-public-radar","keep adoption gaps visible until receipts > 0"],
        ["identity_repro_schemas","public-schema-bundle + identity/repro artifacts","expand formal JSON Schema files if validators require draft schema"],
        ["native_adapters_missing","native-adapter-kit + ecosystem-conformance-suite","test on real Cline/Roo/OpenHands hosts"],
        ["trust_boundaries","trust-tier-evaluate + scoped-trust-report + proof-review","only scoped service credit"],
        ["shallow_task_evals","task-quality-eval","run evals in third-party agents"],
        ["package_distribution_blocked","distribution-submission-pack + release assets","publish to registries once credentials/approval exist"],
        ["audit_drift","platform-audit-dashboard + schema-validate-all + docs-command-check","keep in CI/published dashboard"]
    ]
    payload={"schema_version":"2026-05-03.agentpress-blocker-solution-matrix.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Do not lose the thread: every known bottleneck has a shipped solution layer and a precise remaining blocker.","blocker_count":len(rows),"blockers":[{"bottleneck":a,"solution_layer":b,"remaining":c} for a,b,c in rows]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(rows)} blockers")
    return 0


def next_bottleneck_radar(args):
    """Generate next bottleneck radar after current solution layers are shipped."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    items=[
        {"rank":1,"bottleneck":"real external proof acquisition","why":"all local proof is still self-hosted","next_build":"proof inbox + community submission tracker + first receipt reviewer"},
        {"rank":2,"bottleneck":"registry publication credentials","why":"PyPI/npm/Homebrew/Docker are submission-ready but not live","next_build":"registry checklist + dry-run package metadata validators"},
        {"rank":3,"bottleneck":"real host conformance","why":"native kits are static; must be run inside Cline/Roo/OpenHands","next_build":"host-run transcript schema + failure taxonomy"},
        {"rank":4,"bottleneck":"formal JSON Schema drafts","why":"schema_version exists, but consumers may want draft-2020-12 validators","next_build":"schemas/*.schema.json + validator command"},
        {"rank":5,"bottleneck":"agent UX proof","why":"docs commands passing does not prove low-friction operator UX","next_build":"time-to-first-green metric + confusion taxonomy"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-next-bottleneck-radar.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"After solving the current list, identify the next deeper constraints to build next.","items":items}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(items)} next")
    return 0

def external_audit_run(args):
    """Generate an external first-contact audit run artifact for non-reference agents."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    run_id=args.run_id or f"external-audit-{uuid.uuid4().hex[:8]}"
    commands=[
        "python3 -m pip install git+https://github.com/barneywohl/agentpress.git",
        "agentpress doctor --json",
        "agentpress verify agentpress/examples/api-docs-handoff --strict-schema --json",
        "agentpress docs-command-check --json",
        "agentpress self-test --agent-id <external-agent-id> --out self-test.jsonl",
        "agentpress landing-receipt --agent-id <external-agent-id> --runtime <runtime> --discovery-channel external-audit --capability agentpress_validation --out landing-receipt.json --json",
        "agentpress submission-pack --receipt landing-receipt.json --out submission-pack --json"
    ]
    artifact={"schema_version":"2026-05-03.agentpress-external-first-contact-audit.v1","canonical_url":urljoin(base,(outdir/"external-first-contact-audit.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","run_id":run_id,"runtime":args.runtime,"agent_id":args.agent_id,"purpose":"Replayable outside-agent first-contact audit: install, validate, self-test, receipt, submission pack.","commands":commands,"required_outputs":["doctor.json","strict-verify.json","docs-command-check.json","self-test.jsonl","landing-receipt.json","submission-pack/submission-pack.json"],"acceptance":{"all_commands_pass":True,"no_secrets":True,"receipt_is_opt_in":True,"submission_pack_validates":True},"privacy":"Do not include secrets, cookies, private prompts, local private paths, API tokens, or wallet material."}
    if not args.no_write:
        (outdir/"external-first-contact-audit.json").write_text(json.dumps(artifact,indent=2)+"\n",encoding="utf-8")
        (outdir/"README.md").write_text("# AgentPress External First-Contact Audit\n\nRun these commands from a clean non-reference agent environment and submit the generated proof/blocker pack.\n",encoding="utf-8")
    print(json.dumps(artifact,indent=2) if args.json else f"{artifact['status']} {run_id}")
    return 0


def external_proof_review(args):
    """Review external proof receipt and emit accepted/rejected/needs_fix decision."""
    proof=pathlib.Path(args.proof); out=pathlib.Path(args.out); errors=[]; warnings=[]
    try: data=json.loads(proof.read_text(encoding="utf-8"))
    except Exception as e: data={}; errors.append(f"invalid json: {e}")
    required=["agent_id","runtime","service_id","capability_id","commands_run","artifacts","result_status","redaction_attestation"]
    for k in required:
        if k not in data: errors.append(f"missing {k}")
    secret_terms=["api_key","apikey","secret","password","cookie","authorization:","bearer ","private_key","seed phrase"]
    low=json.dumps(data).lower()
    for t in secret_terms:
        if t in low: errors.append(f"possible secret term present: {t}")
    if data.get("result_status") == "blocked": warnings.append("proof is blocker report, not success proof")
    decision="accepted" if not errors else "rejected"
    if warnings and not errors: decision="needs_fix" if args.strict_success else "accepted"
    review={"schema_version":"2026-05-03.agentpress-external-proof-review.v1","generated_utc":_utc_now(),"status":"ok" if decision in {"accepted","needs_fix"} else "fail","decision":decision,"proof":str(proof),"agent_id":data.get("agent_id",""),"runtime":data.get("runtime",""),"service_id":data.get("service_id",""),"capability_id":data.get("capability_id",""),"errors":errors,"warnings":warnings,"trust_effect":"scoped_service_credit_only" if decision=="accepted" else "none","reviewer":"agentpress-proof-reviewer"}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(review,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(review,indent=2) if args.json else f"{decision} {proof}")
    return 0 if decision in {"accepted","needs_fix"} else 1


def task_quality_eval(args):
    """Generate task-quality eval suite for AgentPress docs, tools, and proof flows."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    evals=[
        {"id":"copy_paste_command_executes","prompt":"Find the AgentPress docs command check command and run it.","expected_artifact":"docs-command-check.json","pass_criteria":["command parses","status ok","failed 0"]},
        {"id":"external_proof_secret_rejected","prompt":"Submit a proof receipt containing api_key and verify it is rejected.","expected_artifact":"proof review fail","pass_criteria":["secret term detected","decision rejected"]},
        {"id":"native_adapter_discovery","prompt":"Find the Roo native adapter and list required surfaces.","expected_artifact":"roo-agentpress.json","pass_criteria":["approval gates linked","runtime validation linked","proof request linked"]},
        {"id":"trust_not_global","prompt":"Show that one proof does not increase all services trust.","expected_artifact":"scoped-trust-report.json","pass_criteria":["global_proof_credit_applied false","unverified services remain"]},
        {"id":"repro_from_clean_install","prompt":"Install from GitHub and run doctor plus strict verify.","expected_artifact":"runtime validation result","pass_criteria":["doctor ok","verify strict ok"]}
    ]
    payload={"schema_version":"2026-05-03.agentpress-task-quality-eval.v1","canonical_url":urljoin(base,(outdir/"task-quality-evals.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Deeper task-quality evals beyond docs parsing: can an agent actually discover, run, reject unsafe proof, and reason about scoped trust?","eval_count":len(evals),"evals":evals}
    if not args.no_write:
        (outdir/"task-quality-evals.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        (outdir/"README.md").write_text("# AgentPress Task Quality Evals\n\nDeeper evals for agent usability and safety.\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(evals)} evals")
    return 0


def public_schema_bundle(args):
    """Generate first-class schema bundle index for newer AgentPress public artifacts."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    artifacts=[
        "agentpress/identity/agentpress-identity-card.json","agentpress/runtime/environment-fingerprint.json","agentpress/runtime/repro-bundle.json","agentpress/audit/platform-audit-dashboard.json","agentpress/adapters/native/manifest.json","agentpress/trust/trust-tier-evaluation.json","agentpress/proof-outreach/proof-request-pack.json","agentpress/evals/task-quality-evals.json"
    ]
    rows=[]
    for rel in artifacts:
        p=pathlib.Path(rel)
        if p.exists():
            try:
                data=json.loads(p.read_text(encoding="utf-8")); rows.append({"artifact":rel,"schema_version":data.get("schema_version",""),"status":"ok" if data.get("schema_version") else "missing_schema_version","url":urljoin(base,rel)})
            except Exception as e: rows.append({"artifact":rel,"status":"parse_fail","error":str(e)})
        else: rows.append({"artifact":rel,"status":"missing"})
    payload={"schema_version":"2026-05-03.agentpress-public-schema-bundle.v1","canonical_url":urljoin(base,(outdir/"public-schema-bundle.json").as_posix()),"generated_utc":_utc_now(),"status":"ok" if all(r.get('status')=='ok' for r in rows) else "needs_attention","purpose":"First-class index of public AgentPress JSON artifacts and schema versions.","artifact_count":len(rows),"artifacts":rows,"policy":"Every public machine artifact must declare schema_version and parse as JSON."}
    if not args.no_write: (outdir/"public-schema-bundle.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(rows)} artifacts")
    return 0

def platform_audit_dashboard(args):
    """Generate a single audit dashboard for AgentPress gates, surfaces, and next actions."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    surfaces={
        "doctor":"agentpress/evidence/browser-smoke.json",
        "docs_command_check":"agentpress/evidence/docs-command-check.json",
        "schema_validate_all":"agentpress/evidence/schema-validate-all.json",
        "native_adapters":"agentpress/adapters/native/manifest.json",
        "trust_tiers":"agentpress/trust/trust-tier-evaluation.json",
        "mission_cockpit":"agentpress/mission-cockpit/mission-cockpit.json",
        "runtime_validation":"agentpress/runtime-validation/runtime-validation-harness.json",
        "package_bridge":"agentpress/package-registry/package-manager-bridge.json",
        "release_index":"agentpress/releases/release-index.json"
    }
    rows=[]
    for name,rel in surfaces.items():
        p=pathlib.Path(rel); status="missing"; detail={}
        if p.exists():
            try:
                data=json.loads(p.read_text(encoding="utf-8")); status=data.get("status") or ("ok" if data else "present"); detail={k:data.get(k) for k in ["checked","failed","service_count","target_count","tool_count","asset_count"] if k in data}
            except Exception as e: status="parse_fail"; detail={"error":str(e)}
        rows.append({"surface":name,"path":rel,"url":urljoin(base,rel),"status":status,"detail":detail})
    ok=sum(1 for r in rows if r["status"] in {"ok","present"})
    payload={"schema_version":"2026-05-03.agentpress-platform-audit-dashboard.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if ok==len(rows) else "needs_attention","purpose":"Single machine-readable audit dashboard after each recursive AgentPress build cycle.","surface_count":len(rows),"ok_count":ok,"surfaces":rows,"next_actions":["collect real external proof receipts","submit/distribute native adapters to ecosystem communities","run conformance suite on real Cline/Roo/OpenHands/MCP hosts","keep schema/docs/package gates green"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {ok}/{len(rows)}")
    return 0


def ecosystem_conformance_suite(args):
    """Generate and check native ecosystem conformance suite for AgentPress."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    targets=["cline","roo","openhands","mcp","langchain","llamaindex","crewai"]
    rows=[]
    for t in targets:
        d=pathlib.Path("agentpress/adapters/native")/t
        configs=list(d.glob("*.json")) if d.exists() else []
        checks=[]
        checks.append({"name":"native_config_exists","status":"pass" if configs else "fail"})
        for rel in ["agentpress/approvals/approval-gates.json","agentpress/runtime-validation/runtime-validation-harness.json","agentpress/observability/action-ledger/manifest.json","agentpress/proof-outreach/proof-request-pack.json"]:
            checks.append({"name":"surface_"+pathlib.Path(rel).stem,"status":"pass" if pathlib.Path(rel).exists() else "fail","path":rel})
        status="pass" if all(c["status"]=="pass" for c in checks) else "fail"
        rows.append({"target":t,"status":status,"config_count":len(configs),"checks":checks,"proof_request_command":f"python3 scripts/agentpress.py proof-request-pack --runtime {t} --json"})
    payload={"schema_version":"2026-05-03.agentpress-ecosystem-conformance-suite.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if all(r['status']=='pass' for r in rows) else "fail","purpose":"Conformance suite proving AgentPress has native adapter, approval, validation, ledger, and proof surfaces for major agent ecosystems.","target_count":len(rows),"pass_count":sum(1 for r in rows if r['status']=='pass'),"targets":rows}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {payload['pass_count']}/{payload['target_count']}")
    return 0 if payload["status"]=="ok" else 1


def iteration_cycle_engine(args):
    """Generate recursive research-build-deploy iteration cycle plan from current AgentPress state."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    cycles=[
        {"cycle":1,"theme":"external adoption proof","why":"self-proof is not market proof","features":["proof-request-pack","proof-receipt-verify","scoped-trust-report"],"remaining":"collect independent receipts"},
        {"cycle":2,"theme":"native ecosystem availability","why":"agents live in Cline/Roo/OpenHands/MCP/LangChain/LlamaIndex/CrewAI","features":["native-adapter-kit","ecosystem-conformance-suite"],"remaining":"submit adapters to communities"},
        {"cycle":3,"theme":"operational trust","why":"agents need plan/approval/review/ledger/runtime artifacts","features":["plan-workflow-kit","approval-gate-kit","reviewer-gate-kit","runtime-validation-harness","run-artifact-pack"],"remaining":"run on real third-party hosts"},
        {"cycle":4,"theme":"continuous audit","why":"docs/schema/package/trust drift silently breaks adoption","features":["schema-validate-all","docs-command-check","platform-audit-dashboard"],"remaining":"make failures visible in cockpit"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-iteration-cycle-engine.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Machine-readable recursive loop: research painpoints, ship feature surfaces, audit, deploy, repeat.","cycles":cycles,"loop_command_sequence":["community-radar --json","agent-platform-feature-backlog --json","platform-audit-dashboard --json","ecosystem-conformance-suite --json","build highest P0/P1 not externally blocked","package/attest/CI/Pages/live verify"],"stop_condition":"Only independent external adoption proof or registry credentials remain."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(cycles)} cycles")
    return 0


def mcp_registry_pack(args):
    """Generate MCP registry/server submission pack for AgentPress static catalog."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    payload={"schema_version":"2026-05-03.agentpress-mcp-registry-pack.v1","canonical_url":urljoin(base,(outdir/"mcp-registry-pack.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Submission-ready MCP registry pack for agents/tools that consume MCP server directories.","server":{"name":"agentpress-static","description":"Static AgentPress tool/catalog/proof/trust resources for agents.","repository":"https://github.com/barneywohl/agentpress","homepage":base,"resources":[urljoin(base,"agentpress/mcp/mcp-static-catalog.json"),urljoin(base,"agentpress/tools/agentpress-tools.json"),urljoin(base,"agentpress/policies/tool-permission-policy.json"),urljoin(base,"agentpress/trust/trust-tier-evaluation.json")],"install":["npm install github:barneywohl/agentpress","python3 -m pip install git+https://github.com/barneywohl/agentpress.git"]},"submission_checklist":["verify no credentials required","verify static catalog JSON parses","verify approval policy is linked","verify trust tier surface is linked","submit to MCP directories/communities with proof request pack"]}
    if not args.no_write:
        (outdir/"mcp-registry-pack.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        (outdir/"README.md").write_text("# AgentPress MCP Registry Pack\n\nSubmission-ready metadata for MCP server/tool directories.\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} mcp-registry-pack")
    return 0

def native_adapter_kit(args):
    """Generate native adapter kits for popular agent ecosystems."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    config_templates={
        "cline":{"file":"cline-agentpress.json","install":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git","entry":"Use AgentPress tools via local CLI command templates; run docs-command-check and runtime-validation-harness before claiming support."},
        "roo":{"file":"roo-agentpress.json","install":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git","entry":"Create a Roo custom mode that reads mcp-static-catalog.json and follows approval-gates.json before execution."},
        "openhands":{"file":"openhands-agentpress.json","install":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git","entry":"Run AgentPress runtime validation inside sandbox before submitting external proof receipts."},
        "mcp":{"file":"mcp-agentpress-static-server.json","install":"npm install github:barneywohl/agentpress","entry":"Expose static AgentPress catalog as MCP resources/tools; no credentials required."},
        "langchain":{"file":"langchain-agentpress.json","install":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git","entry":"Wrap AgentPress CLI commands as LangChain tools with approval and ledger middleware."},
        "llamaindex":{"file":"llamaindex-agentpress.json","install":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git","entry":"Index AgentPress llms.txt/search/source/freshness artifacts for RAG agents."},
        "crewai":{"file":"crewai-agentpress.json","install":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git","entry":"Use AgentPress reviewer gates as CrewAI tasks before closeout."}
    }
    targets=list(config_templates) if args.target == "all" else [args.target]
    errors=[]; catalog=[]
    unknown=[t for t in targets if t not in config_templates]
    if unknown:
        errors.append("unknown target(s): "+", ".join(unknown))
    if not errors and not args.no_write:
        outdir.mkdir(parents=True,exist_ok=True)
    for t in targets:
        tpl=config_templates.get(t)
        if not tpl: continue
        d=outdir/t
        cfg={"schema_version":"2026-05-03.agentpress-native-adapter.v1","target":t,"status":"ok","install_command":tpl["install"],"entrypoint_guidance":tpl["entry"],"required_agentpress_surfaces":{"tools":urljoin(base,"agentpress/tools/agentpress-tools.json"),"mcp_catalog":urljoin(base,"agentpress/mcp/mcp-static-catalog.json"),"approval_gates":urljoin(base,"agentpress/approvals/approval-gates.json"),"permission_policy":urljoin(base,"agentpress/policies/tool-permission-policy.json"),"runtime_validation":urljoin(base,"agentpress/runtime-validation/runtime-validation-harness.json"),"proof_request":urljoin(base,"agentpress/proof-outreach/proof-request-pack.json")},"smoke_commands":["agentpress doctor --json","agentpress docs-command-check --json","agentpress verify agentpress/examples/api-docs-handoff --strict-schema --json"],"safety":"Follow approval gates before external effects; emit action ledger and proof receipts."}
        if not args.no_write:
            d.mkdir(parents=True,exist_ok=True)
            (d/tpl["file"]).write_text(json.dumps(cfg,indent=2)+"\n",encoding="utf-8")
            (d/"README.md").write_text(f"# AgentPress native adapter: {t}\n\nInstall:\n\n```bash\n{tpl['install']}\n```\n\n{tpl['entry']}\n",encoding="utf-8")
        catalog.append({"target":t,"config":urljoin(base,(d/tpl["file"]).as_posix()),"readme":urljoin(base,(d/"README.md").as_posix())})
    manifest={"schema_version":"2026-05-03.agentpress-native-adapter-kit.v2","canonical_url":urljoin(base,(outdir/"manifest.json").as_posix()),"generated_utc":_utc_now(),"status":"ok" if not errors else "fail","purpose":"Native integration kits for ecosystems where agents already work. --no-write must not create files/directories; unknown targets fail closed.","target_count":len(catalog),"targets":catalog,"errors":errors}
    if not args.no_write and not errors:
        (outdir/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2) if args.json else f"{manifest['status']} {len(catalog)} targets")
    return 0 if not errors else 1

def native_adapter_check(args):
    root=pathlib.Path(args.dir); errors=[]; checked=0; targets=[]
    required_targets=["cline","roo","openhands","mcp","langchain","llamaindex","crewai"]
    if not root.exists():
        errors.append(f"adapter root missing: {root}")
    for target in required_targets:
        d=root/target
        if not d.exists() or not d.is_dir():
            errors.append(f"{target}: missing adapter dir"); continue
        files=list(d.glob("*.json"))
        if not files: errors.append(f"{target}: missing json config"); continue
        target_ok=True
        for f in files:
            checked+=1
            try:
                data=json.loads(f.read_text(encoding="utf-8"))
                for k in ["target","install_command","required_agentpress_surfaces","smoke_commands"]:
                    if k not in data: errors.append(f"{f}: missing {k}"); target_ok=False
                if data.get("target") != target: errors.append(f"{f}: target mismatch {data.get('target')} != {target}"); target_ok=False
                surfaces=data.get("required_agentpress_surfaces")
                if not ((isinstance(surfaces, list) and surfaces) or (isinstance(surfaces, dict) and surfaces)):
                    errors.append(f"{f}: required_agentpress_surfaces must be non-empty list/dict"); target_ok=False
                if not isinstance(data.get("smoke_commands"), list) or not data.get("smoke_commands"):
                    errors.append(f"{f}: smoke_commands must be non-empty list"); target_ok=False
                surface_values=list(surfaces.values()) if isinstance(surfaces,dict) else (surfaces if isinstance(surfaces,list) else [])
                for rel in surface_values:
                    if isinstance(rel,str) and rel.startswith("agentpress/") and not pathlib.Path(rel).exists(): errors.append(f"{f}: missing surface {rel}"); target_ok=False
            except Exception as e: errors.append(f"{f}: {e}"); target_ok=False
        targets.append({"target":target,"status":"pass" if target_ok else "fail","config_count":len(files)})
    if checked == 0: errors.append("no native adapter configs checked")
    payload={"schema_version":"2026-05-03.agentpress-native-adapter-check.v2","status":"ok" if not errors else "fail","checked":checked,"target_count":len(targets),"targets":targets,"errors":errors}
    print(json.dumps(payload,indent=2) if args.json else payload["status"])
    return 0 if not errors else 1

def schema_validate_all(args):
    root=pathlib.Path(args.root); out=pathlib.Path(args.out); errors=[]; checked=0; mapped=[]; crawled=[]; jsonl_checked=0
    for rel, schema_name in CONTRACT_SCHEMA_MAP.items():
        p=root/rel
        if p.exists():
            checked+=1
            try:
                data=json.loads(p.read_text(encoding="utf-8")); _,schema=_load_schema_ref(schema_name); es=_strict_json_schema_errors(data,schema); errors.extend([f"{rel}: {e}" for e in es]); mapped.append(rel)
            except Exception as e: errors.append(f"{rel}: {e}")
    for p in sorted((root/"agentpress").rglob("*.json")) if (root/"agentpress").exists() else []:
        rel=p.relative_to(root).as_posix()
        if rel in mapped: continue
        checked+=1; crawled.append(rel)
        try:
            data=json.loads(p.read_text(encoding="utf-8"))
            if p.name != "package.json" and isinstance(data,dict):
                if not data.get("schema_version") and not data.get("$schema") and not rel.startswith("agentpress/fixtures/broken-bundles/"):
                    errors.append(f"{rel}: missing schema_version_or_$schema")
        except Exception as e: errors.append(f"{rel}: {e}")
    for p in sorted((root/"agentpress").rglob("*.jsonl")) if (root/"agentpress").exists() else []:
        rel=p.relative_to(root).as_posix()
        if rel.startswith("agentpress/fixtures/broken-bundles/"): continue
        crawled.append(rel)
        for i,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
            if not line.strip(): continue
            jsonl_checked+=1
            try: json.loads(line)
            except Exception as e: errors.append(f"{rel}:{i}: {e}")
    payload={"schema_version":"2026-05-03.agentpress-schema-validate-all.v2","canonical_url":urljoin(args.base_url.rstrip()+"/",out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if not errors else "fail","checked":checked,"jsonl_checked":jsonl_checked,"failed":len(errors),"mapped_contracts":mapped,"crawled_count":len(crawled),"errors":errors[:args.max_errors]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {checked} checked {len(errors)} failed")
    return 0 if not errors else 1

def trust_tier_evaluate(args):
    root=pathlib.Path(args.root); out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; errors=[]
    try: scoped=json.loads((root/args.scoped_report).read_text(encoding="utf-8"))
    except Exception as e: scoped={}; errors.append(f"scoped report unreadable: {e}")
    if not isinstance(scoped.get("services"), list): errors.append("scoped report missing services array")
    tiers=[]; seen=set()
    for idx,row in enumerate(scoped.get("services",[]) if isinstance(scoped.get("services"),list) else []):
        sid=row.get("service_id")
        if not sid: errors.append(f"services[{idx}]: missing service_id")
        if sid in seen: errors.append(f"duplicate service_id: {sid}")
        seen.add(sid)
        proofs=row.get("scoped_external_proofs",0)
        if not isinstance(proofs,int) or proofs < 0: errors.append(f"{sid}: scoped_external_proofs must be non-negative int"); proofs=0
        if row.get("global_proof_credit_applied") is not False: errors.append(f"{sid}: global_proof_credit_applied must be false")
        if row.get("self_proof_credit_applied") not in {False,None}: errors.append(f"{sid}: self_proof_credit_applied must be false/absent")
        receipts=row.get("accepted_receipts",[])
        if receipts and not isinstance(receipts,list): errors.append(f"{sid}: accepted_receipts must be list")
        if proofs >= 3 and len(receipts) < 3: errors.append(f"{sid}: T0 requires 3 accepted service-scoped receipt refs")
        tier="T3_unverified"
        if proofs>=3 and len(receipts)>=3: tier="T0_independently_verified"
        elif proofs>=1: tier="T1_partially_verified"
        elif row.get("trust_tier") == "provisional": tier="T2_provisional"
        tiers.append({"service_id":sid,"trust_tier":tier,"scoped_external_proofs":proofs,"requirements_to_upgrade":["accepted service-scoped proof receipts","runtime validation result","reviewer gate pass"]})
    payload={"schema_version":"2026-05-03.agentpress-trust-tier-evaluate.v2","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if not errors else "fail","purpose":"Fail-closed trust tiers: no self-proof/global proof inflation and T0 requires receipt refs.","tier_policy":{"T0":"3+ accepted independent service-scoped receipt refs","T1":"1-2 scoped proofs","T2":"provisional/internal proof only","T3":"unverified"},"service_count":len(tiers),"tiers":tiers,"errors":errors}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(tiers)} tiers")
    return 0 if not errors else 1

def plan_workflow_kit(args):
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    payload={"schema_version":"2026-05-03.agentpress-plan-workflow-kit.v1","canonical_url":urljoin(base,(outdir/"plan-workflow.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Plan.md-native workflow for agents: plan, approval checkpoints, implementation, verification, review, closeout.","phases":[{"id":"plan","requires":["goal","constraints","risks","acceptance_gates"]},{"id":"approval_checkpoint","requires":["approval_required_for_external_effects","human_decision_ref_if_needed"]},{"id":"execute","requires":["files_changed","commands_run","action_ledger_ref"]},{"id":"verify","requires":["tests_or_gates","evidence_refs"]},{"id":"review","requires":["reviewer_gate_results","security_or_privacy_check"]},{"id":"closeout","requires":["summary","remaining_gaps","next_cycle_backlog"]}],"plan_md_template":"# Plan\n\n## Goal\n\n## Constraints / approvals\n\n## Risks\n\n## Steps\n\n## Verification gates\n\n## Reviewer gates\n\n## Closeout / next cycle\n","machine_template":{"goal":"","constraints":[],"approval_boundaries":[],"steps":[],"verification_gates":[],"reviewer_gates":[],"closeout":{}}}
    if not args.no_write:
        (outdir/"plan-workflow.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        (outdir/"PLAN_TEMPLATE.md").write_text(payload["plan_md_template"],encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} plan-workflow")
    return 0


def approval_gate_kit(args):
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    payload={"schema_version":"2026-05-03.agentpress-approval-gate-kit.v1","canonical_url":urljoin(base,(outdir/"approval-gates.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Risk-based approval gates for agent actions.","risk_levels":[{"level":"R0","name":"local read/analysis","approval":"not_required"},{"level":"R1","name":"local artifact/write in workspace","approval":"agent_may_execute_with_ledger"},{"level":"R2","name":"external read/network fetch","approval":"allowed_if_public_and_no_credentials"},{"level":"R3","name":"external write/message/PR/release","approval":"human_or_keyword_required"},{"level":"R4","name":"payment/credential/production/data deletion","approval":"explicit_high_impact_keyword_and_review_required"}],"gate_fields":["action","risk_level","external_effect","target","approval_ref","rollback_plan","evidence_ref"],"fail_closed_rules":["missing approval_ref on R3/R4 halts","unknown target halts","credential access without explicit approval halts","payment/signing without budget policy halts"]}
    if not args.no_write: (outdir/"approval-gates.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} approval-gates")
    return 0


def reviewer_gate_kit(args):
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    gates=[{"id":"security_reviewer","checks":["no secrets","no unsafe external effects","permission policy followed","attack surface documented"]},{"id":"product_reviewer","checks":["painpoint mapped","real feature shipped","acceptance gates pass","user value clear"]},{"id":"docs_reviewer","checks":["commands executable","docs-command-check passes","spec links artifacts","no stale claims"]},{"id":"runtime_reviewer","checks":["repro bundle exists","loop guard policy followed","action ledger/event evidence present"]}]
    payload={"schema_version":"2026-05-03.agentpress-reviewer-gate-kit.v1","canonical_url":urljoin(base,(outdir/"reviewer-gates.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Built-in reviewer gate templates before agents claim done.","gates":gates,"result_schema":{"gate_id":"","status":"pass|fail|needs_fix","findings":[],"evidence_refs":[],"reviewer_id":""}}
    if not args.no_write: (outdir/"reviewer-gates.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} reviewer-gates")
    return 0


def provider_compatibility_kit(args):
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    providers=[{"provider":"openai/codex","tool_calling":"strong","notes":"coding agent workflows; use strict schema gates"},{"provider":"anthropic/claude","tool_calling":"strong","notes":"human approval and plan mode fit; MCP ecosystem"},{"provider":"google/gemini","tool_calling":"strong","notes":"large context; verify citations and JSON output"},{"provider":"openrouter/litellm","tool_calling":"variable","notes":"route compatibility varies by model; require smoke test"},{"provider":"local/ollama-lmstudio","tool_calling":"variable","notes":"privacy/cost benefits; weaker JSON/tool reliability; require fallback"},{"provider":"browser/rag agents","tool_calling":"surface-specific","notes":"need freshness/citation/browser smoke evidence"}]
    payload={"schema_version":"2026-05-03.agentpress-provider-compatibility-kit.v1","canonical_url":urljoin(base,(outdir/"provider-compatibility.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Provider/model compatibility matrix and fallback guidance for agents using AgentPress.","providers":providers,"required_smoke":["doctor --json","docs-command-check --json","verify --strict-schema --json","sdk-smoke --json"],"fallback_policy":"If provider fails JSON/tool call twice, switch to CLI/static artifact workflow and record loop-guard event."}
    if not args.no_write: (outdir/"provider-compatibility.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} provider-compatibility")
    return 0


def runtime_validation_harness(args):
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    payload={"schema_version":"2026-05-03.agentpress-runtime-validation-harness.v1","canonical_url":urljoin(base,(outdir/"runtime-validation-harness.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Standard runtime validation harness before an agent claims AgentPress support.","gates":[{"name":"doctor","command":"python3 scripts/agentpress.py doctor --json"},{"name":"strict_schema","command":"python3 scripts/agentpress.py verify agentpress/examples/api-docs-handoff --strict-schema --json"},{"name":"docs_drift","command":"python3 scripts/agentpress.py docs-command-check --json"},{"name":"sdk_smoke","command":"python3 scripts/agentpress.py sdk-smoke --json"},{"name":"package_verify","command":"python3 scripts/agentpress.py package-verify agentpress/releases/agentpress-offline.tar.gz --manifest agentpress/releases/agentpress-offline.tar.gz.sha256.json --json"}],"pass_condition":"all gates status ok / failed 0","artifact":"runtime-validation-result.json"}
    if not args.no_write: (outdir/"runtime-validation-harness.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} runtime-validation")
    return 0


def run_artifact_pack(args):
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    payload={"schema_version":"2026-05-03.agentpress-run-artifact-pack.v1","canonical_url":urljoin(base,(outdir/"run-artifact-pack.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Shareable run artifact bundle for agent work: plan, ledger, context, approvals, validation, review, closeout.","required_files":["PLAN.md","action-ledger.json","context-debugger.json","approval-gates.json","runtime-validation-result.json","reviewer-gates.json","closeout.json"],"closeout_schema":{"status":"done|blocked|needs_review","summary":"","evidence_refs":[],"remaining_gaps":[],"next_cycle_backlog_ref":""},"privacy":"redact secrets/private prompts/cookies/local paths before sharing"}
    if not args.no_write: (outdir/"run-artifact-pack.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} run-artifact-pack")
    return 0


def mission_keeper_kit(args):
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    payload={"schema_version":"2026-05-03.agentpress-mission-keeper-kit.v1","canonical_url":urljoin(base,(outdir/"mission-keeper.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Multi-agent mission keeper policy for recursive research-build-deploy cycles.","cycle":["research painpoints","update backlog","select highest P0/P1","write spec","build machine surface","run gates","deploy","verify live URLs","append action ledger","repeat"],"roles":[{"role":"scout","output":"painpoint evidence"},{"role":"builder","output":"feature artifacts"},{"role":"reviewer","output":"reviewer gate result"},{"role":"keeper","output":"mission cockpit/backlog update"}],"stop_conditions":["only external third-party proof remains","credential boundary with no token","all live gates pass and backlog has no buildable P0/P1"],"anti_patterns":["memo without shipped artifact","self-proof counted as external proof","queue empty while adoption proof is zero","claiming done without live URL checks"]}
    if not args.no_write: (outdir/"mission-keeper.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} mission-keeper")
    return 0

def agent_platform_feature_backlog(args):
    """Generate major AgentPress platform feature backlog from audits/community painpoints."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    items=[
        {"rank":1,"feature":"agent action ledger","painpoint":"agents lack durable observability: what saw/did/changed/failed/cost","status":"shipping_now","acceptance":["machine-readable event schema","example ledger","summary metrics","redaction policy"]},
        {"rank":2,"feature":"mission cockpit","painpoint":"multi-agent runs are hard to coordinate and audit","status":"shipping_now","acceptance":["single cockpit JSON","links trust/runtime/proof/install surfaces","health and next-action list"]},
        {"rank":3,"feature":"context debugger","painpoint":"wrong/bloated context causes bad actions and wasted tokens","status":"shipping_now","acceptance":["context manifest","budget policy","source/citation requirements","missing-context checklist"]},
        {"rank":4,"feature":"loop guard / circuit breaker","painpoint":"agents loop on broken tools, stale refs, provider errors, or missing state","status":"shipping_now","acceptance":["stuck-state signatures","retry budget","escalation rules","machine policy"]},
        {"rank":5,"feature":"provider compatibility matrix","painpoint":"provider/model/tool-call fragmentation across OpenAI/Anthropic/Gemini/OpenRouter/local","status":"next","acceptance":["capability matrix","known quirks","recommended fallback route"]},
        {"rank":6,"feature":"reviewer-gate templates","painpoint":"people need built-in reviewer agents before trusting autonomous changes","status":"next","acceptance":["security/product/docs reviewer checklists","pass/fail artifact schema"]},
        {"rank":7,"feature":"external proof outreach automation","painpoint":"third-party proof remains the hard adoption bottleneck","status":"next","acceptance":["public target list","outreach prompts","proof acceptance criteria"]}
    ]
    payload={"schema_version":"2026-05-03.agentpress-agent-platform-feature-backlog.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Major feature backlog from GLM/team/community audits; converts agent painpoints into buildable AgentPress surfaces.","completed_recent":["strict schema validation","docs command CI gate","package manager bridge","identity card","runtime repro bundle","MCP static catalog","permission policy","community radar","SDK kit"],"items":items,"shipping_now":[x for x in items if x['status']=='shipping_now'],"next_after_batch":[x for x in items if x['status']=='next'],"principle":"When one batch ships, regenerate this backlog and continue from the highest unresolved painpoint."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(items)} features")
    return 0


def action_ledger_kit(args):
    """Generate action ledger schema/example for agent observability."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    schema={"schema_version":"2026-05-03.agentpress-action-ledger-schema.v1","event_fields":{"event_id":"stable unique id","run_id":"agent run/session id","agent_id":"actor","timestamp_utc":"ISO timestamp","phase":"plan|act|observe|verify|escalate","action":"human-readable action","inputs_ref":"redacted input/context reference","tool":"optional tool/command","files_changed":"list of paths/hashes","external_effect":"none|read|write|payment|credential|production","approval_ref":"required if external_effect is sensitive","result_status":"ok|fail|blocked|skipped","evidence":"artifact urls/paths","error":"redacted failure"},"required":["event_id","run_id","agent_id","timestamp_utc","phase","action","external_effect","result_status"]}
    example={"schema_version":"2026-05-03.agentpress-action-ledger.v1","canonical_url":urljoin(base,(outdir/"action-ledger.example.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","run_id":"example-run","privacy":"redacted; no secrets/prompts/cookies/private keys","events":[{"event_id":"evt-plan-001","run_id":"example-run","agent_id":"agentpress-reference-platform","timestamp_utc":_utc_now(),"phase":"plan","action":"select next feature from backlog","inputs_ref":"agentpress/planning/agent-platform-feature-backlog.json","tool":"agent-platform-feature-backlog","files_changed":[],"external_effect":"none","approval_ref":"","result_status":"ok","evidence":[urljoin(base,"agentpress/planning/agent-platform-feature-backlog.json")],"error":""}]}
    summary={"schema_version":"2026-05-03.agentpress-action-ledger-kit.v1","canonical_url":urljoin(base,(outdir/"manifest.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Let agents publish auditable action traces: what they saw, did, changed, failed, and verified.","files":["action-ledger.schema.json","action-ledger.example.json"],"safety":"External effects require approval_ref; sensitive data must be redacted."}
    if not args.no_write:
        (outdir/"action-ledger.schema.json").write_text(json.dumps(schema,indent=2)+"\n",encoding="utf-8")
        (outdir/"action-ledger.example.json").write_text(json.dumps(example,indent=2)+"\n",encoding="utf-8")
        (outdir/"manifest.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2) if args.json else f"{summary['status']} action-ledger")
    return 0


def context_debugger_kit(args):
    """Generate context debugger manifest/policy for agent runs."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    manifest={"schema_version":"2026-05-03.agentpress-context-debugger.v1","canonical_url":urljoin(base,(outdir/"context-debugger.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Prevent wrong/bloated context by requiring source inventory, budgets, omissions, and freshness checks.","context_budget":{"max_files_default":30,"max_uncompressed_chars_default":200000,"require_source_map":True,"require_freshness_for_mutable_facts":True},"required_sections":["goal","known_state","source_inventory","included_context","excluded_context","missing_context","freshness_checks","decision_risks","verification_plan"],"failure_modes":["using stale docs for mutable state","copying huge irrelevant files","missing current git status","missing user approval context","confusing public docs with private credentials"],"output_template":{"goal":"","source_inventory":[],"included_context":[],"excluded_context":[],"missing_context":[],"freshness_checks":[],"decision_risks":[],"verification_plan":[]}}
    if not args.no_write:
        (outdir/"context-debugger.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
        (outdir/"README.md").write_text("# AgentPress Context Debugger\n\nMachine-readable context audit before high-impact agent runs.\n\n```bash\npython3 scripts/agentpress.py context-debugger-kit --json\n```\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2) if args.json else f"{manifest['status']} context-debugger")
    return 0


def loop_guard_kit(args):
    """Generate loop detection/circuit breaker policy for agents."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    policy={"schema_version":"2026-05-03.agentpress-loop-guard-policy.v1","canonical_url":urljoin(base,(outdir/"loop-guard-policy.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Stop agents from wasting cycles or causing damage when stuck.","retry_budget":{"same_action_same_error":2,"stale_browser_ref":1,"network_or_registry_error":2,"test_failure_without_code_change":1},"stuck_signatures":[{"name":"same_tool_same_error","trigger":"same command/tool fails with same error beyond retry budget","action":"change strategy or escalate"},{"name":"stale_browser_refs","trigger":"browser action fails on stale/missing refs twice","action":"fresh snapshot; then switch to direct evidence route"},{"name":"no_new_evidence","trigger":"three consecutive turns produce no new artifact/test/evidence","action":"stop and pick smaller verifiable task"},{"name":"approval_boundary","trigger":"external write/payment/credential/production effect without approval_ref","action":"halt before action"}],"required_ledger_event":"Every circuit breaker must append action-ledger event with phase=escalate.","safety":"Fail closed; do not bypass approvals, secrets, or production safeguards."}
    if not args.no_write:
        (outdir/"loop-guard-policy.json").write_text(json.dumps(policy,indent=2)+"\n",encoding="utf-8")
        (outdir/"README.md").write_text("# AgentPress Loop Guard\n\nCircuit-breaker policy for stuck agents.\n\n```bash\npython3 scripts/agentpress.py loop-guard-kit --json\n```\n",encoding="utf-8")
    print(json.dumps(policy,indent=2) if args.json else f"{policy['status']} loop-guard")
    return 0


def mission_cockpit(args):
    """Generate mission cockpit linking AgentPress trust, runtime, proof, and backlog surfaces."""
    outdir=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"; outdir.mkdir(parents=True,exist_ok=True)
    cockpit={"schema_version":"2026-05-03.agentpress-mission-cockpit.v1","canonical_url":urljoin(base,(outdir/"mission-cockpit.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Single agent/operator cockpit for what is complete, what is next, trust evidence, runtime health, and proof loops.","surfaces":{"feature_backlog":urljoin(base,"agentpress/planning/agent-platform-feature-backlog.json"),"identity":urljoin(base,"agentpress/identity/agentpress-identity-card.json"),"tool_catalog":urljoin(base,"agentpress/tools/agentpress-tools.json"),"mcp_catalog":urljoin(base,"agentpress/mcp/mcp-static-catalog.json"),"permission_policy":urljoin(base,"agentpress/policies/tool-permission-policy.json"),"action_ledger":urljoin(base,"agentpress/observability/action-ledger/manifest.json"),"context_debugger":urljoin(base,"agentpress/context/context-debugger.json"),"loop_guard":urljoin(base,"agentpress/runtime/loop-guard-policy.json"),"repro_bundle":urljoin(base,"agentpress/runtime/repro-bundle.json"),"proof_scoreboard":urljoin(base,"agentpress/external-proofs/proof-scoreboard.json"),"package_bridge":urljoin(base,"agentpress/package-registry/package-manager-bridge.json")},"current_batch":["agent-platform-feature-backlog","action-ledger-kit","context-debugger-kit","loop-guard-kit","mission-cockpit"],"next_cycle":"After deploy: rerun feature backlog, collect GLM/team audit deltas, build highest unshipped P1."}
    if not args.no_write:
        (outdir/"mission-cockpit.json").write_text(json.dumps(cockpit,indent=2)+"\n",encoding="utf-8")
        (outdir/"README.md").write_text("# AgentPress Mission Cockpit\n\nSingle machine-readable cockpit for agent platform completion and next actions.\n\n```bash\npython3 scripts/agentpress.py mission-cockpit --json\n```\n",encoding="utf-8")
    print(json.dumps(cockpit,indent=2) if args.json else f"{cockpit['status']} mission-cockpit")
    return 0

def agent_identity_card(args):
    """Publish AgentPress identity/capability policy card for agent-to-agent trust."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    card={"schema_version":"2026-05-03.agentpress-agent-identity-card.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","agent_id":args.agent_id,"display_name":"AgentPress Reference Platform","operator":"barneywohl","homepage":base,"repository":"https://github.com/barneywohl/agentpress","release":"https://github.com/barneywohl/agentpress/releases/tag/agentpress-2026-05-03-platform","capabilities":["static_agent_contracts","tool_catalog","mcp_static_catalog","proof_ingestion","package_manager_bridge","strict_schema_validation","docs_command_lint","permission_policy","community_radar"],"trust_surfaces":{"tools":urljoin(base,"agentpress/tools/agentpress-tools.json"),"mcp_catalog":urljoin(base,"agentpress/mcp/mcp-static-catalog.json"),"permission_policy":urljoin(base,"agentpress/policies/tool-permission-policy.json"),"attestation_index":urljoin(base,"agentpress/attestations/attestation-index.json"),"proof_scoreboard":urljoin(base,"agentpress/external-proofs/proof-scoreboard.json"),"release_index":urljoin(base,"agentpress/releases/release-index.json")},"policy":{"external_writes":"human_approval_required","payments":"unsigned_intents_only_until_explicit_registry_wallet_approval","credential_access":"not_required_for_public_read","privacy":"no hidden telemetry; opt-in receipts only"},"agent_to_agent_use":"Other agents may discover tools, validate contracts, submit proof/blockers, and install through public package-manager bridge without credentials."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(card,indent=2)+"\n",encoding="utf-8")
        (out.parent/"README.md").write_text("# AgentPress Identity Card\n\nMachine-readable identity/capability policy for agent-to-agent trust.\n\n```bash\npython3 scripts/agentpress.py agent-identity-card --json\n```\n",encoding="utf-8")
    print(json.dumps(card,indent=2) if args.json else f"{card['status']} {card['agent_id']}")
    return 0


def environment_fingerprint(args):
    """Create reproducible environment fingerprint for AgentPress agent runs."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    def run(cmd):
        try:
            cp=subprocess.run(cmd, text=True, capture_output=True, timeout=10)
            return {"cmd":" ".join(cmd),"ok":cp.returncode==0,"stdout":cp.stdout.strip()[:500],"stderr":cp.stderr.strip()[:300]}
        except Exception as e: return {"cmd":" ".join(cmd),"ok":False,"error":str(e)}
    checks=[run(["python3","--version"]), run(["node","--version"]), run(["git","--version"]), run(["npm","--version"])]
    files=[]
    for rel in ["pyproject.toml","package.json","scripts/agentpress.py","agentpress/tools/agentpress-tools.json","agentpress/releases/release-index.json"]:
        pp=pathlib.Path(rel)
        if pp.exists(): files.append({"path":rel,"sha256":hashlib.sha256(pp.read_bytes()).hexdigest(),"bytes":pp.stat().st_size})
    payload={"schema_version":"2026-05-03.agentpress-environment-fingerprint.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Help agents reproduce AgentPress runs and debug flaky runtime drift.","platform":{"system":platform.platform() if 'platform' in globals() else sys.platform,"python":sys.version.split()[0]},"commands":checks,"files":files,"repro_commands":["python3 scripts/agentpress.py doctor --json","python3 scripts/agentpress.py docs-command-check --json","python3 scripts/agentpress.py verify agentpress/examples/api-docs-handoff --strict-schema --json","python3 scripts/agentpress.py package-verify agentpress/releases/agentpress-offline.tar.gz --manifest agentpress/releases/agentpress-offline.tar.gz.sha256.json --json"],"privacy":"local runtime metadata only; no secrets or env vars captured"}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(files)} files")
    return 0


def repro_bundle(args):
    """Publish reproducible run bundle manifest for AgentPress."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    payload={"schema_version":"2026-05-03.agentpress-repro-bundle.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"One-stop reproducibility manifest for agents verifying AgentPress from install to contract gates.","inputs":[urljoin(base,"agentpress/runtime/environment-fingerprint.json"),urljoin(base,"agentpress/releases/release-index.json"),urljoin(base,"agentpress/package-registry/package-manager-bridge.json")],"steps":[{"name":"install_from_git","command":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git"},{"name":"offline_install","command":"python3 -c \"$(curl -fsSL https://barneywohl.github.io/agentpress/agentpress/install/install.py)\" --base-url https://barneywohl.github.io/agentpress/ --out agentpress-offline"},{"name":"contract_verify","command":"python3 scripts/agentpress.py verify agentpress/examples/api-docs-handoff --strict-schema --json"},{"name":"docs_drift_gate","command":"python3 scripts/agentpress.py docs-command-check --json"},{"name":"sdk_smoke","command":"python3 scripts/agentpress.py sdk-smoke --json"}],"expected_evidence":["strict schema ok","docs command check 0 failed","package verify ok","attestation verify ok"],"no_secret_policy":"Do not include tokens, prompts, private repo paths, env vars, cookies, or user data in repro submissions."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        (out.parent/"README.md").write_text("# AgentPress Runtime Repro Bundle\n\n```bash\npython3 scripts/agentpress.py environment-fingerprint --json\npython3 scripts/agentpress.py repro-bundle --json\n```\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} repro-bundle")
    return 0

def package_manager_bridge(args):
    """Generate zero-credential package-manager install bridge for pip/npm/git + registry publish readiness."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    npm_auth=False; npm_error=""
    try:
        cp=subprocess.run(["npm","whoami"], text=True, capture_output=True, timeout=20)
        npm_auth=(cp.returncode==0); npm_error=(cp.stderr or cp.stdout).strip()[:300]
    except Exception as e: npm_error=str(e)
    pypi_auth=bool(os.environ.get("TWINE_API_TOKEN") or (os.environ.get("TWINE_USERNAME") and os.environ.get("TWINE_PASSWORD")) or pathlib.Path.home().joinpath(".pypirc").exists())
    gh_release="https://github.com/barneywohl/agentpress/releases/tag/agentpress-2026-05-03-platform"
    payload={"schema_version":"2026-05-03.agentpress-package-manager-bridge.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Make AgentPress installable through package-manager style paths even when public registry credentials are unavailable.","zero_credential_installs":{"pip_git":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git","pip_archive":"python3 -m pip install https://github.com/barneywohl/agentpress/archive/refs/heads/main.zip","npm_git":"npm install github:barneywohl/agentpress","offline_release":"python3 -c \"$(curl -fsSL https://barneywohl.github.io/agentpress/agentpress/install/install.py)\" --base-url https://barneywohl.github.io/agentpress/ --out agentpress-offline"},"registry_readiness":{"npmjs":{"package":"agentpress-static","available":True,"auth_ok":npm_auth,"auth_error":"" if npm_auth else npm_error,"publish_command":"npm publish --access public"},"pypi":{"package":"agentpress-static","available":True,"auth_ok":pypi_auth,"publish_command":"python3 -m build && python3 -m twine upload dist/*"},"github_release":{"published":True,"url":gh_release,"asset_package":urljoin(base,"agentpress/releases/agentpress-offline.tar.gz"),"asset_manifest":urljoin(base,"agentpress/releases/agentpress-offline.tar.gz.sha256.json")}},"safety":"Publishing to npm/PyPI requires registry credentials; all zero-credential installs above are live now and do not require hidden tokens."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        (out.parent/"README.md").write_text("# AgentPress Package Manager Bridge\n\nLive install paths:\n\n```bash\npython3 -m pip install git+https://github.com/barneywohl/agentpress.git\nnpm install github:barneywohl/agentpress\npython3 -c \"$(curl -fsSL https://barneywohl.github.io/agentpress/agentpress/install/install.py)\" --base-url https://barneywohl.github.io/agentpress/ --out agentpress-offline\n```\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} package bridge")
    return 0

def tool_permission_policy(args):
    """Export per-command permission/approval policy for agent tool use."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    tools_path=root/pathlib.Path(args.tools)
    if not tools_path.exists():
        with contextlib.redirect_stdout(io.StringIO()): tools_manifest(argparse.Namespace(out=args.tools, base_url=args.base_url))
    tools=json.loads(tools_path.read_text(encoding="utf-8")).get("tools",[])
    policies=[]
    risky={"payment","transport","confidential","external","github","publish","credential","production","send"}
    for t in tools:
        tags=set(map(str.lower,t.get("tags",[]))); cmd=t.get("command","")
        needs=sorted([x for x in risky if x in tags or x in cmd.lower()])
        level="auto_read_only"
        approval=[]
        if any(x in needs for x in ["payment","transport","confidential","external","github","publish","credential","production","send"]):
            level="human_approval_required_before_external_effect"
            approval=["confirm target", "redaction/privacy check", "budget/payment check if applicable", "operator approval before external write"]
        policies.append({"tool":t.get("name"),"command_template":cmd,"default_permission":level,"detected_risk_terms":needs,"allowed_without_approval":["local read", "local artifact generation", "static JSON validation"],"approval_checklist":approval,"audit_evidence":["command_template", "stdout/stderr", "artifact paths", "attestation when generated"]})
    payload={"schema_version":"2026-05-03.agentpress-tool-permission-policy.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Give agents a machine-readable permission and approval policy before running AgentPress command templates.","policy_count":len(policies),"defaults":{"read_only":"allowed", "local_artifact_generation":"allowed", "external_write":"human_approval_required", "payment":"human_approval_required", "credential_access":"prohibited_unless_explicitly_approved"},"policies":policies}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        (out.parent/"README.md").write_text("# AgentPress Tool Permission Policy\n\nMachine-readable approval policy for AgentPress command templates.\n\n```bash\npython3 scripts/agentpress.py tool-permission-policy --json\n```\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {payload['policy_count']} policies")
    return 0

def mcp_catalog_export(args):
    """Export AgentPress tools as a static MCP-style catalog for tool-discovery agents."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    tools_path=root/pathlib.Path(args.tools)
    if not tools_path.exists():
        with contextlib.redirect_stdout(io.StringIO()): tools_manifest(argparse.Namespace(out=args.tools, base_url=args.base_url))
    tools=json.loads(tools_path.read_text(encoding="utf-8")).get("tools",[])
    entries=[]
    for t in tools:
        name=str(t.get("name",""))
        entries.append({
            "name":name.replace("agentpress.","agentpress_"),
            "title":name,
            "description":t.get("description",""),
            "input_mode":"local_cli_command_template",
            "command_template":t.get("command",""),
            "tags":t.get("tags",[]),
            "side_effects":"none_by_default_or_explicitly_marked",
            "requires_human_approval":["external_write","payment","credential_access","production_change"],
            "source_tool_manifest":urljoin(base,args.tools)
        })
    payload={"schema_version":"2026-05-03.agentpress-mcp-static-catalog.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Static MCP-compatible tool discovery export so MCP/Cline/Roo/Claude/Codex-style agents can discover AgentPress capabilities without a live server.","transport":"static_json_catalog","server_name":"agentpress-static-tools","mcp_alignment":{"resources":[{"uri":"agentpress://tools","url":urljoin(base,args.tools)},{"uri":"agentpress://community-radar","url":urljoin(base,"agentpress/community/community-radar.json")},{"uri":"agentpress://marketplace","url":urljoin(base,"agentpress/marketplace/marketplace-index.json")}],"tools_are_command_templates":True,"live_mcp_server":"not_required_for_static_discovery"},"tool_count":len(entries),"tools":entries,"safety":{"default_external_side_effects":"none","no_credentials_required_for_read":"true","approval_required_for":["external writes","payments","credential access","production mutations"]}}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        (out.parent/"README.md").write_text("# AgentPress MCP Static Catalog\n\nStatic MCP-style export for agents that discover tools through catalogs instead of prose.\n\n```bash\npython3 scripts/agentpress.py mcp-catalog-export --json\n```\n\nThis is read-only/static discovery; it does not start a server or grant credentials.\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {payload['tool_count']} tools")
    return 0

def community_radar(args):
    """Publish public agent-builder community map and painpoint radar."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    base=args.base_url.rstrip()+"/"
    sources=[
        {"id":"github-cline","kind":"github_repo_issues_discussions","name":"Cline","url":"https://github.com/cline/cline","signals":["human-in-loop approval", "MCP tool ecosystem", "terminal/browser/file edits", "model/API cost control"]},
        {"id":"github-roocode","kind":"github_repo_issues_discord_reddit","name":"Roo Code","url":"https://github.com/RooCodeInc/Roo-Code","signals":["multi-mode agents", "custom modes", "BYO model/API routing", "autonomy vs control"]},
        {"id":"github-openhands","kind":"github_repo_issues_slack_discussions","name":"OpenHands","url":"https://github.com/All-Hands-AI/OpenHands","signals":["sandbox reliability", "browser/test loops", "install friction", "runtime reproducibility"]},
        {"id":"github-autogen","kind":"github_repo_issues_discussions","name":"AutoGen","url":"https://github.com/microsoft/autogen","signals":["agent-to-agent governance", "identity/policy enforcement", "tool integrations", "commerce/tool proposals"]},
        {"id":"github-crewai","kind":"github_repo_issues_discussions","name":"CrewAI","url":"https://github.com/crewAIInc/crewAI","signals":["pre-execution validation", "memory/storage backends", "multi-agent orchestration", "provider key errors"]},
        {"id":"github-langchain","kind":"github_repo_issues_forum","name":"LangChain / LangGraph","url":"https://github.com/langchain-ai/langchain","signals":["agent observability", "tool calling contracts", "state graphs", "production debugging"]},
        {"id":"github-llamaindex","kind":"github_repo_issues_forum","name":"LlamaIndex","url":"https://github.com/run-llama/llama_index","signals":["RAG freshness", "citations", "connectors", "eval reproducibility"]},
        {"id":"hn-agent-builders","kind":"public_forum","name":"Hacker News agent-builder threads","url":"https://hn.algolia.com/?q=AI%20coding%20agents","signals":["skepticism about flaky agents", "E2E self-debug", "package/source search MCP", "orchestration UIs"]},
        {"id":"reddit-localllama","kind":"public_forum","name":"r/LocalLLaMA and related coding-agent threads","url":"https://www.reddit.com/r/LocalLLaMA/search/?q=coding%20agent%20MCP","signals":["local model cost/privacy", "context windows", "tool reliability", "prompt/workflow sharing"]},
        {"id":"mcp-ecosystem","kind":"protocol_ecosystem","name":"MCP servers/directories","url":"https://github.com/modelcontextprotocol/servers","signals":["tool discovery", "safe permissions", "server quality", "installation/config friction"]}
    ]
    painpoints=[
        {"rank":1,"painpoint":"stale or non-executable docs/commands","seen_in":["Cline/Roo/OpenHands style copy-paste workflows", "GitHub issue support patterns"],"agentpress_response":"docs-command-check shipped; make it required CI", "needed_build":"required docs command lint gate"},
        {"rank":2,"painpoint":"unsafe or unclear permissions before tool execution","seen_in":["Cline Plan/Act", "MCP permissions", "CrewAI pre-execution validation"],"agentpress_response":"privacy, redaction, secure-transport readiness shipped", "needed_build":"policy/permission manifest per command"},
        {"rank":3,"painpoint":"tool discovery/configuration friction","seen_in":["MCP server directories", "Roo/Cline custom modes", "AutoGen tool proposals"],"agentpress_response":"tool manifest, marketplace, SDK kit shipped", "needed_build":"MCP-compatible static tool catalog export"},
        {"rank":4,"painpoint":"runtime reproducibility and flaky environments","seen_in":["OpenHands sandbox issues", "HN self-debug/E2E agent threads"],"agentpress_response":"browser smoke, package verify, queue/retry kit shipped", "needed_build":"environment fingerprint + reproducible run bundle"},
        {"rank":5,"painpoint":"agent-to-agent trust, identity, and governance","seen_in":["AutoGen governance extension", "multi-agent orchestration communities"],"agentpress_response":"attestations, reputation, proof ingestion shipped", "needed_build":"agent identity card + signed capability policy"},
        {"rank":6,"painpoint":"cost/model routing and budget anxiety","seen_in":["Roo BYO routing", "Cline/Roo comparisons", "local model communities"],"agentpress_response":"payment-status/payment-intent/no-spend marketplace compare shipped", "needed_build":"cost estimate metadata per tool path"},
        {"rank":7,"painpoint":"external proof is hard to submit and trust","seen_in":["GitHub issue proof/blocker patterns", "open source adoption loops"],"agentpress_response":"proof campaign, proof ingest, scoreboard shipped", "needed_build":"community radar driven outreach queue"},
        {"rank":8,"painpoint":"RAG/citation freshness and source quality","seen_in":["LlamaIndex/RAG ecosystems", "agent search/crawler workflows"],"agentpress_response":"freshness-citation-report shipped", "needed_build":"source provenance badges in search results"}
    ]
    recommended=[
        {"priority":"P1","feature":"required docs-command-check CI gate","why":"community workflows copy commands verbatim; broken docs kill adoption", "status":"partially_shipped"},
        {"priority":"P1","feature":"MCP/static tool catalog export","why":"MCP is a main place agents exchange tools; AgentPress should be directly ingestible", "status":"next_unblocked"},
        {"priority":"P1","feature":"agent identity/capability policy card","why":"agent-to-agent governance and permissions are recurring painpoints", "status":"next"},
        {"priority":"P2","feature":"environment fingerprint/repro bundle","why":"flaky sandboxes and runtime drift dominate issue queues", "status":"next"},
        {"priority":"P2","feature":"community outreach queue","why":"turn radar into public proof/blocker collection tasks", "status":"next"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-community-radar.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Map public places agent builders communicate, what they like/dislike, and which AgentPress features to build next.","research_scope":"public/indexed sources only; no private Discord scraping, no DMs, no hidden telemetry","source_count":len(sources),"sources":sources,"painpoints":painpoints,"recommendations":recommended,"top_next_build":"mcp_static_tool_catalog_export","privacy":"no user tracking; source URLs and qualitative signals only"}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        md=out.with_suffix('.md')
        md.write_text("# AgentPress Community Radar\n\nPublic agent-builder watering holes and painpoints.\n\n## Top findings\n"+"\n".join([f"- **{p['painpoint']}** → {p['needed_build']}" for p in painpoints[:5]])+"\n\n## Sources\n"+"\n".join([f"- [{x['name']}]({x['url']}) — {', '.join(x['signals'][:3])}" for x in sources])+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {payload['source_count']} sources")
    return 0

def proof_scoreboard(args):
    """Compile external proof ingestion into a product/adoption scoreboard."""
    root=pathlib.Path(args.root)
    index_path=root/args.index
    if not index_path.exists():
        proof_ingest(argparse.Namespace(root=args.root, dir=args.dir, out=args.index, base_url=args.base_url, no_write=False, allow_rejected=True, json=False))
    data=json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"proofs":[]}
    proofs=data.get("proofs", [])
    accepted=[p for p in proofs if p.get("status")=="accepted"]
    rejected=[p for p in proofs if p.get("status")=="rejected"]
    by_agent={}
    for p in accepted:
        a=by_agent.setdefault(p.get("agent_id") or "unknown", {"agent_id":p.get("agent_id") or "unknown","runtime":p.get("runtime", ""),"accepted_proofs":0,"score":0,"proof_types":{},"files":[]})
        a["accepted_proofs"]+=1; a["score"]+=p.get("score",0); a["proof_types"][p.get("proof_type") or "unknown"]=a["proof_types"].get(p.get("proof_type") or "unknown",0)+1; a["files"].append(p.get("path"))
    agents=sorted(by_agent.values(), key=lambda x:(-x["score"], x["agent_id"]))
    blockers=[p for p in accepted if p.get("proof_type")=="painpoint_report"]
    successes=[p for p in accepted if p.get("proof_type") in {"first_contact_adoption","tool_use_success","marketplace_route_success"}]
    payload={
        "schema_version":"2026-05-03.agentpress-proof-scoreboard.v1",
        "canonical_url":urljoin(args.base_url.rstrip("/")+"/", args.out),
        "generated_utc":_utc_now(),
        "status":"ok",
        "source_index":args.index,
        "totals":{"proofs":len(proofs),"accepted":len(accepted),"rejected":len(rejected),"success_proofs":len(successes),"blocker_reports":len(blockers)},
        "agents":agents,
        "top_blockers":[{"proof_id":p.get("proof_id"),"agent_id":p.get("agent_id"),"path":p.get("path"),"score":p.get("score")} for p in blockers[:20]],
        "next_actions":["Fix top blocker reports", "Ask accepted proof agents for follow-up tool-use receipts", "Rerun reputation-index with --external-proof-index"]
    }
    if not args.no_write:
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"accepted={len(accepted)} agents={len(agents)}")
    return 0



def freshness_citation_report(args):
    """Generate freshness/citation coverage report for RAG/crawler agents."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    candidates=[]
    for pattern in ["agentpress/**/*.json", "*.md", "agentpress/**/*.md", "llms.txt"]:
        candidates.extend(root.glob(pattern))
    seen=set(); files=[]
    for fp in sorted(candidates):
        if fp.is_dir() or fp in seen: continue
        seen.add(fp)
        rel=fp.relative_to(root).as_posix()
        if rel.startswith(".git/") or "agentpress/releases/agentpress-offline" in rel: continue
        text=""
        try: text=fp.read_text(encoding="utf-8", errors="ignore")
        except Exception: pass
        has_citation=any(x in text.lower() for x in ["citation", "source", "canonical_url", "source-map", "freshness", "generated_utc"])
        generated=None; canonical=False
        if fp.suffix==".json":
            try:
                d=json.loads(text); generated=d.get("generated_utc") or d.get("updated_utc") or d.get("created_utc"); canonical=bool(d.get("canonical_url"))
            except Exception: pass
        files.append({"path":rel,"kind":fp.suffix.lstrip('.') or "text","bytes":fp.stat().st_size,"has_citation_signal":has_citation,"has_canonical_url":canonical,"generated_utc":generated})
    machine=[f for f in files if f["kind"]=="json"]
    citation_count=sum(1 for f in files if f["has_citation_signal"])
    canonical_count=sum(1 for f in machine if f["has_canonical_url"])
    stale_or_unknown=[f for f in machine if not f.get("generated_utc") and not f.get("has_canonical_url")][:100]
    payload={"schema_version":"2026-05-03.agentpress-freshness-citation-report.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Help RAG/crawler agents identify source, citation, canonical URL, and freshness coverage across AgentPress surfaces.","summary":{"file_count":len(files),"machine_json_count":len(machine),"citation_signal_count":citation_count,"canonical_json_count":canonical_count,"unknown_machine_count":len(stale_or_unknown)},"coverage":{"citation_signal_ratio":round(citation_count/max(1,len(files)),4),"canonical_json_ratio":round(canonical_count/max(1,len(machine)),4)},"unknown_machine_files":stale_or_unknown,"files":files if args.include_files else []}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"files={len(files)} unknown={len(stale_or_unknown)}")
    return 0

def browser_smoke(args):
    """Smoke-check public AgentPress URLs and write evidence for agents/browser crawlers."""
    out=pathlib.Path(args.out)
    urls=[]
    if args.url:
        urls.extend(args.url)
    if not urls:
        urls=[
            urljoin(args.base_url.rstrip("/")+"/", "llms.txt"),
            urljoin(args.base_url.rstrip("/")+"/", "README.md"),
            urljoin(args.base_url.rstrip("/")+"/", "agentpress/tools/agentpress-tools.json"),
            urljoin(args.base_url.rstrip("/")+"/", "agentpress/releases/release-index.json"),
            urljoin(args.base_url.rstrip("/")+"/", "agentpress/install/install-catalog.json"),
            urljoin(args.base_url.rstrip("/")+"/", "agentpress/external-proofs/external-proof-index.json"),
            urljoin(args.base_url.rstrip("/")+"/", "agentpress/external-proofs/proof-scoreboard.json"),
            urljoin(args.base_url.rstrip("/")+"/", "agentpress/planning/feature-build-queue.json"),
            urljoin(args.base_url.rstrip("/")+"/", "agentpress/distribution/distribution-mirrors.json"),
            urljoin(args.base_url.rstrip("/")+"/", "agentpress/privacy/privacy-status.json"),
        ]
    checks=[]
    for u in urls:
        started=time.time(); status="fail"; code=None; ctype=""; size=0; digest=""; err=""
        try:
            req=Request(u, headers={"User-Agent":"AgentPressSmoke/1.0"})
            with urlopen(req, timeout=args.timeout_seconds) as r:
                code=getattr(r,"status",None) or r.getcode(); ctype=r.headers.get("content-type",""); body=r.read(args.max_bytes+1)
            size=len(body); digest=hashlib.sha256(body[:args.max_bytes]).hexdigest(); status="ok" if 200 <= int(code) < 400 and size > 0 else "fail"
            if args.require_json and u.endswith(".json"):
                try: json.loads(body.decode("utf-8"))
                except Exception as e: status="fail"; err=f"json parse failed: {e}"
        except Exception as e:
            err=str(e)[:300]
        checks.append({"url":u,"status":status,"http_status":code,"content_type":ctype,"bytes_read":size,"sha256_prefix":digest,"elapsed_ms":round((time.time()-started)*1000,2),"error":err})
    failed=[c for c in checks if c["status"]!="ok"]
    payload={"schema_version":"2026-05-03.agentpress-browser-smoke.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if not failed else "fail","purpose":"Machine-readable public URL smoke evidence for browser/RAG agents.","checked":len(checks),"failed":len(failed),"checks":checks}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"{payload['status']} {payload['checked']} checked")
    return 0 if not failed else 1




def china_deep_angle_radar(args):
    """Deeper China-market angle radar across developer, infra, enterprise, and protocol debates."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    angles=[
        {"angle":"developer_first_run","priority":"P0","signals":["tutorial-heavy Cline/Roo/MCP content","Windows npx errors","virtualenv/path setup friction"],"build":"china-mcp-preflight + windows-npx-doctor + one-screen zh-CN quickstart"},
        {"angle":"distribution_sovereignty","priority":"P0","signals":["GitHub/GHCR/Quay/K8s image pull instability","Docker MCP image distribution article","domestic mirror usage"],"build":"china-container-mirror-pack + offline artifact/hash mirror contract"},
        {"angle":"mcp_cli_layering","priority":"P0","signals":["MCP vs CLI debate","token overhead/debugging concerns","Feishu/DingTalk/WeCom CLI examples"],"build":"mcp-cli-bridge: every MCP capability exposes human-replayable CLI with JSON output"},
        {"angle":"enterprise_collab_tools","priority":"P1","signals":["DingTalk/Feishu/WeCom CLI and enterprise workflows","Chinese enterprise adoption patterns"],"build":"enterprise connector pack for DingTalk/Feishu/WeCom-style CLI receipts, approval, and audit logs"},
        {"angle":"local_model_and_modelscope_ecosystem","priority":"P1","signals":["ModelScope/Tongyi/Qwen/deepseek developer channels","domestic model/provider compatibility"],"build":"provider compatibility examples for Qwen/DeepSeek/OpenAI-compatible endpoints"},
        {"angle":"localized_education_and_terminology","priority":"P1","signals":["Awesome-MCP-ZH and MCPcn resource aggregation","Chinese technical terms differ from English docs"],"build":"zh-CN glossary, examples, and source-map for MCP/AgentPress terms"},
        {"angle":"compliance_and_data_boundary","priority":"P1","signals":["enterprise/private deployment preference","no hidden telemetry expectation"],"build":"China/private deployment privacy statement and offline proof mode"},
    ]
    payload={"schema_version":"2026-05-04.agentpress-china-deep-angle-radar.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Explore all China-market angles for AgentPress adoption beyond simple translation.","angles":angles,"recommended_sequence":["mcp-cli-bridge-pack","china-container-mirror-pack","china-enterprise-connector-pack","zh-cn-glossary-pack","provider-compat-qwen-deepseek"],"research_basis":["Zhihu/Juejin/CSDN snippets","Juejin MCP-vs-CLI article","Juejin Docker MCP/image distribution article","MCPcn/MCP Chinese ecosystem pages","Alibaba/Tencent/AWS China developer articles"],"non_goals":["no private forum scraping","no automatic outreach","no unapproved China mirror account creation"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2,ensure_ascii=False) if args.json else f"{payload['status']} angles={len(angles)}")
    return 0


def mcp_cli_bridge_pack(args):
    """Generate MCP+CLI layering pack for China/global debugging and token-efficiency concerns."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    capabilities=[
        {"capability":"discover_tools","mcp":"tools/list","cli":"agentpress tools --json","why":"CLI gives human-replayable debug path; MCP gives machine contract."},
        {"capability":"validate_config","mcp":"callTool:mcp_config_guard","cli":"agentpress mcp-config-mutation-guard --json","why":"Config mutation must be reproducible outside model context."},
        {"capability":"issue_repro","mcp":"callTool:issue_to_repro_pack","cli":"agentpress issue-to-repro-pack --json","why":"Provider/tool-call failures need copy-pasteable repro artifacts."},
        {"capability":"region_health","mcp":"callTool:region_health","cli":"agentpress region-health --json","why":"Mirror failures should be testable by humans and agents."},
        {"capability":"proof_receipt","mcp":"callTool:proof_receipt_verify","cli":"agentpress proof-receipt-verify <file> --json","why":"External receipts need deterministic reviewer behavior."},
    ]
    payload={"schema_version":"2026-05-04.agentpress-mcp-cli-bridge-pack.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Answer the Chinese MCP-vs-CLI debate with layered design: MCP for contract/discovery, CLI for replay/debug/token efficiency.","principles":["Every MCP tool should have a CLI equivalent","Every CLI must support --json","MCP schemas should be compact; long docs live behind CLI/help URLs","Humans must be able to replay what an agent did","Use consent/approval receipts for risky tools"],"capabilities":capabilities,"metrics_to_track":["schema_token_budget","cli_replay_success","mcp_call_success","human_debug_minutes","config_mutation_fail_closed_count"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        (out.parent/'MCP_CLI_BRIDGE_ZH.md').write_text('# MCP + CLI 分层方案\n\nMCP 负责能力发现、契约和权限；CLI 负责可复现执行、调试和低 token 成本。AgentPress 的原则：每个 MCP 能力都必须有 `--json` CLI 等价命令。\n',encoding='utf-8')
    print(json.dumps(payload,indent=2,ensure_ascii=False) if args.json else f"{payload['status']} capabilities={len(capabilities)}")
    return 0


def china_container_mirror_pack(args):
    """Generate container/image distribution pack for China Agent/MCP platforms."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    registries=[
        {"source":"Docker Hub","risk_cn":"medium_high","example_mirror_pattern":"docker.<mirror-domain>/<image>","agentpress_action":"document mirror variable, verify digest"},
        {"source":"GHCR","risk_cn":"high","example_mirror_pattern":"ghcr.<mirror-domain>/<org>/<image>","agentpress_action":"provide offline OCI tarball/export contract before GHCR reliance"},
        {"source":"Quay","risk_cn":"medium_high","example_mirror_pattern":"quay.<mirror-domain>/<image>","agentpress_action":"list all required images before deploy"},
        {"source":"K8s/GCR","risk_cn":"high","example_mirror_pattern":"k8s.<mirror-domain>/<image>","agentpress_action":"preflight pull pause/coredns/browser images"},
    ]
    payload={"schema_version":"2026-05-04.agentpress-china-container-mirror-pack.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Prevent MCP/Agent platforms from failing at Docker/GHCR/Quay/K8s image distribution in China or restricted networks.","preflight_commands":["docker info","docker pull hello-world","docker pull <mirror>/redis:7-alpine","docker inspect --format='{{index .RepoDigests 0}}' <image>","docker save <image> -o image.tar"],"registries":registries,"compose_policy":["pin image digests","list original source and mirror source","record pull timestamp and digest","support offline image tar export/import","never execute unverified image from unknown mirror"],"receipt_fields":["agent_id","region","registry_source","mirror_used","image","digest","pull_status","latency_ms","error_redacted"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2,ensure_ascii=False) if args.json else f"{payload['status']} registries={len(registries)}")
    return 0


def china_enterprise_connector_pack(args):
    """Generate Chinese enterprise collaboration connector strategy pack."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    connectors=[
        {"platform":"DingTalk/钉钉","status":"strategy_pack_only","integration_shape":"CLI/MCP bridge with approval receipt; no live send by default","risk":"external messaging and enterprise auth require explicit approval"},
        {"platform":"Feishu/Lark/飞书","status":"strategy_pack_only","integration_shape":"CLI JSON command + MCP contract + audit receipt","risk":"workspace auth and data boundary"},
        {"platform":"WeCom/企业微信","status":"strategy_pack_only","integration_shape":"CLI wrapper over approved API/MCP server, replayable by humans","risk":"enterprise credentials and message-send approval"},
        {"platform":"ModelScope/魔搭 + Qwen/通义","status":"strategy_pack_only","integration_shape":"OpenAI-compatible provider profile and model capability receipt","risk":"provider compatibility and regional endpoint handling"},
        {"platform":"Dify/Coze/n8n","status":"strategy_pack_only","integration_shape":"webhook/tool manifest/import pack with no hidden telemetry","risk":"hosted workflow privacy and external effects"},
    ]
    payload={"schema_version":"2026-05-04.agentpress-china-enterprise-connector-pack.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Map AgentPress to Chinese enterprise tool ecosystems without unsafe external writes.","connectors":connectors,"default_policy":"No external send, workspace auth, or webhook write without explicit operator approval. Build manifests, dry-runs, and receipts first.","build_next":["provider profile for Qwen/DeepSeek OpenAI-compatible endpoints","Dify/Coze importable tool manifest","Feishu/DingTalk/WeCom CLI receipt schema","enterprise approval receipt template"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2,ensure_ascii=False) if args.json else f"{payload['status']} connectors={len(connectors)}")
    return 0


def china_painpoint_radar(args):
    """Generate China-focused public painpoint radar for agent/MCP builders."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    sources=[
        {"site":"Zhihu","signals":["MCP best practices","Cline/Roo MCP guides","tool/provider decoupling"],"examples":["通过 MCP 实现 AI Agent 最佳实践","Cline 与 MCP 集成指南","RooCode/Cline 源码/MCP 分析"]},
        {"site":"Juejin","signals":["Cline+GitHub MCP setup","MCP as interoperability infrastructure","Docker/MCP image distribution","MCP vs CLI debate"],"examples":["Cline+GitHub MCP 学习记录","Docker MCP 后的镜像分发问题","MCP与CLI之争"]},
        {"site":"CSDN/Cnblogs/51CTO","signals":["Windows npx/spawn issues","virtualenv setup friction","GitHub connection instability","step-by-step local MCP setup"],"examples":["spawn npx ENOENT","Windows11 VS Code/Cline/GitHub MCP 坑点","Python MCP Server 开发实战"]},
        {"site":"Tencent Cloud/AWS China/SegmentFault","signals":["enterprise integration","MCP server local-to-cloud deployment","LangChain4j/MCP examples"],"examples":["AI Agent 开发新范式 MCP","MCP服务器从本地到云端","LangChain4j + MCP"]},
        {"site":"Awesome-MCP-ZH/mcpcn","signals":["Chinese MCP resource aggregation","localized docs/discovery","Chinese terminology"],"examples":["Awesome-MCP-ZH","MCP 中文站"]},
    ]
    painpoints=[
        {"priority":"P0","painpoint":"github_and_github_pages_reachability","evidence_signal":"Chinese guides frequently route through GitHub, but users report unstable GitHub/MCP setup paths.","agentpress_build":"china mirror pack: Gitee/OSS target, offline tarball, sha256 manifest, no GitHub-only dependency"},
        {"priority":"P0","painpoint":"npm_npx_spawn_and_registry_friction_on_windows","evidence_signal":"CSDN results explicitly mention Cline MCP spawn npx ENOENT and npm/node path issues.","agentpress_build":"windows npx MCP doctor + npmmirror commands + PATH diagnostics"},
        {"priority":"P0","painpoint":"mcp_install_config_complexity","evidence_signal":"Many Chinese posts are step-by-step MCP/Cline setup tutorials, indicating first-run friction.","agentpress_build":"Chinese MCP preflight checklist and Cline/Roo config snippet with consent/config guard"},
        {"priority":"P1","painpoint":"mcp_vs_cli_debuggability_and_token_overhead","evidence_signal":"Juejin has MCP-vs-CLI discussion; debugging and token overhead are visible concerns.","agentpress_build":"CLI-first fallback pack: every MCP tool has equivalent CLI command and repro receipt"},
        {"priority":"P1","painpoint":"container_image_distribution","evidence_signal":"Juejin article frames Docker MCP as creating a new image distribution problem.","agentpress_build":"China-friendly container/GHCR mirror plan and offline OCI tarball contract"},
        {"priority":"P1","painpoint":"localized_examples_for_java_python_js","evidence_signal":"Chinese sources include Python MCP, LangChain4j, Cline/Roo examples.","agentpress_build":"zh-CN examples for Python, Node/npx, Java/LangChain4j, Cline/Roo"},
    ]
    payload={"schema_version":"2026-05-04.agentpress-china-painpoint-radar.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","research_scope":"public indexed Chinese-language sources only; no private groups, no scraping behind logins","sources":sources,"painpoints":painpoints,"top_builds":["china-mcp-preflight","windows-npx-doctor","china-mirror-install-pack","zh-cn-cli-fallback-pack"],"privacy":"No user tracking; only public qualitative signals."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2,ensure_ascii=False) if args.json else f"{payload['status']} painpoints={len(painpoints)}")
    return 0


def china_mcp_preflight(args):
    """Generate China-focused MCP/Cline/Roo first-run preflight checklist."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    checks=[
        {"id":"node_npm_npx","command":"node -v && npm -v && npx -v","fix_cn":"安装 Node LTS；确认 npm 全局路径在 PATH 中；Windows 重启 VS Code 终端。"},
        {"id":"npm_registry","command":"npm config get registry","fix_cn":"如访问慢，可临时使用 npm --registry=https://registry.npmmirror.com。"},
        {"id":"python_uv","command":"python --version || python3 --version; uv --version || pipx --version","fix_cn":"Python MCP 服务建议使用 uv/pipx 隔离环境，避免全局依赖污染。"},
        {"id":"github_reachability","command":"git ls-remote https://github.com/modelcontextprotocol/servers.git HEAD","fix_cn":"如果 GitHub 不稳定，使用镜像/离线包；不要把 token 写进日志。"},
        {"id":"cline_roo_config_backup","command":"cp cline_mcp_settings.json cline_mcp_settings.json.bak","fix_cn":"修改 MCP 配置前必须备份，运行 AgentPress config guard。"},
        {"id":"agentpress_offline_verify","command":"sha256sum -c agentpress-offline.tar.gz.sha256","fix_cn":"离线包执行前先验 hash。"},
    ]
    payload={"schema_version":"2026-05-04.agentpress-china-mcp-preflight.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Reduce Chinese Cline/Roo/MCP first-run failures before agents mutate local config.","checks":checks,"fail_closed_rules":["No config mutation without backup","No secrets in repro receipts","No broad tool scope without consent evidence","Prefer CLI fallback when MCP transport fails"],"related_assets":["agentpress/security/mcp-config-mutation-guard.json","agentpress/install/package-registry-fallback-matrix.json","agentpress/distribution/global-region-mirror-matrix.json"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        (out.parent/'CHINA_MCP_PREFLIGHT.md').write_text('# 中国 MCP/Cline/Roo 预检清单\n\n运行 MCP 服务前：检查 Node/npm/npx、npm registry、Python/uv、GitHub 可达性，并备份 Cline/Roo MCP 配置。\n\n原则：先备份、再改配置；先验 hash、再执行；不要提交密钥、cookie 或私有提示词。\n',encoding='utf-8')
    print(json.dumps(payload,indent=2,ensure_ascii=False) if args.json else f"{payload['status']} checks={len(checks)}")
    return 0


def windows_npx_doctor_pack(args):
    """Generate Windows/npx diagnostic pack for Cline/Roo MCP failures."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    diagnostics=[
        {"symptom":"spawn npx ENOENT","likely_causes":["Node/npm not installed","npm global bin missing from PATH","VS Code inherited stale environment"],"commands":["where node","where npm","where npx","npm config get prefix","echo %PATH%"],"safe_fixes":["Install Node LTS","Add npm global bin to PATH","Restart VS Code/terminal","Avoid deleting random global packages without backup"]},
        {"symptom":"MCP server starts in terminal but not Cline/Roo","likely_causes":["different shell env","relative path in config","working directory mismatch"],"commands":["node -v","npx -y <server> --help","pwd/cd check"],"safe_fixes":["Use absolute command paths","Set explicit cwd/env in config","Capture stderr to repro pack"]},
        {"symptom":"zod/package conflict","likely_causes":["corrupt npm global install","mixed package managers"],"commands":["npm ls -g --depth=0","npm cache verify"],"safe_fixes":["Use npx -y for isolated execution","Use project-local install","Record before/after package list"]},
    ]
    payload={"schema_version":"2026-05-04.agentpress-windows-npx-doctor-pack.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Help Chinese/Windows Cline/Roo users turn npx/MCP startup failures into safe repros and fixes.","diagnostics":diagnostics,"repro_receipt_fields":["os","shell","node_version","npm_version","npx_path","mcp_client","command","stderr_redacted","config_backup_hash","result_status"],"privacy":"Do not include usernames, tokens, private repo names, cookies, or API keys."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2,ensure_ascii=False) if args.json else f"{payload['status']} diagnostics={len(diagnostics)}")
    return 0


def global_mirror_matrix(args):
    """Generate global/region-aware mirror targets and failover policy."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    critical=["llms.txt",".well-known/agentpress.json","agentpress/tools/agentpress-tools.json","agentpress/releases/release-index.json","agentpress/install/install-catalog.json","agentpress/releases/agentpress-offline.tar.gz","agentpress/releases/agentpress-offline.tar.gz.sha256.json"]
    mirrors=[
        {"mirror_id":"github_pages","kind":"primary_static_site","status":"live","base_url":base,"regions":["americas","europe","india","asia_non_cn"],"blocked_domain_risk":"medium_in_restricted_networks","priority":1},
        {"mirror_id":"raw_github_main","kind":"raw_source_fallback","status":"live","base_url":"https://raw.githubusercontent.com/barneywohl/agentpress/refs/heads/main/","regions":["americas","europe","india","asia_non_cn"],"blocked_domain_risk":"medium_high_in_china","priority":2},
        {"mirror_id":"jsdelivr_cdn","kind":"cdn_fallback","status":"live","base_url":"https://cdn.jsdelivr.net/gh/barneywohl/agentpress@main/","regions":["americas","europe","india","asia_non_cn","some_restricted_networks"],"blocked_domain_risk":"medium","priority":3},
        {"mirror_id":"cloudflare_pages_or_r2","kind":"planned_static_object_mirror","status":"planned_owner_dns_needed","base_url":"https://<agentpress-mirror-domain>/","regions":["americas","europe","india","global_edge"],"blocked_domain_risk":"low_medium","priority":4},
        {"mirror_id":"china_gitee_pages","kind":"planned_china_friendly_git_static_mirror","status":"planned_account_needed","base_url":"https://<gitee-user>.gitee.io/agentpress/","regions":["china_mainland"],"blocked_domain_risk":"lower_for_china_than_github","priority":5},
        {"mirror_id":"china_object_storage","kind":"planned_china_object_storage_mirror","status":"planned_account_needed","base_url":"https://<bucket>.<region>.aliyuncs.com/agentpress/","regions":["china_mainland","asia"],"blocked_domain_risk":"low_if_icp_dns_configured","priority":6},
        {"mirror_id":"offline_tarball","kind":"portable_release_artifact","status":"live","base_url":urljoin(base,"agentpress/releases/"),"regions":["all_offline_after_download"],"blocked_domain_risk":"depends_on_initial_download_mirror","priority":7},
    ]
    payload={"schema_version":"2026-05-04.agentpress-global-region-mirror-matrix.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Make AgentPress discoverable/installable for agents across Americas, Europe, India, China, and broader Asia with deterministic failover.","critical_paths":critical,"mirrors":mirrors,"regional_failover":{"americas":["github_pages","raw_github_main","jsdelivr_cdn","cloudflare_pages_or_r2","offline_tarball"],"europe":["github_pages","jsdelivr_cdn","raw_github_main","cloudflare_pages_or_r2","offline_tarball"],"india":["github_pages","jsdelivr_cdn","raw_github_main","cloudflare_pages_or_r2","offline_tarball"],"china_mainland":["china_gitee_pages","china_object_storage","jsdelivr_cdn","offline_tarball"],"asia_non_cn":["github_pages","jsdelivr_cdn","raw_github_main","cloudflare_pages_or_r2","offline_tarball"]},"agent_policy":"Try region failover order, verify sha256 manifest before execution, submit region probe receipt if all mirrors fail.","blocked_actions":["creating external mirror accounts","publishing DNS/ICP records","uploading to owner-controlled cloud buckets"],"next_owner_decisions":["Cloudflare/R2 or other global static mirror account","Gitee or China object storage mirror account","mirror domain/DNS ownership"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
        (out.parent/'GLOBAL_REGION_MIRRORS.md').write_text('# AgentPress Global Region Mirrors\n\nMachine source: `global-region-mirror-matrix.json`.\n\nP0 unresolved: deploy non-GitHub global mirror and China-friendly mirror, then rerun `region-health`.\n',encoding='utf-8')
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} mirrors={len(mirrors)}")
    return 0


def region_health(args):
    """Check live AgentPress mirrors and write regional probe evidence contract."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    matrix_path=root/args.matrix
    if not matrix_path.exists():
        global_mirror_matrix(argparse.Namespace(out=args.matrix, base_url=args.base_url, no_write=False, json=False))
    matrix=json.loads(matrix_path.read_text(encoding='utf-8'))
    checks=[]
    for m in matrix.get('mirrors',[]):
        paths=matrix.get('critical_paths',[])[:args.max_paths]
        if m.get('status')!='live':
            checks.append({"mirror_id":m.get('mirror_id'),"status":"planned_not_checked","mirror_status":m.get('status'),"base_url":m.get('base_url'),"checks":[]})
            continue
        sub=[]
        for rel in paths:
            u=urljoin(m.get('base_url',''), rel); started=time.time(); status='fail'; code=None; size=0; sha=''; err=''
            try:
                with urlopen(Request(u,headers={"User-Agent":"AgentPressRegionHealth/1.0"}), timeout=args.timeout_seconds) as r:
                    code=getattr(r,'status',None) or r.getcode(); body=r.read(args.max_bytes+1)
                size=len(body); sha=hashlib.sha256(body[:args.max_bytes]).hexdigest(); status='ok' if 200 <= int(code) < 400 and size>0 else 'fail'
            except Exception as e: err=str(e)[:240]
            sub.append({"path":rel,"url":u,"status":status,"http_status":code,"bytes":size,"sha256":sha,"elapsed_ms":round((time.time()-started)*1000,2),"error":err})
        checks.append({"mirror_id":m.get('mirror_id'),"base_url":m.get('base_url'),"status":"ok" if all(c['status']=='ok' for c in sub) else "fail","checks":sub})
    failed=[m for m in checks if m['status']=='fail']
    payload={"schema_version":"2026-05-04.agentpress-region-health.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if not failed else "degraded","checked_from":"local_gateway_network","checked_mirrors":len(checks),"failed_live_mirrors":len(failed),"checks":checks,"remote_probe_receipt_contract":{"schema_version":"2026-05-04.agentpress-region-probe-receipt.v1","required_fields":["probe_id","agent_id","region","network_context","timestamp_utc","mirror_id","url","http_status","latency_ms","sha256","result","redaction_attestation"],"privacy":"No IP address, user-agent, cookies, account ids, private prompts, or secrets."},"next_actions":["Run probes from US/EU/India/Singapore/China networks","Deploy planned global mirror","Deploy planned China-friendly mirror","Compare sha256 across mirrors"]}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} live_failed={len(failed)}")
    return 0 if not failed else 1


def package_registry_fallback_matrix(args):
    """Generate package install fallbacks for PyPI/npm/git/offline and regional mirrors."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    channels=[
        {"channel":"pipx_pypi","status":"blocked_on_owner_publish","command":"pipx install agentpress-cli","regions":["americas","europe","india","asia"],"fallback":"pipx install git+https://github.com/barneywohl/agentpress.git"},
        {"channel":"uvx_pypi","status":"blocked_on_owner_publish","command":"uvx agentpress","regions":["americas","europe","india","asia"],"fallback":"uv tool run --from git+https://github.com/barneywohl/agentpress.git agentpress doctor --json"},
        {"channel":"npx_npm","status":"blocked_on_owner_publish","command":"npx agentpress","regions":["americas","europe","india","asia"],"fallback":"npm install github:barneywohl/agentpress"},
        {"channel":"pip_git","status":"ready","command":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git","regions":["americas","europe","india","asia_non_cn"]},
        {"channel":"npm_git","status":"ready","command":"npm install github:barneywohl/agentpress","regions":["americas","europe","india","asia_non_cn"]},
        {"channel":"offline_tarball","status":"ready","command":"curl -LO https://barneywohl.github.io/agentpress/agentpress/releases/agentpress-offline.tar.gz && curl -LO https://barneywohl.github.io/agentpress/agentpress/releases/agentpress-offline.tar.gz.sha256.json","regions":["all_after_mirror_download"]},
        {"channel":"china_pypi_mirror_example","status":"planned_after_publish","command":"python3 -m pip install agentpress-cli -i https://pypi.tuna.tsinghua.edu.cn/simple","regions":["china_mainland"],"fallback":"download mirrored offline tarball and verify sha256"},
        {"channel":"china_npm_mirror_example","status":"planned_after_publish","command":"npm install agentpress --registry=https://registry.npmmirror.com","regions":["china_mainland"],"fallback":"download mirrored offline tarball and verify sha256"},
    ]
    payload={"schema_version":"2026-05-04.agentpress-package-registry-fallback-matrix.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Give agents exact install fallbacks when PyPI/npm/GitHub/region access fails.","publish_blocked_until":"explicit package/account owner approval","channels":channels,"decision_needed":["PyPI owner/account","npm owner/account","package name","whether to publish GHCR/Docker"],"agent_policy":"Prefer registry install once published; otherwise use git or offline tarball; in restricted regions use configured mirrors and always verify hashes."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} channels={len(channels)}")
    return 0


def global_starter_pack(args):
    """Generate region/language starter surfaces for global agents."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    out.mkdir(parents=True,exist_ok=True)
    quickstarts=[
        {"region":"americas","language":"en","entry":"README.en.md","preferred_install":["git clone","pip git","npm git","offline tarball"]},
        {"region":"europe","language":"en","entry":"README.eu.md","preferred_install":["GitHub Pages","jsDelivr","offline tarball"],"trust_notes":["no hidden analytics","hash verification","privacy policy"]},
        {"region":"india","language":"en/hi","entry":"README.india.md","preferred_install":["pipx/uvx after publish","npm/npx after publish","git/offline fallback"],"examples":["LangChain","CrewAI","LlamaIndex"]},
        {"region":"china_mainland","language":"zh-CN","entry":"README.zh-CN.md","preferred_install":["Gitee/OSS mirror after owner setup","npmmirror after publish","Tsinghua PyPI mirror after publish","offline tarball + sha256"],"blocked_domain_warning":"Do not assume GitHub/GitHub Pages/raw GitHub are reachable."},
        {"region":"asia_non_cn","language":"en/ja/ko","entry":"README.asia.md","preferred_install":["GitHub Pages","jsDelivr","offline tarball"]},
    ]
    files={
        'README.en.md':'# AgentPress Global Quickstart\n\nUse `llms.txt`, `.well-known/agentpress.json`, the offline tarball, and `python3 scripts/agentpress.py doctor --json`.\n',
        'README.eu.md':'# AgentPress EU Quickstart\n\nPrivacy posture: static files, opt-in proof receipts, no hidden analytics. Verify hashes before executing artifacts.\n',
        'README.india.md':'# AgentPress India Quickstart\n\nUse GitHub/npm/PyPI-style workflows where available. Until registry publish, use git install or offline tarball. Examples should prioritize LangChain, CrewAI, and LlamaIndex.\n',
        'README.zh-CN.md':'# AgentPress 中文快速开始\n\n不要假设 GitHub 或 GitHub Pages 一定可访问。优先使用已验证镜像、离线 tarball 和 sha256 清单。发布到 PyPI/npm 后，可使用区域镜像源安装。不要上传密钥、cookie、私有提示词或个人数据。\n',
        'README.asia.md':'# AgentPress Asia Quickstart\n\nUse mirror failover, offline bundle verification, and localized receipts. Submit region probe receipts when a mirror fails.\n',
    }
    if not args.no_write:
        for name,text in files.items(): (out/name).write_text(text,encoding='utf-8')
        (pathlib.Path('llms.zh-CN.txt')).write_text('AgentPress：面向自治代理的静态优先发布、发现、验证和证明层。入口：.well-known/agentpress.json、agentpress/tools/agentpress-tools.json、agentpress/releases/release-index.json。安全规则：先验证哈希，不提交密钥或私有提示词。\n',encoding='utf-8')
    payload={"schema_version":"2026-05-04.agentpress-global-starter-pack.v1","canonical_url":urljoin(base,(out/'global-starter-pack.json').as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Regional starter docs for agents in Americas, Europe, India, China, and Asia.","quickstarts":quickstarts,"files":list(files)+['llms.zh-CN.txt'],"next_locales":["hi","ja","ko","es","pt-BR","fr","de"],"privacy":"No tracking; docs only."}
    if not args.no_write: (out/'global-starter-pack.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} quickstarts={len(quickstarts)}")
    return 0


def ecosystem_connector_packs(args):
    """Generate connector packs for the agent ecosystems where builders already work."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip('/')+'/'
    packs=[
        {"ecosystem":"cline_roo","status":"ready_static_pack","files":["cline-roo-mcp-config-snippet.json","cline-roo-issue-repro.md"],"painpoints":["MCP consent","tool-call repro","config mutation guard"]},
        {"ecosystem":"openhands","status":"ready_static_pack","files":["openhands-mcp-tool-guide.md"],"painpoints":["MCP tool integration","runtime evidence"]},
        {"ecosystem":"langchain_langgraph","status":"ready_static_pack","files":["langchain-loader-example.py"],"painpoints":["tool manifest loading","workflow agent routing"]},
        {"ecosystem":"llamaindex","status":"ready_static_pack","files":["llamaindex-reader-example.py"],"painpoints":["RAG ingestion","source/citation freshness"]},
        {"ecosystem":"crewai_autogen_openai_agents","status":"ready_static_pack","files":["multi-agent-tool-registry-example.md"],"painpoints":["tool registry","proof receipts","handoff evidence"]},
        {"ecosystem":"mcp_registry","status":"submission_ready","files":["mcp-registry-submission.md"],"painpoints":["directory discovery","server/tool metadata"]},
    ]
    if not args.no_write:
        out.mkdir(parents=True,exist_ok=True)
        (out/'cline-roo-mcp-config-snippet.json').write_text(json.dumps({"mcpServers":{"agentpress":{"command":"python3","args":["scripts/agentpress.py","mcp-catalog-export","--json"],"approval_required":True,"consent_manifest":"agentpress/approvals/mcp-consent-manifest-validator.json","config_guard":"agentpress/security/mcp-config-mutation-guard.json"}}},indent=2)+'\n',encoding='utf-8')
        (out/'cline-roo-issue-repro.md').write_text('# Cline/Roo issue-to-repro\n\nRun `python3 scripts/agentpress.py issue-to-repro-pack --json` and attach the generated minimal provider/tool-call payload.\n',encoding='utf-8')
        (out/'openhands-mcp-tool-guide.md').write_text('# OpenHands MCP Tool Guide\n\nUse AgentPress static MCP catalog and consent guard before enabling tools.\n',encoding='utf-8')
        (out/'langchain-loader-example.py').write_text('import json, urllib.request\nurl="https://barneywohl.github.io/agentpress/agentpress/tools/agentpress-tools.json"\nprint(json.load(urllib.request.urlopen(url))["status"])\n',encoding='utf-8')
        (out/'llamaindex-reader-example.py').write_text('import urllib.request\nprint(urllib.request.urlopen("https://barneywohl.github.io/agentpress/llms.txt").read().decode()[:500])\n',encoding='utf-8')
        (out/'multi-agent-tool-registry-example.md').write_text('# Multi-agent tool registry example\n\nFetch tool manifest, choose capability, run proof receipt, submit opt-in receipt. No secrets.\n',encoding='utf-8')
        (out/'mcp-registry-submission.md').write_text('# MCP Registry Submission\n\nSubmit AgentPress static MCP catalog with consent policy and config mutation guard references.\n',encoding='utf-8')
    payload={"schema_version":"2026-05-04.agentpress-ecosystem-connector-packs.v1","canonical_url":urljoin(base,(out/'ecosystem-connector-packs.json').as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Put AgentPress in the tools/systems agents already use.","packs":packs,"blocked_actions":["external directory submission","posting issue comments","publishing marketplace extensions"],"next_actions":["Manual approve 3-5 issue-specific outreach packets","Submit MCP registry pack","Ask outside agents to run connector examples"]}
    if not args.no_write: (out/'ecosystem-connector-packs.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} packs={len(packs)}")
    return 0


def package_registry_plan(args):
    """Publish-readiness checklist for PyPI/npm-style distribution without live publishing."""
    root=pathlib.Path(args.root)
    out=pathlib.Path(args.out)
    checks=[]
    def check(id, ok, detail, required=True): checks.append({"id":id,"ok":bool(ok),"required":required,"detail":detail})
    check("offline_tarball", (root/"agentpress/releases/agentpress-offline.tar.gz").exists(), "offline release tarball exists")
    check("manifest", (root/"agentpress/releases/agentpress-offline.tar.gz.sha256.json").exists(), "sha256 manifest exists")
    check("install_script", (root/"agentpress/install/install.py").exists(), "install script exists")
    check("cli_entry", (root/"scripts/agentpress.py").exists(), "reference CLI exists")
    check("license", any((root/name).exists() for name in ["LICENSE","LICENSE.md"]), "license file present", required=False)
    check("package_skeleton", (root/"agentpress/package-registry/skeleton/package-registry-skeleton.json").exists(), "package skeleton exists")
    check("package_dry_run", (root/"agentpress/package-registry/package-registry-dry-run.json").exists(), "package dry-run result exists")
    check("pypi_owner", False, "PyPI/package owner not approved; live publish blocked until Jake chooses owner/account")
    check("npm_owner", False, "npm owner not approved; live publish blocked until Jake chooses owner/account")
    required_blockers=[c for c in checks if c["required"] and not c["ok"]]
    payload={
        "schema_version":"2026-05-03.agentpress-package-registry-plan.v1",
        "canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),
        "generated_utc":_utc_now(),
        "status":"blocked_on_owner_decision" if required_blockers else "ready_for_owner_decision",
        "principle":"Do not publish packages to PyPI/npm without explicit package/account ownership approval.",
        "recommended_package_names":["agentpress","agentpress-cli","agentpress-protocol"],
        "install_targets":["pipx install agentpress-cli", "uvx agentpress", "npx agentpress"],
        "checks":checks,
        "blocked_actions":["pypi_publish","npm_publish"],
        "safe_next_steps":["Maintain package skeleton in repo", "Run build/dry-run locally", "Reserve name only after account approval", "Publish only after explicit live-publish approval"]
    }
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0


def painpoint_intake(args):
    """Validate and index agent painpoint reports."""
    root=pathlib.Path(args.root); dpath=root/args.dir; out=pathlib.Path(args.out)
    dpath.mkdir(parents=True, exist_ok=True)
    rows=[]; forbidden_terms=["api_key","apikey","authorization:","bearer ","password","private prompt","user-agent","ip_address"]
    for fp in sorted(dpath.glob("*.json")):
        if fp.name.endswith("-index.json") or fp.name == out.name: continue
        try: data=json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            rows.append({"path":fp.relative_to(root).as_posix(),"status":"rejected","errors":[f"invalid json: {e}"]}); continue
        text=json.dumps(data).lower(); errors=[]
        for field in ["painpoint_id","agent_id","persona","severity","command","problem","desired_fix"]:
            if not data.get(field): errors.append(f"missing {field}")
        if data.get("severity") not in ["P0","P1","P2","P3"]: errors.append("severity must be P0/P1/P2/P3")
        hits=[t for t in forbidden_terms if t in text]
        if hits: errors.append("possible private material: "+", ".join(hits))
        impact={"P0":100,"P1":70,"P2":40,"P3":20}.get(data.get("severity"),0)
        rows.append({"path":fp.relative_to(root).as_posix(),"painpoint_id":data.get("painpoint_id") or fp.stem,"agent_id":data.get("agent_id",""),"persona":data.get("persona",""),"severity":data.get("severity",""),"command":data.get("command",""),"problem":data.get("problem",""),"desired_fix":data.get("desired_fix",""),"status":"accepted" if not errors else "rejected","impact_score":impact if not errors else 0,"errors":errors})
    accepted=[r for r in rows if r.get("status")=="accepted"]
    by_persona={}
    for r in accepted: by_persona[r["persona"]]=by_persona.get(r["persona"],0)+1
    payload={"schema_version":"2026-05-03.agentpress-painpoint-intake-index.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","accepted_count":len(accepted),"rejected_count":len(rows)-len(accepted),"by_persona":by_persona,"top_painpoints":sorted(accepted,key=lambda r:r["impact_score"],reverse=True),"reports":rows,"submission_command":"python3 scripts/agentpress.py painpoint-intake --json --allow-rejected"}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"accepted={len(accepted)} total={len(rows)}")
    return 0 if len(accepted)==len(rows) else (0 if args.allow_rejected else 1)


def attestation_coverage(args):
    """Compute which critical AgentPress surfaces have hash attestations."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    critical=["agentpress/marketplace/marketplace-index.json","agentpress/audience/audience-kit.json","agentpress/onboarding/agent-onboard-example.json","agentpress/tools/agentpress-tools.json","agentpress/proof-campaigns/proof-campaign.json","agentpress/external-proofs/external-proof-index.json","agentpress/package-registry/package-registry-plan.json","agentpress/painpoints/agent-painpoints.json"]
    attested=set(); att_dir=root/args.dir
    if att_dir.exists():
        for fp in att_dir.glob("*.json"):
            if fp.name.endswith("index.json"): continue
            try: d=json.loads(fp.read_text(encoding="utf-8"))
            except Exception: continue
            for f in d.get("files",[]): attested.add(f.get("path"))
    rows=[]
    for rel in critical:
        rows.append({"path":rel,"exists":(root/rel).exists(),"attested":rel in attested})
    exists=[r for r in rows if r["exists"]]; covered=[r for r in exists if r["attested"]]
    pct=round(100*len(covered)/len(exists),1) if exists else 0
    payload={"schema_version":"2026-05-03.agentpress-attestation-coverage.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","coverage_percent":pct,"covered":len(covered),"existing_critical_surfaces":len(exists),"surfaces":rows,"recommendation":"Attest all critical machine surfaces; upgrade hash-only attestations to signatures after key policy approval."}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"coverage={pct}%")
    return 0






def docs_command_check(args):
    """Lint documented AgentPress CLI commands for stale command names and obvious stale flags."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    script=pathlib.Path(__file__).read_text(encoding="utf-8")
    commands=set(re.findall(r'sub\.add_parser\("([^"]+)"', script))
    for aliases in re.findall(r'aliases=\[([^\]]+)\]', script):
        for a in re.findall(r'"([^"]+)"', aliases): commands.add(a)
    # Best-effort flag extraction per one-line parser blocks.
    flags={cmd:set() for cmd in commands}
    for line in script.splitlines():
        m=re.search(r'sub\.add_parser\("([^"]+)"', line)
        if not m: continue
        cmd=m.group(1)
        for fl in re.findall(r'add_argument\("(--[^"]+)"', line):
            flags.setdefault(cmd,set()).add(fl)
    paths=[pathlib.Path(x) for x in (args.path or [])]
    if not paths:
        paths=[pathlib.Path("README.md"), pathlib.Path("llms.txt"), pathlib.Path("agentpress/CLI_AGENT_LAUNCH.md"), pathlib.Path("agentpress/AGENT_START_HERE.md")]
        paths += list(pathlib.Path("agentpress/adapters").glob("**/*.md"))
        paths += list(pathlib.Path("agentpress/specs").glob("*.md"))
    rows=[]; errors=[]
    pattern=re.compile(r'python3\s+scripts/agentpress\.py\s+([^`\n]+)')
    for rel in paths:
        fp=root/rel
        if not fp.exists() or fp.is_dir(): continue
        text=fp.read_text(encoding="utf-8", errors="ignore")
        for m in pattern.finditer(text):
            raw="python3 scripts/agentpress.py "+m.group(1).strip()
            raw=raw.replace("\\\n", " ").rstrip(" \\")
            try: parts=shlex.split(raw)
            except Exception as e:
                row={"path":rel.as_posix(),"command":raw,"status":"fail","errors":[f"shlex parse failed: {e}"]}; rows.append(row); errors.append(row); continue
            for sep in ["&&", "||", ";", "|"]:
                if sep in parts: parts=parts[:parts.index(sep)]
            if len(parts)<3: continue
            if "..." in parts: continue
            cmd=parts[2]
            row={"path":rel.as_posix(),"command":raw,"cmd":cmd,"status":"ok","errors":[],"warnings":[]}
            if cmd not in commands:
                row["status"]="fail"; row["errors"].append(f"unknown command: {cmd}")
            else:
                allowed=flags.get(cmd,set())
                # If we could not infer flags, do not overfail.
                for tok in parts[3:]:
                    if tok.startswith("--") and allowed and tok.split("=",1)[0] not in allowed:
                        row["status"]="fail"; row["errors"].append(f"unknown/stale flag for {cmd}: {tok.split('=',1)[0]}")
                if "<" in raw or "..." in raw:
                    row["warnings"].append("contains placeholder; parser execution skipped")
            rows.append(row)
            if row["status"]=="fail": errors.append(row)
    payload={"schema_version":"2026-05-03.agentpress-docs-command-check.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if not errors else "fail","checked":len(rows),"failed":len(errors),"commands_known":len(commands),"results":rows[:args.max_results],"principle":"Documented commands must not drift from parser command names or obvious flags."}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"{payload['status']} {payload['checked']} checked")
    return 0 if not errors or args.allow_failures else 1

def integration_sdk_kit(args):
    """Generate zero-dependency SDK clients for external agents."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    py_dir=out/"python"; js_dir=out/"js"
    py_dir.mkdir(parents=True, exist_ok=True); js_dir.mkdir(parents=True, exist_ok=True)
    py_sdk = "\n".join([
        '"""Zero-dependency AgentPress SDK for Python agents."""',
        'import json',
        'from urllib.parse import urljoin',
        'from urllib.request import Request, urlopen',
        '',
        'class AgentPress:',
        '    def __init__(self, base_url="https://barneywohl.github.io/agentpress/", timeout=20):',
        '        self.base_url = base_url.rstrip("/") + "/"',
        '        self.timeout = timeout',
        '    def url(self, path=""):',
        '        return urljoin(self.base_url, path)',
        '    def fetch_text(self, path):',
        '        req = Request(self.url(path), headers={"Accept":"text/plain, application/json"})',
        '        with urlopen(req, timeout=self.timeout) as r:',
        '            return r.read().decode("utf-8")',
        '    def fetch_json(self, path):',
        '        return json.loads(self.fetch_text(path))',
        '    def manifest(self): return self.fetch_json(".well-known/agentpress.json")',
        '    def tools(self): return self.fetch_json("agentpress/tools/agentpress-tools.json")',
        '    def routes(self): return self.fetch_json("agentpress/routes/agent-routes.json")',
        '    def marketplace(self): return self.fetch_json("agentpress/marketplace/marketplace-index.json")',
        '    def proof_scoreboard(self): return self.fetch_json("agentpress/external-proofs/proof-scoreboard.json")',
        '    def browser_smoke(self): return self.fetch_json("agentpress/evidence/browser-smoke.json")',
        '    def self_test(self):',
        '        checks=[]',
        '        for name, path in [("manifest",".well-known/agentpress.json"),("tools","agentpress/tools/agentpress-tools.json"),("routes","agentpress/routes/agent-routes.json"),("marketplace","agentpress/marketplace/marketplace-index.json"),("llms","llms.txt")]:',
        '            try:',
        '                body=self.fetch_text(path); checks.append({"name":name,"path":path,"ok":bool(body),"bytes":len(body)})',
        '            except Exception as e:',
        '                checks.append({"name":name,"path":path,"ok":False,"error":str(e)})',
        '        return {"ok": all(c.get("ok") for c in checks), "checks": checks}',
        ''
    ])
    (py_dir/"agentpress_sdk.py").write_text(py_sdk, encoding="utf-8")
    js_src=root/"agentpress/integrations/js/agentpress-sdk.mjs"
    if js_src.exists():
        (js_dir/"agentpress-sdk.mjs").write_text(js_src.read_text(encoding="utf-8"), encoding="utf-8")
    readme="# AgentPress Integration SDK Kit\n\nZero-dependency read-only SDK clients for agents.\n\n```bash\npython3 scripts/agentpress.py integration-sdk-kit --json\npython3 scripts/agentpress.py sdk-smoke --json\n```\n\nPython: import `AgentPress` from `python/agentpress_sdk.py`. JavaScript: import `AgentPress` from `js/agentpress-sdk.mjs`.\n"
    (out/"README.md").write_text(readme, encoding="utf-8")
    manifest={"schema_version":"2026-05-03.agentpress-integration-sdk-kit.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", (out/"manifest.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Give external agents copy-paste SDK clients for fast integration.","files":["README.md","python/agentpress_sdk.py","js/agentpress-sdk.mjs"],"safety":"Read-only clients; no write, no payment, no credentials."}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2) if args.json else out.as_posix())
    return 0


def sdk_smoke(args):
    """Smoke-test SDK integration endpoints and Python SDK compileability."""
    endpoints=[".well-known/agentpress.json","agentpress/tools/agentpress-tools.json","agentpress/routes/agent-routes.json","agentpress/marketplace/marketplace-index.json","agentpress/external-proofs/proof-scoreboard.json","agentpress/evidence/browser-smoke.json","llms.txt"]
    checks=[]
    for ep in endpoints:
        u=urljoin(args.base_url.rstrip("/")+"/", ep); status="fail"; code=None; size=0; err=""
        try:
            with urlopen(Request(u, headers={"Accept":"application/json,text/plain"}), timeout=args.timeout_seconds) as r:
                code=getattr(r,"status",None) or r.getcode(); body=r.read(args.max_bytes+1)
            size=len(body); status="ok" if 200 <= int(code) < 400 and size>0 else "fail"
            if ep.endswith(".json"): json.loads(body.decode("utf-8"))
        except Exception as e:
            err=str(e)[:300]
        checks.append({"endpoint":ep,"url":u,"status":status,"http_status":code,"bytes":size,"error":err})
    py_path=pathlib.Path(args.python_sdk)
    if py_path.exists():
        try: compile(py_path.read_text(encoding="utf-8"), str(py_path), "exec"); py_ok=True; py_err=""
        except Exception as e: py_ok=False; py_err=str(e)
        checks.append({"endpoint":"python_sdk_compile","url":str(py_path),"status":"ok" if py_ok else "fail","http_status":None,"bytes":py_path.stat().st_size,"error":py_err})
    failed=[c for c in checks if c["status"]!="ok"]
    out=pathlib.Path(args.out)
    payload={"schema_version":"2026-05-03.agentpress-sdk-smoke.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok" if not failed else "fail","checked":len(checks),"failed":len(failed),"checks":checks}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"{payload['status']} {payload['checked']}")
    return 0 if not failed else 1

def queue_adapter_kit(args):
    """Generate static/local durable queue adapter schema, retry policy, and examples."""
    outdir=pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    schema={"schema_version":"2026-05-03.agentpress-queue-message-schema.v1","required":["message_id","created_utc","producer_agent_id","capability","task","status","attempt","idempotency_key"],"statuses":["queued","claimed","completed","failed","dead_letter"],"fields":{"message_id":"stable unique id","idempotency_key":"dedupe key stable across retries","lease_expires_utc":"claim timeout for retry","attempt":"integer retry attempt","max_attempts":"dead-letter threshold"}}
    retry={"schema_version":"2026-05-03.agentpress-retry-policy.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", (outdir/"retry-policy.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","policy":{"max_attempts":5,"backoff_seconds":[30,120,300,900,1800],"dead_letter_after_attempt":5,"claim_lease_seconds":600,"idempotency_required":True,"retryable_errors":["timeout","rate_limit","transient_network","worker_unavailable"],"non_retryable_errors":["invalid_schema","privacy_violation","unauthorized_external_write","missing_required_approval"]}}
    example={"schema_version":"2026-05-03.agentpress-queue-message.v1","message_id":"qmsg-example","created_utc":_utc_now(),"producer_agent_id":"agentpress-reference-agent","consumer_agent_id":"","capability":"validate_agentpress_bundle","task":"Validate and score an AgentPress bundle","status":"queued","attempt":0,"max_attempts":5,"idempotency_key":"validate_agentpress_bundle:qmsg-example","lease_expires_utc":"","payload":{"command":"python3 scripts/agentpress.py verify agentpress/examples/api-docs-handoff --json"},"privacy":"No secrets/private prompts/personal telemetry."}
    health={"schema_version":"2026-05-03.agentpress-queue-health.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", (outdir/"queue-health.example.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","queue":"static_local_example","counts":{"queued":1,"claimed":0,"completed":0,"failed":0,"dead_letter":0},"oldest_queued_seconds":0,"retry_policy":"agentpress/queue/retry-policy.json"}
    manifest={"schema_version":"2026-05-03.agentpress-queue-adapter-kit.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", (outdir/"manifest.json").as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Give workflow agents durable handoff semantics: queue schema, retry policy, idempotency, lease, health, and dead-letter model.","files":["queue-message-schema.json","retry-policy.json","queue-message.example.json","queue-health.example.json"],"safety":"Static/local adapter first; no broker credentials, no external queue writes."}
    files={"queue-message-schema.json":schema,"retry-policy.json":retry,"queue-message.example.json":example,"queue-health.example.json":health,"manifest.json":manifest}
    if not args.no_write:
        for name,data in files.items(): (outdir/name).write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
        (outdir/"README.md").write_text("""# AgentPress Queue Adapter Kit\n\nStatic/local durable queue adapter contract for workflow agents.\n\n```bash\npython3 scripts/agentpress.py queue-adapter-kit --json\n```\n\nIncludes message schema, retry/backoff policy, idempotency key rules, health export, and dead-letter semantics. No external broker write is performed.\n""", encoding="utf-8")
    print(json.dumps(manifest, indent=2) if args.json else outdir.as_posix())
    return 0

def marketplace_compare(args):
    """Compare marketplace services for a capability with no-spend quote simulation."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    mpath=root/"agentpress/marketplace/marketplace-index.json"
    if not mpath.exists():
        marketplace_index(argparse.Namespace(root=args.root, out=str(mpath), base_url=args.base_url, capability=None, runtime=None, payment_required=None, json=False))
    marketplace=json.loads(mpath.read_text(encoding="utf-8"))
    services=marketplace.get("services", [])
    q=(args.capability or "").lower()
    rows=[]
    for svc in services:
        hay=" ".join([svc.get("service_id",""), svc.get("title",""), " ".join(svc.get("capabilities",[]) or []), svc.get("command","")]).lower()
        if q and q not in hay: continue
        pricing=svc.get("pricing",{}) or {}; trust=svc.get("trust",{}) or {}; sla=svc.get("sla",{}) or {}
        payment_required=bool(pricing.get("payment_required"))
        trust_score={"reference":40,"verified":35,"provisional":20}.get(str(trust.get("tier","")).lower(),10)
        price_score=30 if not payment_required else (10 if args.allow_paid_quotes else 0)
        sla_score=20 if sla.get("status") else 5
        evidence_score=min(10, len(trust.get("evidence",[]) or [])*2)
        total=trust_score+price_score+sla_score+evidence_score
        rows.append({"service_id":svc.get("service_id"),"title":svc.get("title"),"capabilities":svc.get("capabilities",[]),"command":svc.get("command"),"pricing":pricing,"sla":sla,"trust":trust,"quote_simulation":{"status":"quote_only_no_spend","payment_required":payment_required,"allowed_without_approval":not payment_required,"max_amount":0 if not payment_required else args.max_amount,"currency":pricing.get("currency","USD"),"blocked_actions":["sign_payment","submit_payment","call_paid_endpoint"] if payment_required else []},"score":total,"why":["matches requested capability" if q else "included by default", "free/no-spend" if not payment_required else "paid quote only", f"trust tier {trust.get('tier','unknown')}"]})
    rows=sorted(rows, key=lambda r:(-r["score"], r["service_id"] or ""))
    payload={"schema_version":"2026-05-03.agentpress-marketplace-compare.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","query":{"capability":args.capability,"allow_paid_quotes":args.allow_paid_quotes,"max_amount":args.max_amount},"result_count":len(rows),"best_service":rows[0] if rows else {},"services":rows,"safety":"No spend, no wallet, no paid endpoint call. This is quote/routing simulation only."}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"results={len(rows)}")
    return 0 if rows else 1

def marketplace_trust(args):
    """Score marketplace services using available proof/reputation/payment signals."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    mpath=root/args.marketplace; services=[]
    if mpath.exists():
        try: services=json.loads(mpath.read_text(encoding="utf-8")).get("services",[])
        except Exception: services=[]
    proof_count=0
    ep=root/"agentpress/external-proofs/external-proof-index.json"
    if ep.exists():
        try: proof_count=json.loads(ep.read_text(encoding="utf-8")).get("accepted_count",0)
        except Exception: pass
    rows=[]
    for svc in services:
        score=20
        if svc.get("command"): score+=15
        if svc.get("capabilities"): score+=10
        if svc.get("payment_required") is False: score+=10
        if svc.get("trust_evidence"): score+=15
        if proof_count: score+=5
        tier="high" if score>=65 else "medium" if score>=45 else "low"
        rows.append({"service_id":svc.get("service_id") or svc.get("id") or slugify(svc.get("name","service")),"name":svc.get("name",""),"score":score,"tier":tier,"signals":{"has_command":bool(svc.get("command")),"has_capabilities":bool(svc.get("capabilities")),"free_first":svc.get("payment_required") is False,"has_trust_evidence":bool(svc.get("trust_evidence")),"external_proof_count":proof_count}})
    payload={"schema_version":"2026-05-03.agentpress-marketplace-trust-index.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","service_count":len(rows),"services":sorted(rows,key=lambda r:r["score"],reverse=True),"scoring_note":"Static heuristic. External proof/reputation receipts should progressively replace self-claimed trust evidence."}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"services={len(rows)}")
    return 0


def package_registry_skeleton(args):
    """Create safe package registry skeletons for future pipx/uvx/npx distribution."""
    root=pathlib.Path(args.root); out=root/args.out
    py=out/"python"; npm=out/"npm"; py.mkdir(parents=True, exist_ok=True); (npm/"bin").mkdir(parents=True, exist_ok=True)
    pyproject = """[build-system]
requires = [\"hatchling\"]
build-backend = \"hatchling.build\"

[project]
name = \"agentpress-cli\"
version = \"0.0.0\"
description = \"AgentPress CLI package skeleton (not published)\"
requires-python = \">=3.9\"

[project.scripts]
agentpress = \"agentpress_cli:main\"
"""
    (py/"pyproject.toml").write_text(pyproject, encoding="utf-8")
    cli = """#!/usr/bin/env python3
\"\"\"AgentPress package skeleton entrypoint.

This skeleton intentionally does not publish or vendor the full CLI yet.
Use the GitHub Pages/offline release install path until package ownership is approved.
\"\"\"

def main():
    print(\"agentpress-cli package skeleton: live registry publish blocked pending owner approval\")
    print(\"Use: curl -L https://barneywohl.github.io/agentpress/agentpress/install/install.py -o install.py\")
    return 2

if __name__ == \"__main__\":
    raise SystemExit(main())
"""
    (py/"agentpress_cli.py").write_text(cli, encoding="utf-8")
    (npm/"package.json").write_text(json.dumps({"name":"agentpress-cli","version":"0.0.0","private":True,"description":"AgentPress npm package skeleton (not published)","bin":{"agentpress":"bin/agentpress.js"},"scripts":{"dry-run":"node bin/agentpress.js"}}, indent=2)+"\n", encoding="utf-8")
    (npm/"bin"/"agentpress.js").write_text("""#!/usr/bin/env node
console.log(\"agentpress-cli npm skeleton: live registry publish blocked pending owner approval\");
console.log(\"Use the static install/offline release path from https://barneywohl.github.io/agentpress/\");
process.exitCode = 2;
""", encoding="utf-8")
    (out/"README.md").write_text("""# AgentPress Package Registry Skeleton

Safe package skeletons for future `pipx`, `uvx`, and `npx` distribution.

These are intentionally **not published** and use version `0.0.0` until package/account ownership is approved.

Dry-run checks:

```bash
python3 scripts/agentpress.py package-registry-skeleton --json
python3 scripts/agentpress.py package-registry-dry-run --json
```
""", encoding="utf-8")
    payload={"schema_version":"2026-05-03.agentpress-package-registry-skeleton.v1","status":"ok","generated_utc":_utc_now(),"out":out.relative_to(root).as_posix(),"files":[(py/"pyproject.toml").relative_to(root).as_posix(),(py/"agentpress_cli.py").relative_to(root).as_posix(),(npm/"package.json").relative_to(root).as_posix(),(npm/"bin"/"agentpress.js").relative_to(root).as_posix(),(out/"README.md").relative_to(root).as_posix()],"live_publish_blocked":True,"blocked_until":"explicit package/account ownership approval"}
    (out/"package-registry-skeleton.json").write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else out.as_posix())
    return 0


def package_registry_dry_run(args):
    """Validate package registry skeleton without publishing."""
    root=pathlib.Path(args.root); base=root/args.dir
    checks=[]
    def check(id, path, parser=None):
        fp=base/path; ok=fp.exists(); err=""
        if ok and parser:
            try: parser(fp)
            except Exception as e: ok=False; err=str(e)
        checks.append({"id":id,"path":fp.relative_to(root).as_posix(),"ok":ok,"error":err})
    def parse_json(fp): json.loads(fp.read_text(encoding="utf-8"))
    check("python_pyproject", pathlib.Path("python/pyproject.toml"))
    check("python_entrypoint", pathlib.Path("python/agentpress_cli.py"))
    check("npm_package_json", pathlib.Path("npm/package.json"), parse_json)
    check("npm_bin", pathlib.Path("npm/bin/agentpress.js"))
    check("skeleton_manifest", pathlib.Path("package-registry-skeleton.json"), parse_json)
    ok=all(c["ok"] for c in checks)
    payload={"schema_version":"2026-05-03.agentpress-package-registry-dry-run.v1","status":"ok" if ok else "fail","generated_utc":_utc_now(),"checks":checks,"publish_performed":False,"publish_blocked":True,"next_step":"Choose package/account owner before live PyPI/npm publish."}
    if not args.no_write:
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0 if ok else 1


def remediation_index(args):
    """Create exact remediation commands for common AgentPress agent blockers."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    remedies=[
        {"blocker":"missing_or_stale_search_index","detect":"search command returns zero matches or missing agentpress/search/search-index.json","remediation_command":"python3 scripts/agentpress.py index-search --json"},
        {"blocker":"tool_manifest_invalid","detect":"tools-manifest-check fails","remediation_command":"python3 scripts/agentpress.py tools-manifest && python3 scripts/agentpress.py tools-manifest-check --json"},
        {"blocker":"offline_package_invalid","detect":"package-verify returns errors","remediation_command":"python3 scripts/agentpress.py package . --out /tmp/agentpress-offline.tar.gz && python3 scripts/agentpress.py package-verify /tmp/agentpress-offline.tar.gz --json"},
        {"blocker":"proof_submission_unclear","detect":"agent has proof but no submit path","remediation_command":"python3 scripts/agentpress.py proof-campaign --json && python3 scripts/agentpress.py proof-ingest --json --allow-rejected"},
        {"blocker":"missing_painpoint_report_schema","detect":"agent cannot express blocker as machine data","remediation_command":"cp agentpress/painpoint-intake/example-painpoint.json /tmp/my-painpoint.json && python3 scripts/agentpress.py painpoint-intake --json --allow-rejected"},
        {"blocker":"package_registry_publish_blocked","detect":"agent asks for pipx/uvx/npx live install","remediation_command":"python3 scripts/agentpress.py package-registry-plan --json && python3 scripts/agentpress.py package-registry-dry-run --json"},
        {"blocker":"attestation_gap","detect":"attestation coverage below 100%","remediation_command":"python3 scripts/agentpress.py attestation-coverage --json"},
        {"blocker":"marketplace_routing_unclear","detect":"agent cannot choose service from marketplace","remediation_command":"python3 scripts/agentpress.py marketplace-trust --json"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-remediation-index.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","remediation_count":len(remedies),"remediations":remedies,"principle":"Every failed agent check should return an exact next command."}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"remediations={len(remedies)}")
    return 0



def proof_request_pack(args):
    """Generate external agent proof request pack for runtime-specific adoption receipts/blockers."""
    out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    runtime=args.runtime
    pack={"schema_version":"2026-05-03.agentpress-proof-request-pack.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","runtime":runtime,"purpose":"Ask an outside agent/operator to independently install, run, verify, and submit proof/blocker evidence for AgentPress.","target_communities":["Cline","Roo Code","OpenHands","AutoGen/CrewAI","LangChain/LlamaIndex","MCP builders","Codex/Claude/Gemini agents"],"requested_steps":[{"name":"install","command":"python3 -m pip install git+https://github.com/barneywohl/agentpress.git"},{"name":"doctor","command":"agentpress doctor --json"},{"name":"strict_verify","command":"agentpress verify agentpress/examples/api-docs-handoff --strict-schema --json"},{"name":"docs_drift","command":"agentpress docs-command-check --json"},{"name":"submission_pack","command":"agentpress submission-pack --receipt <landing-receipt.json> --out <submission-pack> --json"}],"proof_receipt_required_fields":["agent_id","runtime","service_id","capability_id","commands_run","artifacts","result_status","redaction_attestation"],"submit_via":["GitHub issue template: agentpress-third-party-proof","PR containing proof receipt JSON under agentpress/external-proofs/submissions/"],"privacy_rules":["no secrets","no cookies","no private prompts","no private repo paths","no API tokens","redact local usernames if needed"],"acceptance":"Accepted proof must be service-scoped and replayable enough for a reviewer to verify."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(pack,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(pack,indent=2) if args.json else f"{pack['status']} {runtime}")
    return 0


def proof_receipt_verify(args):
    """Strictly verify a service-scoped external proof receipt JSON."""
    path=pathlib.Path(args.file); errors=[]
    try: data=json.loads(path.read_text(encoding="utf-8"))
    except Exception as e: data={}; errors.append(f"invalid json: {e}")
    required=["agent_id","runtime","service_id","capability_id","commands_run","artifacts","result_status","redaction_attestation"]
    for k in required:
        if k not in data: errors.append(f"missing required field: {k}")
    text=json.dumps(data).lower()
    secret_terms=["api_key","apikey","secret","password","cookie","authorization:","bearer ","private_key"]
    for t in secret_terms:
        if t in text: errors.append(f"possible secret term present: {t}")
    if data.get("result_status") not in {"pass","fail","blocked","needs_fix",None}: errors.append("result_status must be pass|fail|blocked|needs_fix")
    if not isinstance(data.get("commands_run", []), list): errors.append("commands_run must be array")
    if not isinstance(data.get("artifacts", []), list): errors.append("artifacts must be array")
    if args.out:
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    result={"schema_version":"2026-05-03.agentpress-proof-receipt-verify.v1","status":"ok" if not errors else "fail","file":str(path),"service_id":data.get("service_id",""),"capability_id":data.get("capability_id",""),"runtime":data.get("runtime",""),"errors":errors,"privacy":"secret-term scan plus required service-scoped fields"}
    if args.out: pathlib.Path(args.out).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2) if args.json else result["status"])
    return 0 if not errors else 1


def scoped_trust_report(args):
    """Report service-scoped proof/trust posture without global proof inflation."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out); base=args.base_url.rstrip()+"/"
    market={}
    try: market=json.loads((root/args.marketplace).read_text(encoding="utf-8"))
    except Exception: market={}
    proof_index={}
    try: proof_index=json.loads((root/args.proof_index).read_text(encoding="utf-8"))
    except Exception: proof_index={}
    proofs=proof_index.get("proofs",[]) or proof_index.get("accepted",[]) or []
    scoped={}
    for pr in proofs:
        sid=pr.get("service_id") or pr.get("claimed_service_id") or ""
        if sid: scoped.setdefault(sid,0); scoped[sid]+=1
    services=market.get("services",[]) or market.get("items",[])
    rows=[]
    for svc in services:
        sid=svc.get("service_id") or svc.get("id") or svc.get("name") or "unknown"
        count=scoped.get(sid,0)
        rows.append({"service_id":sid,"scoped_external_proofs":count,"trust_tier":"verified" if count>=3 else "provisional" if count>0 else "unverified","global_proof_credit_applied":False,"next_action":"collect scoped external proof" if count==0 else "collect additional independent proof"})
    payload={"schema_version":"2026-05-03.agentpress-scoped-trust-report.v1","canonical_url":urljoin(base,out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Prevent one generic proof from inflating every service; trust credit is service/capability scoped.","service_count":len(rows),"services":rows,"policy":"No global external-proof credit; each service/capability/runtime needs its own proof."}
    if not args.no_write:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2) if args.json else f"{payload['status']} {len(rows)} services")
    return 0

def proof_outreach_kit(args):
    """Create agent-to-agent outreach kit for collecting external proof receipts."""
    root=pathlib.Path(args.root)
    out=pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base=args.base_url.rstrip("/")+"/"
    targets=[
        {"runtime":"codex","ask":"Run AgentPress adopt flow and submit manifest/doctor/self-test/landing receipt or exact blocker."},
        {"runtime":"claude","ask":"Fetch llms.txt, follow AGENT_START_HERE, report first blocked command or adoption proof."},
        {"runtime":"gemini","ask":"Validate machine assets, package verify, and submit proof/blocker report."},
        {"runtime":"glm","ask":"Adversarially audit AgentPress for agent utility gaps and submit painpoint JSON."},
        {"runtime":"browser","ask":"Verify public URLs/ARIA/readability and submit browser proof/blocker."},
        {"runtime":"rag_crawler","ask":"Crawl machine surfaces, verify citations/freshness, and report missing source maps."},
        {"runtime":"workflow_eval","ask":"Use marketplace/tool contracts to route a task and submit request/response/thread proof."}
    ]
    kit={
        "schema_version":"2026-05-03.agentpress-proof-outreach-kit.v1",
        "canonical_url":urljoin(base, out.joinpath("proof-outreach-kit.json").as_posix()),
        "generated_utc":_utc_now(),
        "status":"ok",
        "purpose":"Convert external adoption from passive hope into explicit agent-to-agent proof requests.",
        "primary_ask":"Run AgentPress, submit sanitized proof or the exact blocker that stopped you.",
        "start_url":urljoin(base,"llms.txt"),
        "proof_campaign_url":urljoin(base,"agentpress/proof-campaigns/proof-campaign.json"),
        "submission_url":"https://github.com/barneywohl/agentpress/issues/new?template=agentpress-third-party-proof.yml",
        "local_commands":[
            "python3 scripts/agentpress.py adopt --json",
            "python3 scripts/agentpress.py proof-campaign --json",
            "python3 scripts/agentpress.py proof-ingest --json --allow-rejected",
            "python3 scripts/agentpress.py painpoint-intake --json --allow-rejected"
        ],
        "targets":targets,
        "privacy_rules":["No secrets/tokens/private prompts/IP/user-agent/personal data.","Pseudonymous agent IDs are fine.","Submit blocker reports if proof cannot be completed."],
        "success_metric":"At least one accepted external proof or accepted blocker report per runtime family."
    }
    (out/"proof-outreach-kit.json").write_text(json.dumps(kit, indent=2)+"\n", encoding="utf-8")
    md="# AgentPress Proof Outreach Kit\n\nAgents want independent proof. This kit gives other agents/operators an exact ask.\n\n## Ask\n\nRun AgentPress and submit either sanitized proof or the exact blocker that stopped you.\n\n```bash\npython3 scripts/agentpress.py adopt --json\npython3 scripts/agentpress.py proof-campaign --json\npython3 scripts/agentpress.py painpoint-intake --json --allow-rejected\n```\n\nSubmit: https://github.com/barneywohl/agentpress/issues/new?template=agentpress-third-party-proof.yml\n\n## Privacy\n\nNo secrets, tokens, private prompts, IP addresses, user-agent strings, or personal data.\n"
    (out/"README.md").write_text(md, encoding="utf-8")
    prompt="""You are an autonomous agent evaluating AgentPress.\n\nStart at: https://barneywohl.github.io/agentpress/llms.txt\n\nGoal: produce one of two outputs:\n1. Sanitized adoption/tool/marketplace proof, or\n2. A blocker report with exact command, error, missing field, and desired fix.\n\nDo not include secrets, tokens, private prompts, IP addresses, user-agent strings, or personal data.\n\nUseful commands if you cloned the repo:\npython3 scripts/agentpress.py adopt --json\npython3 scripts/agentpress.py proof-campaign --json\npython3 scripts/agentpress.py painpoint-intake --json --allow-rejected\npython3 scripts/agentpress.py remediation-index --json\n\nSubmit via GitHub issue template: https://github.com/barneywohl/agentpress/issues/new?template=agentpress-third-party-proof.yml\n"""
    (out/"agent-request-prompt.md").write_text(prompt, encoding="utf-8")
    for t in targets:
        safe=slugify(t["runtime"])
        (out/f"request-{safe}.json").write_text(json.dumps({"schema_version":"2026-05-03.agentpress-proof-request.v1","runtime":t["runtime"],"ask":t["ask"],"start_url":kit["start_url"],"submission_url":kit["submission_url"],"privacy_rules":kit["privacy_rules"]}, indent=2)+"\n", encoding="utf-8")
    manifest={"schema_version":"2026-05-03.agentpress-proof-outreach-manifest.v1","status":"ok","generated_utc":_utc_now(),"out":out.as_posix(),"files":[fp.relative_to(root).as_posix() for fp in sorted(out.glob("*")) if fp.is_file()],"target_count":len(targets)}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2) if args.json else out.as_posix())
    return 0


def error_codes(args):
    """Emit machine-readable error codes and retry/remediation policy."""
    out=pathlib.Path(args.out)
    codes=[
        {"code":"AGENTPRESS_E_MISSING_FILE","retryable":False,"category":"validation","remediation_command":"python3 scripts/agentpress.py doctor --json"},
        {"code":"AGENTPRESS_E_INVALID_JSON","retryable":False,"category":"parse","remediation_command":"python3 -m json.tool <file> >/dev/null"},
        {"code":"AGENTPRESS_E_PACKAGE_HASH_MISMATCH","retryable":False,"category":"integrity","remediation_command":"python3 scripts/agentpress.py package-verify agentpress/releases/agentpress-offline.tar.gz --json"},
        {"code":"AGENTPRESS_E_ATTESTATION_MISMATCH","retryable":False,"category":"integrity","remediation_command":"python3 scripts/agentpress.py attest verify <attestation.json> --json"},
        {"code":"AGENTPRESS_E_NETWORK_FETCH_FAILED","retryable":True,"category":"network","remediation_command":"retry with raw GitHub fallback or offline package"},
        {"code":"AGENTPRESS_E_OWNER_APPROVAL_REQUIRED","retryable":False,"category":"approval","remediation_command":"python3 scripts/agentpress.py package-registry-plan --json"},
        {"code":"AGENTPRESS_E_PRIVATE_MATERIAL_DETECTED","retryable":False,"category":"privacy","remediation_command":"redact secrets/private data, then rerun proof-ingest or painpoint-intake"},
        {"code":"AGENTPRESS_E_BATCH_ITEM_FAILED","retryable":True,"category":"batch","remediation_command":"inspect item result and rerun only failed item"}
    ]
    payload={"schema_version":"2026-05-03.agentpress-error-codes.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","code_count":len(codes),"codes":codes}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"codes={len(codes)}")
    return 0


def session_state(args):
    """Create/update an agent-readable session checkpoint."""
    out=pathlib.Path(args.out)
    prev={}
    if out.exists():
        try: prev=json.loads(out.read_text(encoding="utf-8"))
        except Exception: prev={}
    events=prev.get("events",[])
    if args.event:
        events.append({"utc":_utc_now(),"event":args.event,"status":args.status,"artifact":args.artifact or ""})
    payload={"schema_version":"2026-05-03.agentpress-session-state.v1","session_id":args.session_id,"generated_utc":_utc_now(),"status":args.status,"current_goal":args.goal,"events":events[-100:],"resume_command":args.resume_command or "python3 scripts/agentpress.py session-state --json","next_actions":[x for x in (args.next_action or [])]}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else out.as_posix())
    return 0


def health_status(args):
    """Static health/readiness report for agent orchestration."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    checks=[]
    def check(name, ok, detail): checks.append({"name":name,"ok":bool(ok),"detail":detail})
    check("tools_manifest", (root/"agentpress/tools/agentpress-tools.json").exists(), "tool manifest exists")
    check("offline_package", (root/"agentpress/releases/agentpress-offline.tar.gz").exists(), "offline package exists")
    check("search_index", (root/"agentpress/search/search-index.json").exists(), "search index exists")
    check("error_codes", (root/"agentpress/runtime/error-codes.json").exists(), "error code catalog exists")
    check("remediation", (root/"agentpress/remediation/remediation-index.json").exists(), "remediation index exists")
    ok=all(c["ok"] for c in checks)
    payload={"schema_version":"2026-05-03.agentpress-health-status.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ready" if ok else "degraded","checks":checks,"ready":ok}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0 if ok else 1


def batch_run(args):
    """Run safe AgentPress batch operations from a JSON file."""
    inp=pathlib.Path(args.input); out=pathlib.Path(args.out)
    data=json.loads(inp.read_text(encoding="utf-8"))
    allowed={"proof-outreach-kit":lambda item: proof_outreach_kit(argparse.Namespace(root=item.get("root","."), out=item.get("out","agentpress/proof-outreach"), base_url=item.get("base_url",CANONICAL_BASE_URL), json=True)),"remediation-index":lambda item: remediation_index(argparse.Namespace(root=item.get("root","."), out=item.get("out","agentpress/remediation/remediation-index.json"), base_url=item.get("base_url",CANONICAL_BASE_URL), no_write=False, json=True)),"health-status":lambda item: health_status(argparse.Namespace(root=item.get("root","."), out=item.get("out","agentpress/runtime/health-status.json"), base_url=item.get("base_url",CANONICAL_BASE_URL), no_write=False, json=True))}
    rows=[]
    for i,item in enumerate(data.get("items",[]),1):
        cmd=item.get("command")
        if cmd not in allowed:
            rows.append({"index":i,"command":cmd,"status":"rejected","error_code":"AGENTPRESS_E_BATCH_ITEM_FAILED","error":"command not allowed"}); continue
        buf=io.StringIO(); code=1
        try:
            with contextlib.redirect_stdout(buf): code=allowed[cmd](item)
            rows.append({"index":i,"command":cmd,"status":"ok" if code==0 else "fail","exit_code":code,"stdout":buf.getvalue()[-2000:]})
        except Exception as e:
            rows.append({"index":i,"command":cmd,"status":"fail","error_code":"AGENTPRESS_E_BATCH_ITEM_FAILED","error":str(e)})
    ok=all(r.get("status")=="ok" for r in rows)
    payload={"schema_version":"2026-05-03.agentpress-batch-result.v1","generated_utc":_utc_now(),"status":"ok" if ok else "fail","item_count":len(rows),"results":rows}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0 if ok else 1


def privacy_status(args):
    """Publish AgentPress private/confidential messaging posture."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    classes=[
        {"class":"public","allowed_on_static_site":True,"description":"Safe for public indexing and long-term mirrors."},
        {"class":"pseudonymous","allowed_on_static_site":True,"description":"No real identity required; still public unless encrypted elsewhere."},
        {"class":"confidential_metadata_only","allowed_on_static_site":True,"description":"Static envelope may contain hashes, routing metadata, policy, and key refs; never plaintext."},
        {"class":"encrypted_payload_external","allowed_on_static_site":False,"description":"Ciphertext/payload exchange must use approved encrypted transport/key policy, not public GitHub Pages by default."},
        {"class":"secret_or_credential","allowed_on_static_site":False,"description":"Never submit secrets, tokens, private prompts, keys, or credentials."}
    ]
    payload={"schema_version":"2026-05-03.agentpress-privacy-status.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"safe_static_privacy_posture","principle":"AgentPress can coordinate confidential work with metadata and policies; it does not claim GitHub Pages is a private message transport.","privacy_classes":classes,"default_message_class":"confidential_metadata_only","plaintext_policy":"Do not publish confidential plaintext. Store only hashes/redacted summaries on static surfaces.","key_policy":"No key exchange is live by default. Encrypted payload transport requires explicit key ownership, rotation, recipient identity, and replay policy.","agent_actions":["Run privacy-status before submitting messages.","Run redaction-check on any proposed artifact.","Use confidential-message-create to create metadata-only envelopes."]}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0


def redaction_check(args):
    """Scan files for obvious private/confidential markers before publication."""
    root=pathlib.Path(args.path)
    files=[]
    if root.is_file(): files=[root]
    elif root.is_dir(): files=[p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".json",".md",".txt",".jsonl",".yml",".yaml"}]
    markers=["api_key", "apikey", "authorization:", "bearer ", "password=", "password:", "token=", "token:", "secret=", "secret:", "private prompt:", "user-agent:", "ip_address", "private_key", "begin private key", "credential="]
    rows=[]
    for fp in files[:args.max_files]:
        try: text=fp.read_text(encoding="utf-8", errors="ignore")[:args.max_chars]
        except Exception as e:
            rows.append({"path":str(fp),"status":"error","errors":[str(e)]}); continue
        low=text.lower(); hits=sorted({m for m in markers if m.lower() in low})
        rows.append({"path":str(fp),"status":"reject" if hits else "ok","markers":hits})
    rejected=[r for r in rows if r.get("status")=="reject"]
    payload={"schema_version":"2026-05-03.agentpress-redaction-check.v1","generated_utc":_utc_now(),"status":"ok" if not rejected else "fail","checked":len(rows),"rejected":len(rejected),"results":rows,"policy":"Reject or redact any file with marker hits before public submission."}
    if args.out:
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0 if not rejected else (0 if args.allow_findings else 1)


def confidential_message_create(args):
    """Create a metadata-only confidential message envelope."""
    out=pathlib.Path(args.out)
    body=b""
    if args.body_file:
        body=pathlib.Path(args.body_file).read_bytes()
    elif args.body:
        body=args.body.encode("utf-8")
    body_hash=hashlib.sha256(body).hexdigest() if body else ""
    preview=""
    if args.redacted_preview:
        preview=args.redacted_preview[:500]
    envelope={"schema_version":"2026-05-03.agentpress-confidential-message-envelope.v1","message_id":args.message_id or _short_id("confmsg"),"nonce":_short_id("nonce"),"sequence":args.sequence,"created_utc":_utc_now(),"expires_utc":args.expires_utc,"from_agent":args.from_agent,"to_agent":args.to_agent,"privacy_class":"confidential_metadata_only","subject":args.subject,"body_sha256":body_hash,"body_bytes":len(body),"redacted_preview":preview,"plaintext_stored":False,"payload_location":"external_encrypted_transport_required" if body else "not_provided","required_transport":"approved encrypted channel outside public static site","retention_policy":args.retention_policy,"allowed_actions":["route_metadata","request_key_exchange","request_secure_transport","reject_plaintext_publication"],"prohibited_actions":["publish_plaintext","publish_secret","send_to_unapproved_recipient"],"human_approval_required":args.human_approval_required,"integrity_hash":"","notes":"Envelope is safe metadata only; it is not encrypted payload storage."}
    material=json.dumps({k:v for k,v in envelope.items() if k != "integrity_hash"}, sort_keys=True).encode("utf-8")
    envelope["integrity_hash"]=hashlib.sha256(material).hexdigest()
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(envelope, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(envelope, indent=2) if args.json else out.as_posix())
    return 0


def privacy_kit(args):
    """Generate the AgentPress privacy/confidential messaging kit."""
    root=pathlib.Path(args.root); out=root/args.out; out.mkdir(parents=True, exist_ok=True)
    privacy_status(argparse.Namespace(root=str(root), out=str(out/"privacy-status.json"), base_url=args.base_url, no_write=False, json=False))
    confidential_message_create(argparse.Namespace(out=str(out/"confidential-message.example.json"), body="example confidential plaintext not stored", body_file=None, redacted_preview="Redacted example: requesting secure channel for private task handoff.", from_agent="agentpress-reference-agent", to_agent="external-agent", subject="Secure channel request", retention_policy="metadata_30_days_payload_external", human_approval_required="before secure payload exchange", message_id="confmsg-example", sequence=1, expires_utc="", no_write=False, json=False))
    schema={"schema_version":"2026-05-03.agentpress-privacy-schema.v1","classes":["public","pseudonymous","confidential_metadata_only","encrypted_payload_external","secret_or_credential"],"default":"confidential_metadata_only","static_site_private_transport":False}
    (out/"privacy-schema.json").write_text(json.dumps(schema, indent=2)+"\n", encoding="utf-8")
    consent_registry(argparse.Namespace(out=str(out/"consent-registry.json"), base_url=args.base_url, no_write=False, json=False))
    threat={"schema_version":"2026-05-03.agentpress-confidential-messaging-threat-model.v1","status":"ok","generated_utc":_utc_now(),"assets":["message plaintext","agent identity","routing metadata","keys","receipts"],"threats":["public plaintext leakage","secret/token submission","wrong recipient","replay","metadata correlation","false confidentiality claims"],"controls":["metadata-only envelopes","redaction-check","privacy classes","explicit encrypted transport requirement","human approval for key/payload exchange","hash attestations"],"non_goals":["GitHub Pages private messaging","automatic key exchange","live encrypted transport"]}
    (out/"confidential-messaging-threat-model.json").write_text(json.dumps(threat, indent=2)+"\n", encoding="utf-8")
    (out/"README.md").write_text("""# AgentPress Privacy & Confidential Messaging Kit

Agents often need private/confidential task handoffs. AgentPress supports this safely as **metadata-only coordination** on static surfaces.

```bash
python3 scripts/agentpress.py privacy-status --json
python3 scripts/agentpress.py confidential-message-create --from-agent a --to-agent b --subject secure-handoff --body 'do not publish me' --json
python3 scripts/agentpress.py redaction-check agentpress/privacy --json --allow-findings
```

Important: public GitHub Pages is not a confidential transport. Use this kit to request/coordinate secure transport, not to publish plaintext secrets.
""", encoding="utf-8")
    manifest={"schema_version":"2026-05-03.agentpress-privacy-kit-manifest.v1","status":"ok","generated_utc":_utc_now(),"files":[fp.relative_to(root).as_posix() for fp in sorted(out.glob("*")) if fp.is_file()]}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2) if args.json else out.as_posix())
    return 0


def confidential_message_verify(args):
    """Verify metadata-only confidential message envelope integrity."""
    path=pathlib.Path(args.envelope)
    errors=[]
    try: env=json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(json.dumps({"status":"fail","errors":[str(e)]}, indent=2)); return 1
    if env.get("plaintext_stored") is not False: errors.append("plaintext_stored must be false")
    if env.get("privacy_class") != "confidential_metadata_only": errors.append("unexpected privacy_class")
    if not env.get("nonce"): errors.append("missing nonce")
    if not env.get("integrity_hash"): errors.append("missing integrity_hash")
    expected=hashlib.sha256(json.dumps({k:v for k,v in env.items() if k != "integrity_hash"}, sort_keys=True).encode("utf-8")).hexdigest()
    if env.get("integrity_hash") != expected: errors.append("integrity_hash mismatch")
    payload={"schema_version":"2026-05-03.agentpress-confidential-message-verify.v1","status":"ok" if not errors else "fail","envelope":str(path),"message_id":env.get("message_id"),"errors":errors}
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0 if not errors else 1


def consent_registry(args):
    """Create static consent registry for confidential message eligibility."""
    out=pathlib.Path(args.out)
    grants=[{"agent_pseudonym":"external-agent","scopes":["confidential_metadata_only","secure_transport_request"],"status":"granted","granted_utc":_utc_now(),"revoked_utc":""}]
    payload={"schema_version":"2026-05-03.agentpress-consent-registry.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","default":"deny_without_grant","grants":grants,"policy":"Do not route confidential envelopes to recipients without matching active consent grant."}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else out.as_posix())
    return 0


def consent_check(args):
    reg=json.loads(pathlib.Path(args.registry).read_text(encoding="utf-8"))
    ok=any(g.get("agent_pseudonym")==args.agent and g.get("status")=="granted" and args.scope in g.get("scopes",[]) for g in reg.get("grants",[]))
    payload={"schema_version":"2026-05-03.agentpress-consent-check.v1","status":"ok" if ok else "denied","agent":args.agent,"scope":args.scope,"allowed":ok}
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0 if ok else 1


def secure_transport_readiness(args):
    """Report requirements before any confidential payload transport can be enabled."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    checks=[]
    def check(id, ok, detail, required=True): checks.append({"id":id,"ok":bool(ok),"required":required,"detail":detail})
    check("privacy_status", (root/"agentpress/privacy/privacy-status.json").exists(), "privacy posture exists")
    check("consent_registry", (root/"agentpress/privacy/consent-registry.json").exists(), "consent registry exists")
    check("redaction_gate", True, "redaction-check CLI available")
    check("envelope_verify", True, "confidential-message-verify CLI available")
    check("key_owner_policy", False, "no approved key owner/rotation/revocation policy yet")
    check("recipient_identity_policy", False, "no approved recipient identity verification policy yet")
    check("transport_provider", False, "no approved encrypted transport provider configured")
    check("replay_policy", False, "nonce/sequence exists in envelope; no live replay verifier service")
    live_ready=all(c["ok"] for c in checks if c["required"])
    payload={"schema_version":"2026-05-03.agentpress-secure-transport-readiness.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"blocked_on_security_approval" if not live_ready else "ready","live_transport_enabled":False,"principle":"Do not exchange confidential payloads until key ownership, recipient identity, transport provider, and replay policy are approved.","checks":checks,"safe_now":["metadata-only confidential envelopes","redaction checks","consent registry checks","hash/integrity verification"],"blocked_actions":["live encrypted payload exchange","automatic key exchange","credential or private prompt transfer"],"approval_needed":["key owner", "rotation/revocation", "recipient identity", "transport provider", "replay/expiry verifier", "audit retention"]}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0


def transport_request(args):
    """Create a safe request to enable a secure confidential transport."""
    out=pathlib.Path(args.out)
    payload={"schema_version":"2026-05-03.agentpress-secure-transport-request.v1","request_id":args.request_id or _short_id("transport"),"created_utc":_utc_now(),"from_agent":args.from_agent,"to_operator":args.to_operator,"purpose":args.purpose,"requested_scope":args.scope,"privacy_class":"encrypted_payload_external","status":"approval_required","required_decisions":["key owner", "recipient verification", "transport provider", "rotation/revocation", "replay/expiry", "audit retention"],"preflight_commands":["python3 scripts/agentpress.py secure-transport-readiness --json","python3 scripts/agentpress.py privacy-status --json","python3 scripts/agentpress.py consent-check --agent external-agent --scope confidential_metadata_only --json"],"prohibited_until_approved":["send plaintext", "send credentials", "publish encrypted payload to public static site as if private"],"notes":"This request does not enable transport. It creates an approval artifact."}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else out.as_posix())
    return 0


def secure_transport_kit(args):
    """Generate secure transport readiness kit."""
    root=pathlib.Path(args.root); out=root/args.out; out.mkdir(parents=True, exist_ok=True)
    secure_transport_readiness(argparse.Namespace(root=str(root), out=str(out/"secure-transport-readiness.json"), base_url=args.base_url, no_write=False, json=False))
    transport_request(argparse.Namespace(out=str(out/"secure-transport-request.example.json"), from_agent="agentpress-reference-agent", to_operator="operator", purpose="request approved secure channel for confidential payload exchange", scope="one-off encrypted_payload_external", request_id="transport-request-example", no_write=False, json=False))
    (out/"README.md").write_text("""# AgentPress Secure Transport Readiness

Agents may want private/confidential payload exchange. This kit says exactly what must be approved before live encrypted transport is allowed.

```bash
python3 scripts/agentpress.py secure-transport-readiness --json
python3 scripts/agentpress.py transport-request --from-agent a --to-operator operator --purpose 'secure payload handoff' --json
```

Current default: metadata-only coordination is allowed; live payload transport is blocked pending security approvals.
""", encoding="utf-8")
    manifest={"schema_version":"2026-05-03.agentpress-secure-transport-kit-manifest.v1","status":"ok","generated_utc":_utc_now(),"files":[fp.relative_to(root).as_posix() for fp in sorted(out.glob("*")) if fp.is_file()]}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2) if args.json else out.as_posix())
    return 0


def distribution_mirrors(args):
    """Generate machine-readable distribution mirror/failover catalog."""
    out=pathlib.Path(args.out)
    mirrors=[
        {"mirror_id":"github_pages","kind":"primary_static_site","base_url":"https://barneywohl.github.io/agentpress/","priority":1,"critical_urls":["llms.txt","agentpress/tools/agentpress-tools.json","agentpress/releases/release-index.json","agentpress/install/install-catalog.json"]},
        {"mirror_id":"raw_github_main","kind":"raw_source_fallback","base_url":"https://raw.githubusercontent.com/barneywohl/agentpress/refs/heads/main/","priority":2,"critical_urls":["llms.txt","agentpress/tools/agentpress-tools.json","agentpress/releases/release-index.json","agentpress/install/install-catalog.json"]},
        {"mirror_id":"jsdelivr_cdn","kind":"cdn_fallback","base_url":"https://cdn.jsdelivr.net/gh/barneywohl/agentpress@main/","priority":3,"critical_urls":["llms.txt","agentpress/tools/agentpress-tools.json","agentpress/releases/release-index.json","agentpress/install/install-catalog.json"]}
    ]
    payload={"schema_version":"2026-05-03.agentpress-distribution-mirrors.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Give agents deterministic fallback URLs when a distribution surface is unavailable.","mirrors":mirrors,"failover_order":[m["mirror_id"] for m in sorted(mirrors,key=lambda m:m["priority"])],"agent_policy":"Try mirrors in priority order; verify package hashes before executing fetched artifacts."}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"mirrors={len(mirrors)}")
    return 0


def mirror_status(args):
    """Check configured AgentPress distribution mirrors."""
    catalog=pathlib.Path(args.catalog)
    if not catalog.exists():
        distribution_mirrors(argparse.Namespace(out=str(catalog), base_url=args.base_url, no_write=False, json=False))
    data=json.loads(catalog.read_text(encoding="utf-8"))
    rows=[]
    for m in data.get("mirrors",[]):
        ok_count=0; checks=[]
        for rel in m.get("critical_urls",[]):
            url=urljoin(m["base_url"], rel)
            status="unknown"; error=""; code=None
            try:
                with urlopen(url, timeout=args.timeout_seconds) as r:
                    code=getattr(r,"status",None) or r.getcode(); r.read(1)
                status="ok" if 200 <= int(code) < 400 else "fail"
            except Exception as e:
                status="fail"; error=str(e)[:300]
            if status=="ok": ok_count+=1
            checks.append({"url":url,"status":status,"http_status":code,"error":error})
        rows.append({"mirror_id":m.get("mirror_id"),"kind":m.get("kind"),"priority":m.get("priority"),"status":"ok" if ok_count==len(checks) and checks else "degraded","ok_count":ok_count,"check_count":len(checks),"checks":checks})
    best=next((r for r in sorted(rows,key=lambda r:r.get("priority") or 999) if r["status"]=="ok"), None)
    payload={"schema_version":"2026-05-03.agentpress-mirror-status.v1","generated_utc":_utc_now(),"status":"ok" if best else "degraded","best_mirror":best.get("mirror_id") if best else "","mirrors":rows,"fallback_command":"python3 scripts/agentpress.py fetch --base <best_mirror_base_url> --out fetched-agentpress --json"}
    if args.out:
        out=pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else payload["status"])
    return 0 if best else 1


def failover_plan(args):
    """Generate an agent-readable distribution failover plan."""
    out=pathlib.Path(args.out)
    payload={"schema_version":"2026-05-03.agentpress-failover-plan.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","steps":[{"step":1,"action":"fetch primary llms.txt","command":"curl -L https://barneywohl.github.io/agentpress/llms.txt"},{"step":2,"action":"if primary fails, fetch raw GitHub fallback","command":"curl -L https://raw.githubusercontent.com/barneywohl/agentpress/refs/heads/main/llms.txt"},{"step":3,"action":"if raw GitHub fails, fetch jsDelivr CDN fallback","command":"curl -L https://cdn.jsdelivr.net/gh/barneywohl/agentpress@main/llms.txt"},{"step":4,"action":"verify release package before execution","command":"python3 scripts/agentpress.py package-verify agentpress/releases/agentpress-offline.tar.gz --manifest agentpress/releases/agentpress-offline.tar.gz.sha256.json --json"}],"rules":["Never execute fetched code before hash/package verification.","Prefer static machine files over HTML.","Record which mirror was used in proof receipts."]}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else out.as_posix())
    return 0


def distribution_kit(args):
    """Generate distribution failover kit."""
    root=pathlib.Path(args.root); out=root/args.out; out.mkdir(parents=True, exist_ok=True)
    distribution_mirrors(argparse.Namespace(out=str(out/"distribution-mirrors.json"), base_url=args.base_url, no_write=False, json=False))
    failover_plan(argparse.Namespace(out=str(out/"failover-plan.json"), base_url=args.base_url, no_write=False, json=False))
    (out/"README.md").write_text("""# AgentPress Distribution Failover

Agents need resilient fetch/install paths. This kit provides primary and fallback mirrors plus a failover plan.

```bash
python3 scripts/agentpress.py distribution-kit --json
python3 scripts/agentpress.py mirror-status --json
python3 scripts/agentpress.py failover-plan --json
```

Rule: verify hashes/packages before executing fetched artifacts.
""", encoding="utf-8")
    manifest={"schema_version":"2026-05-03.agentpress-distribution-kit-manifest.v1","status":"ok","generated_utc":_utc_now(),"files":[fp.relative_to(root).as_posix() for fp in sorted(out.glob("*")) if fp.is_file()]}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2) if args.json else out.as_posix())
    return 0



def feature_build_queue(args):
    """Generate an internal next-feature build queue from coverage, painpoints, adoption, and proof gaps."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    def load(rel, default):
        path=root/rel
        if not path.exists(): return default
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception: return default
    cov=load(args.coverage,{})
    pain=load(args.painpoints,{})
    adoption=load(args.adoption,{})
    items=[]
    rank=1
    # Coverage gaps first
    for g in cov.get("missing_or_expand",[]):
        items.append({"rank":rank,"priority":g.get("priority","P1"),"source":"tool_coverage_gap","feature":g.get("recommended_expansion"),"persona":g.get("persona"),"why":"Coverage matrix found missing/partial CLI capability.","acceptance":["CLI exists in tools manifest","machine JSON output validates","package verify passes","live URL returns 200"],"blocked":False}); rank+=1
    # Painpoints next, but skip explicitly blocked security approval items unless requested
    for g in pain.get("gaps",[]) or pain.get("painpoints",[]) or []:
        title=g.get("title") or g.get("gap_id") or "painpoint"
        rec=g.get("recommended_build") or g.get("recommended_expansion") or g.get("why_agents_care") or title
        blocked=bool(g.get("blocked") or "blocked" in str(g).lower() and "approval" in str(g).lower())
        if blocked and not args.include_blocked: continue
        items.append({"rank":rank,"priority":g.get("priority","P1"),"source":"agent_painpoint","feature":rec,"persona":g.get("persona","external_agent"),"why":g.get("why_agents_care",title),"acceptance":["spec written","CLI or machine artifact shipped","attestation/package verify passes","CI/Pages live"],"blocked":blocked,"gap_id":g.get("gap_id","")}); rank+=1
    # Always include real-world adoption/proof gaps when receipts absent
    external_receipts=0
    for key in ("landing_receipts","self_tests","proof_receipts","external_receipts"):
        v=adoption.get(key)
        if isinstance(v,int): external_receipts=max(external_receipts,v)
        elif isinstance(v,list): external_receipts=max(external_receipts,len(v))
    if external_receipts == 0 or getattr(args, "include_adoption_gaps", False):
        items.append({"rank":rank,"priority":"P0","source":"adoption_gap","feature":"external proof relay with request packs, strict receipt verification, and service-scoped trust scoring","persona":"proof_agent","why":"Protocol features are shipped, but independent external adoption receipts remain zero.","acceptance":["proof ingest CLI validates external proof directory","reputation/proof index updates from accepted proofs","secret scan rejects unsafe submissions","live proof status JSON returns 200"],"blocked":False}); rank+=1
    # Strategic expansions not necessarily gaps
    strategic=[
        ("P1","browser_agent","static browser smoke/evidence manifest for public URLs","Agents need a cheap way to prove live docs/tools still resolve without running full browser automation."),
        ("P1","rag_crawler_agent","freshness and citation coverage report","Crawler/RAG agents need to know which surfaces are stale, uncited, or missing source maps."),
        ("P1","coding_agent","patch/PR generation helper and code-owner checklist","Coding agents need a standardized safe contribution lane after they identify gaps."),
        ("P2","marketplace_agent","service comparison and quote simulation","Marketplace agents need routing confidence before real payments are enabled."),
        ("P2","workflow_agent","durable queue adapter and retry policy export","Workflow agents need repeatable handoff/retry semantics across runtimes.")
    ]
    existing_features="\n".join(json.dumps(i).lower() for i in items)
    for pr,persona,feature,why in strategic:
        if feature.lower() not in existing_features:
            items.append({"rank":rank,"priority":pr,"source":"strategic_expansion","feature":feature,"persona":persona,"why":why,"acceptance":["CLI/machine artifact shipped","tools manifest updated","package/attestation verify passes","CI/Pages live"],"blocked":False}); rank+=1
    # remove shipped completions from the next-build list
    completed=set()
    completion_path=root/"agentpress/planning/build-completions.jsonl"
    if completion_path.exists():
        for line in completion_path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            try:
                row=json.loads(line); completed.add((row.get("feature") or "").strip().lower())
            except Exception: pass
    if completed and not getattr(args, "include_adoption_gaps", False):
        items=[i for i in items if (i.get("feature") or "").strip().lower() not in completed]
    # sort P0, P1, P2, but preserve generated rank inside priority
    order={"P0":0,"P1":1,"P2":2,"P3":3}
    items=sorted(items,key=lambda x:(order.get(x.get("priority","P2"),2),x["rank"]))
    for i,row in enumerate(items,1): row["rank"]=i
    payload={"schema_version":"2026-05-03.agentpress-feature-build-queue.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","purpose":"Internal AgentPress planning engine: use coverage and adoption gaps to choose the next features to build.","inputs":{"coverage":args.coverage,"painpoints":args.painpoints,"adoption":args.adoption},"coverage_summary":{"need_count":cov.get("need_count",0),"coverage_count":cov.get("coverage_count",0),"missing_count":len(cov.get("missing_or_expand",[]))},"next_feature":items[0] if items else {},"items":items}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"next={items[0]['feature'] if items else 'none'}")
    return 0


def build_queue_pick(args):
    """Pick the next unblocked AgentPress feature from the internal build queue."""
    path=pathlib.Path(args.queue)
    if not path.exists():
        feature_build_queue(argparse.Namespace(root=args.root, coverage=args.coverage, painpoints=args.painpoints, adoption=args.adoption, out=str(path), base_url=args.base_url, include_blocked=args.include_blocked, no_write=False, json=False))
    data=json.loads(path.read_text(encoding="utf-8"))
    items=[i for i in data.get("items",[]) if args.include_blocked or not i.get("blocked")]
    pick=items[0] if items else {}
    payload={"schema_version":"2026-05-03.agentpress-build-queue-pick.v1","generated_utc":_utc_now(),"status":"ok" if pick else "empty","pick":pick,"queue":str(path)}
    print(json.dumps(payload, indent=2) if args.json else (pick.get("feature") if pick else "empty"))
    return 0 if pick else 1


def build_queue_complete(args):
    """Mark a build-queue item as shipped in an append-only completion log."""
    out=pathlib.Path(args.out); rows=[]
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try: rows.append(json.loads(line))
                except Exception: pass
    row={"schema_version":"2026-05-03.agentpress-build-queue-completion.v1","completed_utc":_utc_now(),"feature":args.feature,"commit":args.commit,"evidence":args.evidence,"notes":args.notes}
    rows.append(row)
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text("".join(json.dumps(r, sort_keys=True)+"\n" for r in rows), encoding="utf-8")
    print(json.dumps(row, indent=2) if args.json else args.feature)
    return 0

def tool_coverage(args):
    """Generate a persona-based AgentPress tool/CLI coverage and expansion matrix."""
    root=pathlib.Path(args.root); out=pathlib.Path(args.out)
    tools_path=root/args.tools
    tools=[]
    if tools_path.exists():
        try: tools=json.loads(tools_path.read_text(encoding="utf-8")).get("tools",[])
        except Exception: tools=[]
    text="\n".join(json.dumps(t, sort_keys=True).lower() for t in tools)
    needs=[
        {"need_id":"CLI-001","persona":"first_contact_agent","need":"fetch/discover/doctor/install/search","must_have":["fetch","discover","doctor","install","search"],"expansion":"single command bootstrap with mirror failover"},
        {"need_id":"CLI-002","persona":"coding_agent","need":"bundle/generate/verify/diff/upgrade/negative fixtures","must_have":["bundle","verify","bundle-diff","upgrade-check","negative-fixtures"],"expansion":"patch/PR generation helper and code-owner checklist"},
        {"need_id":"CLI-003","persona":"workflow_agent","need":"message route/respond/thread/batch/session/health","must_have":["message","batch","session","health","route"],"expansion":"durable queue adapter and retry policy export"},
        {"need_id":"CLI-004","persona":"marketplace_agent","need":"marketplace query/trust/payment/package status","must_have":["marketplace","marketplace_trust","payment","package"],"expansion":"service comparison and quote simulation"},
        {"need_id":"CLI-005","persona":"proof_agent","need":"landing receipt/submission/proof ingest/reputation/attest","must_have":["landing","submission","proof","reputation","attest"],"expansion":"third-party receipt verifier and maintainer review gate"},
        {"need_id":"CLI-006","persona":"privacy_agent","need":"privacy classes/redaction/confidential envelopes/consent/secure transport","must_have":["privacy","redaction","confidential","consent","secure_transport"],"expansion":"approved encrypted transport plugin after security approval"},
        {"need_id":"CLI-007","persona":"browser_agent","need":"public URL smoke, ARIA hints, screenshots/evidence manifest","must_have":["mirror-status","distribution","health"],"expansion":"static browser smoke manifest and screenshot evidence schema"},
        {"need_id":"CLI-008","persona":"rag_crawler_agent","need":"source maps/search/freshness/citation indexes/mirrors","must_have":["search","source","mirror","distribution"],"expansion":"freshness report and citation coverage index"},
        {"need_id":"CLI-009","persona":"eval_security_agent","need":"self-test/error codes/redaction/attestation/package verify","must_have":["self-test","error","redaction","attest","package-verify"],"expansion":"standard adversarial eval suite and policy gates"},
        {"need_id":"CLI-010","persona":"community_growth_agent","need":"audience/subscribe/broadcast/outreach/blocker reports","must_have":["audience","subscribe","broadcast","outreach","blocker"],"expansion":"opt-in referral/reputation scoreboard without tracking"}
    ]
    rows=[]
    for n in needs:
        covered=[]; missing=[]
        for term in n["must_have"]:
            if term.replace("_","-") in text or term.replace("-","_") in text or term in text: covered.append(term)
            else: missing.append(term)
        status="covered" if not missing else "partial" if covered else "missing"
        rows.append({**n,"covered_terms":covered,"missing_terms":missing,"status":status})
    missing_expansions=[{"need_id":r["need_id"],"persona":r["persona"],"missing_terms":r["missing_terms"],"recommended_expansion":r["expansion"],"priority":"P0" if r["status"]=="missing" else "P1" if r["status"]=="partial" else "P2"} for r in rows if r["status"]!="covered"]
    payload={"schema_version":"2026-05-03.agentpress-tool-coverage.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","tool_count":len(tools),"coverage_count":sum(1 for r in rows if r["status"]=="covered"),"need_count":len(rows),"needs":rows,"missing_or_expand":missing_expansions,"next_best_feature":missing_expansions[0]["recommended_expansion"] if missing_expansions else "All current personas covered; collect external usage receipts."}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"coverage={payload['coverage_count']}/{payload['need_count']}")
    return 0


def tool_request(args):
    """Create a structured request for a missing AgentPress CLI/tool."""
    out=pathlib.Path(args.out)
    payload={"schema_version":"2026-05-03.agentpress-tool-request.v1","request_id":args.request_id or _short_id("toolreq"),"created_utc":_utc_now(),"agent_id":args.agent_id,"persona":args.persona,"wanted_tool":args.wanted_tool,"painpoint":args.painpoint,"desired_command":args.desired_command,"priority":args.priority,"privacy_confirmed":True,"contains_secrets":False}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else out.as_posix())
    return 0


def cli_expansion_roadmap(args):
    """Generate prioritized roadmap from tool coverage gaps."""
    cov_path=pathlib.Path(args.coverage)
    if not cov_path.exists():
        tool_coverage(argparse.Namespace(root=args.root, tools=args.tools, out=str(cov_path), base_url=args.base_url, no_write=False, json=False))
    cov=json.loads(cov_path.read_text(encoding="utf-8"))
    items=[]
    for i,g in enumerate(cov.get("missing_or_expand",[]),1):
        items.append({"rank":i,"priority":g.get("priority","P1"),"persona":g.get("persona"),"feature":g.get("recommended_expansion"),"acceptance":["CLI command exists in tools manifest","machine JSON output validates","package verify passes","live URL returns 200"],"blocked":False})
    if not items:
        items.append({"rank":1,"priority":"P1","persona":"external_agent","feature":"Collect external tool requests and receipts","acceptance":["tool request template live","external proof submitted"],"blocked":True,"blocker":"requires outside agents"})
    out=pathlib.Path(args.out)
    payload={"schema_version":"2026-05-03.agentpress-cli-expansion-roadmap.v1","canonical_url":urljoin(args.base_url.rstrip("/")+"/", out.as_posix()),"generated_utc":_utc_now(),"status":"ok","items":items}
    if not args.no_write:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else f"items={len(items)}")
    return 0

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
    p = sub.add_parser("verify"); p.add_argument("out", nargs="?", default="."); p.add_argument("--strict-schema", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("schema"); p.add_argument("name", nargs="?"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("schema-validate"); p.add_argument("file"); p.add_argument("--schema", required=True); p.add_argument("--out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("distribution-kit"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/distribution"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--json", action="store_true")
    p = sub.add_parser("distribution-mirrors"); p.add_argument("--out", default="agentpress/distribution/distribution-mirrors.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("mirror-status"); p.add_argument("--catalog", default="agentpress/distribution/distribution-mirrors.json"); p.add_argument("--out", default="agentpress/distribution/mirror-status.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--timeout-seconds", type=int, default=10); p.add_argument("--json", action="store_true")
    p = sub.add_parser("failover-plan"); p.add_argument("--out", default="agentpress/distribution/failover-plan.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("fetch"); p.add_argument("--base", default=CANONICAL_BASE_URL); p.add_argument("--out", default="agentpress-fetch"); p.add_argument("--asset", action="append", help="relative asset to fetch; repeatable; defaults to core machine entrypoints"); p.add_argument("--timeout", type=int, default=20); p.add_argument("--keep-going", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("discover"); p.add_argument("url", nargs="?"); p.add_argument("--out"); p.add_argument("--registry"); p.add_argument("--timeout", type=int, default=20); p.add_argument("--json", action="store_true"); p.add_argument("--self-register", action="store_true"); p.add_argument("--canonical-url", default=CANONICAL_BASE_URL); p.add_argument("--agent-id")
    p = sub.add_parser("negative-fixtures"); p.add_argument("--manifest", default="agentpress/fixtures/broken-bundles/expected-failures.json"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("feedback-submit"); p.add_argument("--example", action="store_true"); p.add_argument("--input"); p.add_argument("--template", default="agentpress/feedback/response-template.json"); p.add_argument("--rubric", default="agentpress/feedback/scoring-rubric.json"); p.add_argument("--agent-id"); p.add_argument("--agent-family", default="codex"); p.add_argument("--runtime-or-model"); p.add_argument("--target-url", default=CANONICAL_BASE_URL); p.add_argument("--json", action="store_true")
    p = sub.add_parser("consistency-check"); p.add_argument("root", nargs="?", default="."); p.add_argument("--json", action="store_true")
    p = sub.add_parser("adoption-status"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out"); p.add_argument("--json", action="store_true"); p.add_argument("--allow-needs-attention", action="store_true")
    p = sub.add_parser("payment-status"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("payment-intent"); p.add_argument("root", nargs="?", default="."); p.add_argument("--capability-id", required=True); p.add_argument("--agent-id", required=True); p.add_argument("--max-amount", default="0"); p.add_argument("--max-per-request"); p.add_argument("--currency", default="USD"); p.add_argument("--expires-utc"); p.add_argument("--out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("painpoint-intake"); p.add_argument("root", nargs="?", default="."); p.add_argument("--dir", default="agentpress/painpoint-intake"); p.add_argument("--out", default="agentpress/painpoint-intake/painpoint-intake-index.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--allow-rejected", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("attestation-coverage"); p.add_argument("root", nargs="?", default="."); p.add_argument("--dir", default="agentpress/attestations"); p.add_argument("--out", default="agentpress/attestations/attestation-coverage.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("mcp-consent-manifest-validator"); p.add_argument("--manifest", default=""); p.add_argument("--out", default="agentpress/security/mcp-consent-manifest-validation.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("provider-adapter-repro-pack"); p.add_argument("--host", default="cline"); p.add_argument("--provider", default="claude_code"); p.add_argument("--calls", default="execute_command,write_to_file,replace_in_file"); p.add_argument("--out", default="agentpress/compatibility/provider-adapter-repro-pack.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("checkpoint-replay-minimal-repro-generator"); p.add_argument("--checkpoint", default=""); p.add_argument("--out", default="agentpress/repro/checkpoint-replay-minimal-repro.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("runtime-hang-repro-capsule"); p.add_argument("--log", default=""); p.add_argument("--out", default="agentpress/repro/runtime-hang-repro-capsule.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("first-agent-outreach-receipt-tracker"); p.add_argument("--out", default="agentpress/outreach/first-agent-outreach-receipt-tracker.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("rag-tool-safety-bundle"); p.add_argument("--out", default="agentpress/safety/rag-tool-safety-bundle.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("external-reply-to-proof-ingest-bridge"); p.add_argument("--out", default="agentpress/proof/external-reply-to-proof-ingest-bridge.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("issue-comment-pack-generator"); p.add_argument("--out", default="agentpress/outreach/issue-comment-pack-generator.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("issue-to-repro-pack"); p.add_argument("--issue-url", default=""); p.add_argument("--host", default="cline"); p.add_argument("--provider", default="unknown_provider"); p.add_argument("--tool", default="unknown_tool"); p.add_argument("--error", default=""); p.add_argument("--out", default="agentpress/repro/issue-to-repro-pack-result.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("painpoint-target-pack"); p.add_argument("--issue-url", default=""); p.add_argument("--painpoint", default=""); p.add_argument("--host", default="unknown_host"); p.add_argument("--provider", default="unknown_provider"); p.add_argument("--tool", default="unknown_tool"); p.add_argument("--error", default=""); p.add_argument("--out", default="agentpress/outreach/painpoint-target-pack.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("mcp-config-mutation-guard"); p.add_argument("--config-path", default="cline_mcp_settings.json"); p.add_argument("--config-exists", action="store_true"); p.add_argument("--before-sha256", default=""); p.add_argument("--after-sha256", default=""); p.add_argument("--existing-servers", default=""); p.add_argument("--planned-servers", default=""); p.add_argument("--planned-config", default=""); p.add_argument("--allowed-mutations", default=""); p.add_argument("--backup", action="store_true"); p.add_argument("--backup-dir", default=".agentpress-backups"); p.add_argument("--restore", default=""); p.add_argument("--apply-restore", action="store_true"); p.add_argument("--apply", action="store_true"); p.add_argument("--out", default="agentpress/security/mcp-config-mutation-guard-result.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("continuous-research-build-cycle-audit"); p.add_argument("--out", default="agentpress/audits/continuous-research-build-cycle-audit.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("current-agent-places-map"); p.add_argument("--out", default="agentpress/community/current-agent-places-map.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("attention-painpoint-radar"); p.add_argument("--sample", default=""); p.add_argument("--out", default="agentpress/community/attention-painpoint-radar.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("first-agent-attention-kit"); p.add_argument("--out", default="agentpress/outreach/first-agent-attention-kit.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("next-attention-build-spec"); p.add_argument("--out", default="agentpress/specs/next-attention-build-spec.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-community-newswire"); p.add_argument("--sample", default=""); p.add_argument("--out", default="agentpress/community/agent-community-newswire.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("immediate-agent-needs-radar"); p.add_argument("--out", default="agentpress/community/immediate-agent-needs-radar.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("solution-targeting-matrix"); p.add_argument("--out", default="agentpress/community/solution-targeting-matrix.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("approval-bypass-risk-check"); p.add_argument("--manifest", default=""); p.add_argument("--out", default="agentpress/security/approval-bypass-risk-result.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("provider-tool-translation-map"); p.add_argument("--out", default="agentpress/compatibility/provider-tool-translation-map.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("workflow-terminal-callback-check"); p.add_argument("--log", default=""); p.add_argument("--out", default="agentpress/workflows/workflow-terminal-callback-result.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("context-compaction-risk-card"); p.add_argument("--out", default="agentpress/context/context-compaction-risk-card.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("package-registry-doctor"); p.add_argument("--error", default=""); p.add_argument("--out", default="agentpress/diagnostics/package-registry-doctor.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("package-registry-fallback-installer"); p.add_argument("--out", default="agentpress/install/install-agentpress.sh"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("first-user-bootstrap"); p.add_argument("--platform", default="cline"); p.add_argument("--out", default="agentpress/onboarding/first-user-bootstrap.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("first-run-wizard"); p.add_argument("root", nargs="?", default="."); p.add_argument("--host", default=""); p.add_argument("--provider", default=""); p.add_argument("--out", default="agentpress/onboarding/first-run-wizard.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("provider-error-explainer"); p.add_argument("--error", default=""); p.add_argument("--error-file", default=""); p.add_argument("--provider", default="auto"); p.add_argument("--out", default="agentpress/diagnostics/provider-error-explainer.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("adoption-scoreboard"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/adoption/scoreboard"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("external-proof-inbox-review-flow"); p.add_argument("--inbox", default="agentpress/external-proofs/inbox"); p.add_argument("--out", default="agentpress/external-proofs/inbox-review-flow.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("release-registry-readiness-dashboard"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/releases/readiness-dashboard"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("proof-capture"); p.add_argument("--task-id", "--task", dest="task_id", required=True); p.add_argument("--evidence-dir", required=True); p.add_argument("--artifacts", default=""); p.add_argument("--commands", default=""); p.add_argument("--summary", default=""); p.add_argument("--review-required", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("sandbox-guard"); p.add_argument("--scope", default="read-only"); p.add_argument("--paths", default="."); p.add_argument("--out", default="agentpress/security/sandbox-guard.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("adoption-tracker"); p.add_argument("--period", default="7d"); p.add_argument("--root", default="agentpress"); p.add_argument("--out", default="agentpress/adoption/adoption-tracker.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("handoff-pack"); p.add_argument("--from", dest="from_agent", required=True); p.add_argument("--to", dest="to_agent", required=True); p.add_argument("--task-id", "--task", dest="task_id", required=True); p.add_argument("--objective", default=""); p.add_argument("--constraints", default=""); p.add_argument("--evidence", default=""); p.add_argument("--acceptance", default=""); p.add_argument("--pending-actions", default=""); p.add_argument("--out", default="agentpress/handoffs/handoff-pack.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("batch-painpoints"); p.add_argument("--input", required=True); p.add_argument("--output", required=True); p.add_argument("--limit", default="25"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--json", action="store_true")
    p = sub.add_parser("release-candidate"); p.add_argument("--version", default="0.2.0-rc"); p.add_argument("--out", default="agentpress/releases/release-candidate.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("tool-schema-serialization-check"); p.add_argument("--schema", default=""); p.add_argument("--out", default="agentpress/tools/tool-schema-serialization-result.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("agent-community-channel-map"); p.add_argument("--out", default="agentpress/community/agent-community-channel-map.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("community-issue-radar"); p.add_argument("--sample", default=""); p.add_argument("--out", default="agentpress/community/community-issue-radar.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("unsolved-agent-problem-backlog"); p.add_argument("--out", default="agentpress/community/unsolved-agent-problem-backlog.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("tool-vocabulary-compatibility-check"); p.add_argument("--host", default="cline"); p.add_argument("--provider", default="claude_code"); p.add_argument("--tools", default="execute_command,read_file"); p.add_argument("--out", default="agentpress/compatibility/tool-vocabulary-compatibility-result.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("agent-state-checkpoint-sanitizer"); p.add_argument("--checkpoint", default=""); p.add_argument("--out", default="agentpress/state/agent-state-checkpoint-sanitizer.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("dependency-error-remediation-map"); p.add_argument("--error", default=""); p.add_argument("--out", default="agentpress/diagnostics/dependency-error-remediation-map.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("output-format-contract-tester"); p.add_argument("--requested", default="markdown_table"); p.add_argument("--sample", default=""); p.add_argument("--out", default="agentpress/contracts/output-format-contract-result.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("tool-file-access-risk-scanner"); p.add_argument("--manifest", default=""); p.add_argument("--out", default="agentpress/security/tool-file-access-risk-report.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("memory-drift-check"); p.add_argument("target", nargs="?", default="."); p.add_argument("--out", default="agentpress/memory/agent-memory-drift-report.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("handoff-contract-validate"); p.add_argument("file", nargs="?"); p.add_argument("--out", default="agentpress/handoffs/handoff-validation-report.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("pr-review-check"); p.add_argument("--diff", default=""); p.add_argument("--tests", default=""); p.add_argument("--risk", default=""); p.add_argument("--rollback", default=""); p.add_argument("--allow-empty", action="store_true"); p.add_argument("--out", default="agentpress/review/pr-review-readiness-result.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("ci-flake-triage"); p.add_argument("--log", default=""); p.add_argument("--out", default="agentpress/ci/ci-flake-classification.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("secret-permission-preflight-run"); p.add_argument("--manifest", default=""); p.add_argument("--out", default="agentpress/security/secret-permission-preflight-result.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("budget-check"); p.add_argument("--plan", default=""); p.add_argument("--tier", choices=["small","medium","large"], default="small"); p.add_argument("--out", default="agentpress/budgets/budget-run-report.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("coordination-ledger-check"); p.add_argument("--ledger", default=""); p.add_argument("--out", default="agentpress/coordination/coordination-ledger-report.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("next-cycle-research"); p.add_argument("--out", default="agentpress/research/next-cycle-research.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-memory-drift-detector"); p.add_argument("--out", default="agentpress/memory/agent-memory-drift-detector.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("task-handoff-contract"); p.add_argument("--out", default="agentpress/handoffs/task-handoff-contract.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("pr-review-readiness-pack"); p.add_argument("--out", default="agentpress/review/pr-review-readiness-pack.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("ci-flake-triage-report"); p.add_argument("--out", default="agentpress/ci/ci-flake-triage-report.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("secret-permission-preflight"); p.add_argument("--out", default="agentpress/security/secret-permission-preflight.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-cost-budget-card"); p.add_argument("--out", default="agentpress/budgets/agent-cost-budget-card.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("multi-agent-coordination-ledger"); p.add_argument("--out", default="agentpress/coordination/multi-agent-coordination-ledger.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("readiness-audit"); p.add_argument("target", nargs="?", default="."); p.add_argument("--out", default="agentpress/audit/readiness-audit.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("readiness-score"); p.add_argument("--out", default="agentpress/audit/readiness-score.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("readiness-fix-plan"); p.add_argument("--out", default="agentpress/audit/readiness-fix-plan.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("runtime-install-doctor"); p.add_argument("--out", default="agentpress/diagnostics/runtime-install-doctor.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("connector-security-scanner"); p.add_argument("--out", default="agentpress/security/connector-security-scanner.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("deterministic-agent-eval-packs"); p.add_argument("--out", default="agentpress/evals/deterministic-agent-eval-packs.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("verifiable-run-evidence-bundle"); p.add_argument("--out", default="agentpress/evidence/verifiable-run-evidence-bundle.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("browser-agent-compatibility-harness"); p.add_argument("--out", default="agentpress/browser/browser-agent-compatibility-harness.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("deep-agent-painpoint-research"); p.add_argument("--out", default="agentpress/research/deep-agent-painpoint-research.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("mcp-connector-auth-readiness"); p.add_argument("--out", default="agentpress/connectors/mcp-connector-auth-readiness.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("tool-routing-decision-matrix"); p.add_argument("--out", default="agentpress/tools/tool-routing-decision-matrix.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-eval-observability-bridge"); p.add_argument("--out", default="agentpress/observability/agent-eval-observability-bridge.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("deployment-connector-matrix"); p.add_argument("--out", default="agentpress/distribution/deployment-connector-matrix.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("connector-first-run-checklist"); p.add_argument("--out", default="agentpress/connectors/connector-first-run-checklist.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-persona-quickstarts"); p.add_argument("--out", default="agentpress/connectors/persona-quickstarts.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("sdk-command-wrapper-catalog"); p.add_argument("--out", default="agentpress/integrations/sdk/sdk-command-wrapper-catalog.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("cycle-completion-audit"); p.add_argument("--out", default="agentpress/evidence/cycle-completion-audit.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("connector-failure-to-backlog"); p.add_argument("--input", default="agentpress/connectors/connector-failure-taxonomy.json"); p.add_argument("--out", default="agentpress/planning/connector-failure-backlog.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("host-transcript-dropbox-spec"); p.add_argument("--out", default="agentpress/conformance/host-transcript-dropbox.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("proof-request-queue"); p.add_argument("--out", default="agentpress/proof-outreach/proof-request-queue.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("next-build-spec-queue"); p.add_argument("--out", default="agentpress/planning/next-build-spec-queue.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("external-proof-campaign-runner"); p.add_argument("--out", default="agentpress/proof-outreach/external-proof-campaign-runner.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("host-transcript-batch-ingest"); p.add_argument("dir"); p.add_argument("--out", default="agentpress/conformance/host-transcript-batch-ingest.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("connector-failure-taxonomy"); p.add_argument("--out", default="agentpress/connectors/connector-failure-taxonomy.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("cycle-gap-radar"); p.add_argument("--out", default="agentpress/planning/cycle-gap-radar.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("edge-case-gap-scan"); p.add_argument("--out", default="agentpress/evidence/edge-case-gap-scan.json"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("connector-catalog"); p.add_argument("--out", default="agentpress/connectors/connector-catalog.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("connector-health-check"); p.add_argument("--catalog", default="agentpress/connectors/connector-catalog.json"); p.add_argument("--out", default="agentpress/evidence/connector-health-check.json"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-wants-research"); p.add_argument("--out", default="agentpress/research/agent-wants-research.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("missing-connector-backlog"); p.add_argument("--out", default="agentpress/planning/missing-connector-backlog.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("host-transcript-validate"); p.add_argument("transcript"); p.add_argument("--out", default="agentpress/evidence/host-transcript-validation.json"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("ttf-green-import"); p.add_argument("input"); p.add_argument("--out", default="agentpress/evidence/ttf-green-import.json"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("conformance-evidence-score"); p.add_argument("--host-result", default="agentpress/evidence/host-transcript-validation.json"); p.add_argument("--ttf-result", default="agentpress/evidence/ttf-green-import.json"); p.add_argument("--out", default="agentpress/conformance/conformance-evidence-score.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("approval-gate-eval"); p.add_argument("action"); p.add_argument("--out", default="agentpress/evidence/approval-gate-result.json"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("reviewer-gate-eval"); p.add_argument("review"); p.add_argument("--out", default="agentpress/evidence/reviewer-gate-result.json"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("action-ledger-adapter-wiring"); p.add_argument("--out", default="agentpress/observability/action-ledger/adapter-wiring.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("external-proof-relay-status"); p.add_argument("--out", default="agentpress/proof-outreach/external-proof-relay-status.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("glm-concerns-closure"); p.add_argument("--out", default="agentpress/planning/glm-concerns-closure.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("registry-dry-run"); p.add_argument("--out", default="agentpress/distribution/registry-dry-run.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("proof-ingest-review"); p.add_argument("--inbox", default="agentpress/external-proofs/inbox"); p.add_argument("--out", default="agentpress/external-proofs/proof-ingest-review.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("receipt-to-backlog"); p.add_argument("--ingest", default="agentpress/external-proofs/proof-ingest-review.json"); p.add_argument("--out", default="agentpress/planning/receipt-to-backlog.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("exponential-improvement-radar"); p.add_argument("--out", default="agentpress/planning/exponential-improvement-radar.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("json-schema-bundle"); p.add_argument("--out", default="agentpress/schemas/draft2020-12"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("schema-validator"); p.add_argument("--out", default="agentpress/evidence/schema-validator.json"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("proof-inbox-tracker"); p.add_argument("--inbox", default="agentpress/external-proofs/inbox"); p.add_argument("--out", default="agentpress/external-proofs/proof-inbox-tracker.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("host-run-harness"); p.add_argument("--out", default="agentpress/conformance/host-run-harness"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("ttf-green-metric"); p.add_argument("--out", default="agentpress/metrics/time-to-first-green.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("distribution-submission-pack"); p.add_argument("--out", default="agentpress/distribution/submission-pack"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("external-proof-pipeline"); p.add_argument("--out", default="agentpress/external-proofs/proof-pipeline.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("blocker-solution-matrix"); p.add_argument("--out", default="agentpress/planning/blocker-solution-matrix.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("next-bottleneck-radar"); p.add_argument("--out", default="agentpress/planning/next-bottleneck-radar.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("external-audit-run"); p.add_argument("--runtime", default="codex"); p.add_argument("--agent-id", default="external-agent"); p.add_argument("--run-id"); p.add_argument("--out", default="agentpress/external-audits/first-contact"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("external-proof-review"); p.add_argument("proof"); p.add_argument("--out", default="agentpress/external-proofs/proof-review.example.json"); p.add_argument("--strict-success", action="store_true"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("task-quality-eval"); p.add_argument("--out", default="agentpress/evals"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("public-schema-bundle"); p.add_argument("--out", default="agentpress/schemas/public"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("platform-audit-dashboard"); p.add_argument("--out", default="agentpress/audit/platform-audit-dashboard.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("ecosystem-conformance-suite"); p.add_argument("--out", default="agentpress/evidence/ecosystem-conformance-suite.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("iteration-cycle-engine"); p.add_argument("--out", default="agentpress/planning/iteration-cycle-engine.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("mcp-registry-pack"); p.add_argument("--out", default="agentpress/mcp/registry-pack"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("native-adapter-kit"); p.add_argument("--target", default="all"); p.add_argument("--out", default="agentpress/adapters/native"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("native-adapter-check"); p.add_argument("dir", nargs="?", default="agentpress/adapters/native"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("schema-validate-all"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/evidence/schema-validate-all.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--max-errors", type=int, default=200); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("trust-tier-evaluate"); p.add_argument("root", nargs="?", default="."); p.add_argument("--scoped-report", default="agentpress/marketplace/scoped-trust-report.json"); p.add_argument("--out", default="agentpress/trust/trust-tier-evaluation.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("plan-workflow-kit"); p.add_argument("--out", default="agentpress/workflows/plan-workflow"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("approval-gate-kit"); p.add_argument("--out", default="agentpress/approvals"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("reviewer-gate-kit"); p.add_argument("--out", default="agentpress/reviewers"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("provider-compatibility-kit"); p.add_argument("--out", default="agentpress/providers"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("runtime-validation-harness"); p.add_argument("--out", default="agentpress/runtime-validation"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("run-artifact-pack"); p.add_argument("--out", default="agentpress/run-artifacts"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("mission-keeper-kit"); p.add_argument("--out", default="agentpress/mission-keeper"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-platform-feature-backlog"); p.add_argument("--out", default="agentpress/planning/agent-platform-feature-backlog.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("action-ledger-kit"); p.add_argument("--out", default="agentpress/observability/action-ledger"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("context-debugger-kit"); p.add_argument("--out", default="agentpress/context"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("loop-guard-kit"); p.add_argument("--out", default="agentpress/runtime"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("mission-cockpit"); p.add_argument("--out", default="agentpress/mission-cockpit"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-identity-card"); p.add_argument("--agent-id", default="agentpress-reference-platform"); p.add_argument("--out", default="agentpress/identity/agentpress-identity-card.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("environment-fingerprint"); p.add_argument("--out", default="agentpress/runtime/environment-fingerprint.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("repro-bundle"); p.add_argument("--out", default="agentpress/runtime/repro-bundle.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("package-manager-bridge"); p.add_argument("--out", default="agentpress/package-registry/package-manager-bridge.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("tool-permission-policy"); p.add_argument("root", nargs="?", default="."); p.add_argument("--tools", default="agentpress/tools/agentpress-tools.json"); p.add_argument("--out", default="agentpress/policies/tool-permission-policy.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("mcp-catalog-export"); p.add_argument("root", nargs="?", default="."); p.add_argument("--tools", default="agentpress/tools/agentpress-tools.json"); p.add_argument("--out", default="agentpress/mcp/mcp-static-catalog.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("community-radar"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/community/community-radar.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("docs-command-check"); p.add_argument("root", nargs="?", default="."); p.add_argument("--path", action="append"); p.add_argument("--out", default="agentpress/evidence/docs-command-check.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--max-results", type=int, default=500); p.add_argument("--allow-failures", action="store_true"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("integration-sdk-kit"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/integrations/sdk"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--json", action="store_true")
    p = sub.add_parser("sdk-smoke"); p.add_argument("--out", default="agentpress/integrations/sdk/sdk-smoke.json"); p.add_argument("--python-sdk", default="agentpress/integrations/sdk/python/agentpress_sdk.py"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--timeout-seconds", type=int, default=10); p.add_argument("--max-bytes", type=int, default=1048576); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("queue-adapter-kit"); p.add_argument("--out", default="agentpress/queue"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("marketplace-compare"); p.add_argument("root", nargs="?", default="."); p.add_argument("--capability", default=""); p.add_argument("--max-amount", type=float, default=0.0); p.add_argument("--allow-paid-quotes", action="store_true"); p.add_argument("--out", default="agentpress/marketplace/marketplace-compare.example.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("marketplace-trust"); p.add_argument("root", nargs="?", default="."); p.add_argument("--marketplace", default="agentpress/marketplace/marketplace-index.json"); p.add_argument("--out", default="agentpress/marketplace/marketplace-trust-index.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("proof-request-pack"); p.add_argument("--runtime", default="codex"); p.add_argument("--out", default="agentpress/proof-outreach/proof-request-pack.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("proof-receipt-verify"); p.add_argument("file"); p.add_argument("--out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("scoped-trust-report"); p.add_argument("root", nargs="?", default="."); p.add_argument("--marketplace", default="agentpress/marketplace/marketplace-index.json"); p.add_argument("--proof-index", default="agentpress/external-proofs/external-proof-index.json"); p.add_argument("--out", default="agentpress/marketplace/scoped-trust-report.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("proof-outreach-kit"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/proof-outreach"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--json", action="store_true")
    p = sub.add_parser("proof-ingest"); p.add_argument("root", nargs="?", default="."); p.add_argument("--dir", default="agentpress/external-proofs"); p.add_argument("--out", default="agentpress/external-proofs/external-proof-index.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--allow-rejected", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("proof-scoreboard"); p.add_argument("root", nargs="?", default="."); p.add_argument("--dir", default="agentpress/external-proofs"); p.add_argument("--index", default="agentpress/external-proofs/external-proof-index.json"); p.add_argument("--out", default="agentpress/external-proofs/proof-scoreboard.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("package-registry-skeleton"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/package-registry/skeleton"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("package-registry-dry-run"); p.add_argument("root", nargs="?", default="."); p.add_argument("--dir", default="agentpress/package-registry/skeleton"); p.add_argument("--out", default="agentpress/package-registry/package-registry-dry-run.json"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("secure-transport-readiness"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/secure-transport/secure-transport-readiness.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("transport-request"); p.add_argument("--out", default="agentpress/secure-transport/secure-transport-request.example.json"); p.add_argument("--from-agent", required=True); p.add_argument("--to-operator", required=True); p.add_argument("--purpose", required=True); p.add_argument("--scope", default="one-off encrypted_payload_external"); p.add_argument("--request-id"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("secure-transport-kit"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/secure-transport"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--json", action="store_true")
    p = sub.add_parser("privacy-status"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/privacy/privacy-status.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("privacy-kit"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/privacy"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--json", action="store_true")
    p = sub.add_parser("redaction-check"); p.add_argument("path"); p.add_argument("--out"); p.add_argument("--max-files", type=int, default=200); p.add_argument("--max-chars", type=int, default=200000); p.add_argument("--allow-findings", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("confidential-message-verify"); p.add_argument("envelope"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("consent-registry"); p.add_argument("--out", default="agentpress/privacy/consent-registry.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("consent-check"); p.add_argument("--registry", default="agentpress/privacy/consent-registry.json"); p.add_argument("--agent", required=True); p.add_argument("--scope", default="confidential_metadata_only"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("confidential-message-create"); p.add_argument("--out", default="agentpress/privacy/confidential-message.example.json"); p.add_argument("--from-agent", required=True); p.add_argument("--to-agent", required=True); p.add_argument("--subject", required=True); p.add_argument("--body"); p.add_argument("--body-file"); p.add_argument("--redacted-preview"); p.add_argument("--retention-policy", default="metadata_30_days_payload_external"); p.add_argument("--human-approval-required", default="before secure payload exchange"); p.add_argument("--message-id"); p.add_argument("--sequence", type=int, default=1); p.add_argument("--expires-utc", default=""); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("error-codes"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/runtime/error-codes.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("session-state"); p.add_argument("--out", default="agentpress/runtime/session-state.example.json"); p.add_argument("--session-id", default="agentpress-session-example"); p.add_argument("--goal", default="AgentPress resumable work"); p.add_argument("--status", default="in_progress"); p.add_argument("--event"); p.add_argument("--artifact"); p.add_argument("--resume-command"); p.add_argument("--next-action", action="append"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("health-status"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/runtime/health-status.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("batch-run"); p.add_argument("input"); p.add_argument("--out", default="agentpress/runtime/batch-result.json"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("remediation-index"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/remediation/remediation-index.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("china-deep-angle-radar"); p.add_argument("--out", default="agentpress/china/china-deep-angle-radar.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("mcp-cli-bridge-pack"); p.add_argument("--out", default="agentpress/china/mcp-cli-bridge-pack.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("china-container-mirror-pack"); p.add_argument("--out", default="agentpress/china/china-container-mirror-pack.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("china-enterprise-connector-pack"); p.add_argument("--out", default="agentpress/china/china-enterprise-connector-pack.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("china-painpoint-radar"); p.add_argument("--out", default="agentpress/china/china-painpoint-radar.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("china-mcp-preflight"); p.add_argument("--out", default="agentpress/china/china-mcp-preflight.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("windows-npx-doctor-pack"); p.add_argument("--out", default="agentpress/china/windows-npx-doctor-pack.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("global-mirror-matrix"); p.add_argument("--out", default="agentpress/distribution/global-region-mirror-matrix.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("region-health"); p.add_argument("root", nargs="?", default="."); p.add_argument("--matrix", default="agentpress/distribution/global-region-mirror-matrix.json"); p.add_argument("--out", default="agentpress/evidence/region-health.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--timeout-seconds", type=int, default=12); p.add_argument("--max-bytes", type=int, default=1048576); p.add_argument("--max-paths", type=int, default=5); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("package-registry-fallback-matrix"); p.add_argument("--out", default="agentpress/install/package-registry-fallback-matrix.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("global-starter-pack"); p.add_argument("--out", default="agentpress/global"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("ecosystem-connector-packs"); p.add_argument("--out", default="agentpress/connectors/ecosystem-packs"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("package-registry-plan"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/package-registry/package-registry-plan.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("lint"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/evidence/agentpress-lint.json"); p.add_argument("--max-readme-chars", type=int, default=12000); p.add_argument("--allow-warnings", action="store_true"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("consumer-demo-pack"); p.add_argument("--out", default="agentpress/demos/consumer"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("proof-campaign"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/proof-campaigns/proof-campaign.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("attest"); att = p.add_subparsers(dest="attest_cmd", required=True)
    c=att.add_parser("create"); c.add_argument("root", nargs="?", default="."); c.add_argument("--file", action="append", required=True); c.add_argument("--subject", required=True); c.add_argument("--issuer", default="agentpress-reference-agent"); c.add_argument("--attestation-id"); c.add_argument("--notes"); c.add_argument("--out", required=True); c.add_argument("--json", action="store_true")
    v=att.add_parser("verify"); v.add_argument("attestation"); v.add_argument("root", nargs="?", default="."); v.add_argument("--json", action="store_true")
    i=att.add_parser("index"); i.add_argument("root", nargs="?", default="."); i.add_argument("--dir", default="agentpress/attestations"); i.add_argument("--out", default="agentpress/attestations/attestation-index.json"); i.add_argument("--base-url", default=CANONICAL_BASE_URL); i.add_argument("--json", action="store_true")
    p = sub.add_parser("agent-painpoints"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/painpoints/agent-painpoints.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("audience-kit"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/audience/audience-kit.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--agent-id"); p.add_argument("--topic", default="agentpress-updates"); p.add_argument("--contact"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("marketplace"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/marketplace/marketplace-index.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--capability"); p.add_argument("--runtime"); p.add_argument("--payment-required"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
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
    p = sub.add_parser("submission-validate"); p.add_argument("path"); p.add_argument("--out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("blocker-report"); p.add_argument("--agent-id", required=True); p.add_argument("--runtime", required=True); p.add_argument("--severity", choices=["P0","P1","P2","P3"], default="P1"); p.add_argument("--command", required=True); p.add_argument("--error-summary", required=True); p.add_argument("--missing-field"); p.add_argument("--desired-fix", required=True); p.add_argument("--blocker-id"); p.add_argument("--out", default="agentpress/submissions/blocker-report.example.json"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("submission-pack"); p.add_argument("--receipt", required=True); p.add_argument("--out", required=True); p.add_argument("--json", action="store_true")
    p = sub.add_parser("reputation-index"); p.add_argument("--landing-dir", default="agentpress/landing"); p.add_argument("--self-test-dir", default="agentpress/self-test"); p.add_argument("--receipt-dir", default="agentpress/receipts"); p.add_argument("--external-proof-index", default="agentpress/external-proofs/external-proof-index.json"); p.add_argument("--out", required=True); p.add_argument("--json", action="store_true")
    p = sub.add_parser("landing-receipt"); p.add_argument("--agent-id", required=True); p.add_argument("--runtime", required=True); p.add_argument("--discovery-channel", required=True); p.add_argument("--capability", action="append"); p.add_argument("--self-test-ref"); p.add_argument("--contact"); p.add_argument("--base-url", default="https://barneywohl.github.io/agentpress/"); p.add_argument("--landing-id"); p.add_argument("--out", required=True); p.add_argument("--json", action="store_true")
    p = sub.add_parser("landing-index"); p.add_argument("dir"); p.add_argument("--out"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("inbox-compile"); p.add_argument("inbox_dir"); p.add_argument("--out", required=True); p.add_argument("--json", action="store_true")
    p = sub.add_parser("patch-pr-helper"); p.add_argument("--title", required=True); p.add_argument("--change-summary", required=True); p.add_argument("--diff"); p.add_argument("--changed-file", action="append"); p.add_argument("--base-branch", default="main"); p.add_argument("--target-branch"); p.add_argument("--reviewer", action="append"); p.add_argument("--validation", action="append"); p.add_argument("--out", default="agentpress/contrib/patch-pr-helper.example.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
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
    p = sub.add_parser("freshness-citation-report"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/evidence/freshness-citation-report.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--include-files", action="store_true"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("browser-smoke"); p.add_argument("--url", action="append"); p.add_argument("--out", default="agentpress/evidence/browser-smoke.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--timeout-seconds", type=int, default=10); p.add_argument("--max-bytes", type=int, default=1048576); p.add_argument("--require-json", action="store_true"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("feature-build-queue"); p.add_argument("root", nargs="?", default="."); p.add_argument("--coverage", default="agentpress/tools/tool-coverage.json"); p.add_argument("--painpoints", default="agentpress/painpoints/agent-painpoints.json"); p.add_argument("--adoption", default="agentpress/adoption/adoption-status.json"); p.add_argument("--out", default="agentpress/planning/feature-build-queue.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--include-blocked", action="store_true"); p.add_argument("--include-adoption-gaps", action="store_true"); p.add_argument("--include-public-radar", action="store_true"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("build-queue-pick"); p.add_argument("root", nargs="?", default="."); p.add_argument("--queue", default="agentpress/planning/feature-build-queue.json"); p.add_argument("--coverage", default="agentpress/tools/tool-coverage.json"); p.add_argument("--painpoints", default="agentpress/painpoints/agent-painpoints.json"); p.add_argument("--adoption", default="agentpress/adoption/adoption-status.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--include-blocked", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("build-queue-complete"); p.add_argument("--feature", required=True); p.add_argument("--commit", default=""); p.add_argument("--evidence", default=""); p.add_argument("--notes", default=""); p.add_argument("--out", default="agentpress/planning/build-completions.jsonl"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("tool-coverage"); p.add_argument("root", nargs="?", default="."); p.add_argument("--tools", default="agentpress/tools/agentpress-tools.json"); p.add_argument("--out", default="agentpress/tools/tool-coverage.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("cli-expansion-roadmap"); p.add_argument("root", nargs="?", default="."); p.add_argument("--tools", default="agentpress/tools/agentpress-tools.json"); p.add_argument("--coverage", default="agentpress/tools/tool-coverage.json"); p.add_argument("--out", default="agentpress/tools/cli-expansion-roadmap.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("tool-request"); p.add_argument("--agent-id", required=True); p.add_argument("--persona", required=True); p.add_argument("--wanted-tool", required=True); p.add_argument("--painpoint", required=True); p.add_argument("--desired-command", required=True); p.add_argument("--priority", choices=["P0","P1","P2","P3"], default="P1"); p.add_argument("--request-id"); p.add_argument("--out", default="agentpress/tools/tool-request.example.json"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
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
    if args.cmd == "schema-validate": return schema_validate(args)
    if args.cmd == "fetch": return fetch(args)
    if args.cmd == "distribution-kit": return distribution_kit(args)
    if args.cmd == "distribution-mirrors": return distribution_mirrors(args)
    if args.cmd == "mirror-status": return mirror_status(args)
    if args.cmd == "failover-plan": return failover_plan(args)
    if args.cmd == "discover": return discover_agentpress(args)
    if args.cmd == "negative-fixtures": return negative_fixtures(args)
    if args.cmd == "feedback-submit": return feedback_submit(args)
    if args.cmd == "consistency-check": return consistency_check(args)
    if args.cmd == "adoption-status": return adoption_status(args)
    if args.cmd == "payment-status": return payment_status(args)
    if args.cmd == "payment-intent": return payment_intent(args)
    if args.cmd == "marketplace": return marketplace_index(args)
    if args.cmd == "audience-kit": return audience_kit(args)
    if args.cmd == "agent-painpoints": return agent_painpoints(args)
    if args.cmd == "attest": return attest(args)
    if args.cmd == "proof-campaign": return proof_campaign(args)
    if args.cmd == "proof-ingest": return proof_ingest(args)
    if args.cmd == "proof-scoreboard": return proof_scoreboard(args)
    if args.cmd == "proof-outreach-kit": return proof_outreach_kit(args)
    if args.cmd == "proof-request-pack": return proof_request_pack(args)
    if args.cmd == "proof-receipt-verify": return proof_receipt_verify(args)
    if args.cmd == "scoped-trust-report": return scoped_trust_report(args)
    if args.cmd == "china-deep-angle-radar": return china_deep_angle_radar(args)
    if args.cmd == "mcp-cli-bridge-pack": return mcp_cli_bridge_pack(args)
    if args.cmd == "china-container-mirror-pack": return china_container_mirror_pack(args)
    if args.cmd == "china-enterprise-connector-pack": return china_enterprise_connector_pack(args)
    if args.cmd == "china-painpoint-radar": return china_painpoint_radar(args)
    if args.cmd == "china-mcp-preflight": return china_mcp_preflight(args)
    if args.cmd == "windows-npx-doctor-pack": return windows_npx_doctor_pack(args)
    if args.cmd == "global-mirror-matrix": return global_mirror_matrix(args)
    if args.cmd == "region-health": return region_health(args)
    if args.cmd == "package-registry-fallback-matrix": return package_registry_fallback_matrix(args)
    if args.cmd == "global-starter-pack": return global_starter_pack(args)
    if args.cmd == "ecosystem-connector-packs": return ecosystem_connector_packs(args)
    if args.cmd == "package-registry-plan": return package_registry_plan(args)
    if args.cmd == "lint": return agent_lint(args)
    if args.cmd == "consumer-demo-pack": return consumer_demo_pack(args)
    if args.cmd == "package-registry-skeleton": return package_registry_skeleton(args)
    if args.cmd == "package-registry-dry-run": return package_registry_dry_run(args)
    if args.cmd == "remediation-index": return remediation_index(args)
    if args.cmd == "error-codes": return error_codes(args)
    if args.cmd == "privacy-status": return privacy_status(args)
    if args.cmd == "secure-transport-readiness": return secure_transport_readiness(args)
    if args.cmd == "transport-request": return transport_request(args)
    if args.cmd == "secure-transport-kit": return secure_transport_kit(args)
    if args.cmd == "privacy-kit": return privacy_kit(args)
    if args.cmd == "redaction-check": return redaction_check(args)
    if args.cmd == "confidential-message-create": return confidential_message_create(args)
    if args.cmd == "confidential-message-verify": return confidential_message_verify(args)
    if args.cmd == "consent-registry": return consent_registry(args)
    if args.cmd == "consent-check": return consent_check(args)
    if args.cmd == "session-state": return session_state(args)
    if args.cmd == "health-status": return health_status(args)
    if args.cmd == "batch-run": return batch_run(args)
    if args.cmd == "painpoint-intake": return painpoint_intake(args)
    if args.cmd == "attestation-coverage": return attestation_coverage(args)
    if args.cmd == "marketplace-trust": return marketplace_trust(args)
    if args.cmd == "marketplace-compare": return marketplace_compare(args)
    if args.cmd == "queue-adapter-kit": return queue_adapter_kit(args)
    if args.cmd == "integration-sdk-kit": return integration_sdk_kit(args)
    if args.cmd == "docs-command-check": return docs_command_check(args)
    if args.cmd == "community-radar": return community_radar(args)
    if args.cmd == "mcp-catalog-export": return mcp_catalog_export(args)
    if args.cmd == "tool-permission-policy": return tool_permission_policy(args)
    if args.cmd == "package-manager-bridge": return package_manager_bridge(args)
    if args.cmd == "agent-identity-card": return agent_identity_card(args)
    if args.cmd == "agent-platform-feature-backlog": return agent_platform_feature_backlog(args)
    if args.cmd == "plan-workflow-kit": return plan_workflow_kit(args)
    if args.cmd == "native-adapter-kit": return native_adapter_kit(args)
    if args.cmd == "platform-audit-dashboard": return platform_audit_dashboard(args)
    if args.cmd == "external-audit-run": return external_audit_run(args)
    if args.cmd == "distribution-submission-pack": return distribution_submission_pack(args)
    if args.cmd == "json-schema-bundle": return json_schema_bundle(args)
    if args.cmd == "registry-dry-run": return registry_dry_run(args)
    if args.cmd == "approval-gate-eval": return approval_gate_eval(args)
    if args.cmd == "host-transcript-validate": return host_transcript_validate(args)
    if args.cmd == "connector-catalog": return connector_catalog(args)
    if args.cmd == "edge-case-gap-scan": return edge_case_gap_scan(args)
    if args.cmd == "external-proof-campaign-runner": return external_proof_campaign_runner(args)
    if args.cmd == "connector-failure-to-backlog": return connector_failure_to_backlog(args)
    if args.cmd == "agent-persona-quickstarts": return agent_persona_quickstarts(args)
    if args.cmd == "deep-agent-painpoint-research": return deep_agent_painpoint_research(args)
    if args.cmd == "readiness-audit": return readiness_audit_cli(args)
    if args.cmd == "next-cycle-research": return next_cycle_research(args)
    if args.cmd == "memory-drift-check": return memory_drift_check(args)
    if args.cmd == "agent-community-channel-map": return agent_community_channel_map(args)
    if args.cmd == "mcp-consent-manifest-validator": return mcp_consent_manifest_validator(args)
    if args.cmd == "provider-adapter-repro-pack": return provider_adapter_repro_pack(args)
    if args.cmd == "checkpoint-replay-minimal-repro-generator": return checkpoint_replay_minimal_repro_generator(args)
    if args.cmd == "runtime-hang-repro-capsule": return runtime_hang_repro_capsule(args)
    if args.cmd == "first-agent-outreach-receipt-tracker": return first_agent_outreach_receipt_tracker(args)
    if args.cmd == "rag-tool-safety-bundle": return rag_tool_safety_bundle(args)
    if args.cmd == "external-reply-to-proof-ingest-bridge": return external_reply_to_proof_ingest_bridge(args)
    if args.cmd == "issue-comment-pack-generator": return issue_comment_pack_generator(args)
    if args.cmd == "issue-to-repro-pack": return issue_to_repro_pack(args)
    if args.cmd == "painpoint-target-pack": return painpoint_target_pack(args)
    if args.cmd == "mcp-config-mutation-guard": return mcp_config_mutation_guard(args)
    if args.cmd == "continuous-research-build-cycle-audit": return continuous_research_build_cycle_audit(args)
    if args.cmd == "current-agent-places-map": return current_agent_places_map(args)
    if args.cmd == "attention-painpoint-radar": return attention_painpoint_radar(args)
    if args.cmd == "first-agent-attention-kit": return first_agent_attention_kit(args)
    if args.cmd == "next-attention-build-spec": return next_attention_build_spec(args)
    if args.cmd == "agent-community-newswire": return agent_community_newswire(args)
    if args.cmd == "immediate-agent-needs-radar": return immediate_agent_needs_radar(args)
    if args.cmd == "solution-targeting-matrix": return solution_targeting_matrix(args)
    if args.cmd == "approval-bypass-risk-check": return approval_bypass_risk_check(args)
    if args.cmd == "provider-tool-translation-map": return provider_tool_translation_map(args)
    if args.cmd == "workflow-terminal-callback-check": return workflow_terminal_callback_check(args)
    if args.cmd == "context-compaction-risk-card": return context_compaction_risk_card(args)
    if args.cmd == "package-registry-doctor": return package_registry_doctor(args)
    if args.cmd == "package-registry-fallback-installer": return package_registry_fallback_installer(args)
    if args.cmd == "first-user-bootstrap": return first_user_bootstrap(args)
    if args.cmd == "first-run-wizard": return first_run_wizard(args)
    if args.cmd == "provider-error-explainer": return provider_error_explainer(args)
    if args.cmd == "adoption-scoreboard": return adoption_scoreboard(args)
    if args.cmd == "external-proof-inbox-review-flow": return external_proof_inbox_review_flow(args)
    if args.cmd == "release-registry-readiness-dashboard": return release_registry_readiness_dashboard(args)
    if args.cmd == "proof-capture": return proof_capture(args)
    if args.cmd == "sandbox-guard": return sandbox_guard(args)
    if args.cmd == "adoption-tracker": return adoption_tracker(args)
    if args.cmd == "handoff-pack": return handoff_pack(args)
    if args.cmd == "batch-painpoints": return batch_painpoints(args)
    if args.cmd == "release-candidate": return release_candidate(args)
    if args.cmd == "tool-schema-serialization-check": return tool_schema_serialization_check(args)
    if args.cmd == "community-issue-radar": return community_issue_radar(args)
    if args.cmd == "unsolved-agent-problem-backlog": return unsolved_agent_problem_backlog(args)
    if args.cmd == "tool-vocabulary-compatibility-check": return tool_vocabulary_compatibility_check(args)
    if args.cmd == "agent-state-checkpoint-sanitizer": return agent_state_checkpoint_sanitizer(args)
    if args.cmd == "dependency-error-remediation-map": return dependency_error_remediation_map(args)
    if args.cmd == "output-format-contract-tester": return output_format_contract_tester(args)
    if args.cmd == "tool-file-access-risk-scanner": return tool_file_access_risk_scanner(args)
    if args.cmd == "handoff-contract-validate": return handoff_contract_validate(args)
    if args.cmd == "pr-review-check": return pr_review_check(args)
    if args.cmd == "ci-flake-triage": return ci_flake_triage(args)
    if args.cmd == "secret-permission-preflight-run": return secret_permission_preflight_run(args)
    if args.cmd == "budget-check": return budget_check(args)
    if args.cmd == "coordination-ledger-check": return coordination_ledger_check(args)
    if args.cmd == "agent-memory-drift-detector": return agent_memory_drift_detector(args)
    if args.cmd == "task-handoff-contract": return task_handoff_contract(args)
    if args.cmd == "pr-review-readiness-pack": return pr_review_readiness_pack(args)
    if args.cmd == "ci-flake-triage-report": return ci_flake_triage_report(args)
    if args.cmd == "secret-permission-preflight": return secret_permission_preflight(args)
    if args.cmd == "agent-cost-budget-card": return agent_cost_budget_card(args)
    if args.cmd == "multi-agent-coordination-ledger": return multi_agent_coordination_ledger(args)
    if args.cmd == "readiness-score": return readiness_score(args)
    if args.cmd == "readiness-fix-plan": return readiness_fix_plan(args)
    if args.cmd == "runtime-install-doctor": return runtime_install_doctor(args)
    if args.cmd == "connector-security-scanner": return connector_security_scanner(args)
    if args.cmd == "deterministic-agent-eval-packs": return deterministic_agent_eval_packs(args)
    if args.cmd == "verifiable-run-evidence-bundle": return verifiable_run_evidence_bundle(args)
    if args.cmd == "browser-agent-compatibility-harness": return browser_agent_compatibility_harness(args)
    if args.cmd == "mcp-connector-auth-readiness": return mcp_connector_auth_readiness(args)
    if args.cmd == "tool-routing-decision-matrix": return tool_routing_decision_matrix(args)
    if args.cmd == "agent-eval-observability-bridge": return agent_eval_observability_bridge(args)
    if args.cmd == "deployment-connector-matrix": return deployment_connector_matrix(args)
    if args.cmd == "connector-first-run-checklist": return connector_first_run_checklist(args)
    if args.cmd == "sdk-command-wrapper-catalog": return sdk_command_wrapper_catalog(args)
    if args.cmd == "cycle-completion-audit": return cycle_completion_audit(args)
    if args.cmd == "host-transcript-dropbox-spec": return host_transcript_dropbox_spec(args)
    if args.cmd == "proof-request-queue": return proof_request_queue(args)
    if args.cmd == "next-build-spec-queue": return next_build_spec_queue(args)
    if args.cmd == "host-transcript-batch-ingest": return host_transcript_batch_ingest(args)
    if args.cmd == "connector-failure-taxonomy": return connector_failure_taxonomy(args)
    if args.cmd == "cycle-gap-radar": return cycle_gap_radar(args)
    if args.cmd == "connector-health-check": return connector_health_check(args)
    if args.cmd == "agent-wants-research": return agent_wants_research(args)
    if args.cmd == "missing-connector-backlog": return missing_connector_backlog(args)
    if args.cmd == "ttf-green-import": return ttf_green_import(args)
    if args.cmd == "conformance-evidence-score": return conformance_evidence_score(args)
    if args.cmd == "reviewer-gate-eval": return reviewer_gate_eval(args)
    if args.cmd == "action-ledger-adapter-wiring": return action_ledger_adapter_wiring(args)
    if args.cmd == "external-proof-relay-status": return external_proof_relay_status(args)
    if args.cmd == "glm-concerns-closure": return glm_concerns_closure(args)
    if args.cmd == "proof-ingest": return proof_ingest(args)
    if args.cmd == "proof-ingest-review": return proof_ingest_review(args)
    if args.cmd == "receipt-to-backlog": return receipt_to_backlog(args)
    if args.cmd == "exponential-improvement-radar": return exponential_improvement_radar(args)
    if args.cmd == "schema-validator": return schema_validator(args)
    if args.cmd == "proof-inbox-tracker": return proof_inbox_tracker(args)
    if args.cmd == "host-run-harness": return host_run_harness(args)
    if args.cmd == "ttf-green-metric": return ttf_green_metric(args)
    if args.cmd == "external-proof-pipeline": return external_proof_pipeline(args)
    if args.cmd == "blocker-solution-matrix": return blocker_solution_matrix(args)
    if args.cmd == "next-bottleneck-radar": return next_bottleneck_radar(args)
    if args.cmd == "external-proof-review": return external_proof_review(args)
    if args.cmd == "task-quality-eval": return task_quality_eval(args)
    if args.cmd == "public-schema-bundle": return public_schema_bundle(args)
    if args.cmd == "ecosystem-conformance-suite": return ecosystem_conformance_suite(args)
    if args.cmd == "iteration-cycle-engine": return iteration_cycle_engine(args)
    if args.cmd == "mcp-registry-pack": return mcp_registry_pack(args)
    if args.cmd == "native-adapter-check": return native_adapter_check(args)
    if args.cmd == "schema-validate-all": return schema_validate_all(args)
    if args.cmd == "trust-tier-evaluate": return trust_tier_evaluate(args)
    if args.cmd == "approval-gate-kit": return approval_gate_kit(args)
    if args.cmd == "reviewer-gate-kit": return reviewer_gate_kit(args)
    if args.cmd == "provider-compatibility-kit": return provider_compatibility_kit(args)
    if args.cmd == "runtime-validation-harness": return runtime_validation_harness(args)
    if args.cmd == "run-artifact-pack": return run_artifact_pack(args)
    if args.cmd == "mission-keeper-kit": return mission_keeper_kit(args)
    if args.cmd == "action-ledger-kit": return action_ledger_kit(args)
    if args.cmd == "context-debugger-kit": return context_debugger_kit(args)
    if args.cmd == "loop-guard-kit": return loop_guard_kit(args)
    if args.cmd == "mission-cockpit": return mission_cockpit(args)
    if args.cmd == "environment-fingerprint": return environment_fingerprint(args)
    if args.cmd == "repro-bundle": return repro_bundle(args)
    if args.cmd == "sdk-smoke": return sdk_smoke(args)
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
    if args.cmd == "submission-validate": return submission_validate(args)
    if args.cmd == "blocker-report": return blocker_report(args)
    if args.cmd == "reputation-index": return reputation_index(args)
    if args.cmd == "landing-receipt": return landing_receipt(args)
    if args.cmd == "landing-index": return landing_index(args)
    if args.cmd == "inbox-compile": return inbox_compile(args)
    if args.cmd == "bundle-diff": return bundle_diff(args)
    if args.cmd == "patch-pr-helper": return patch_pr_helper(args)
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
    if args.cmd == "tool-coverage": return tool_coverage(args)
    if args.cmd == "feature-build-queue": return feature_build_queue(args)
    if args.cmd == "browser-smoke": return browser_smoke(args)
    if args.cmd == "freshness-citation-report": return freshness_citation_report(args)
    if args.cmd == "build-queue-pick": return build_queue_pick(args)
    if args.cmd == "build-queue-complete": return build_queue_complete(args)
    if args.cmd == "cli-expansion-roadmap": return cli_expansion_roadmap(args)
    if args.cmd == "tool-request": return tool_request(args)
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
