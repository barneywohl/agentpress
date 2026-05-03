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
        {"name":"agentpress.tool_permission_policy", "description":"Export per-command permission/approval policy for safe agent tool use.", "command":"python3 scripts/agentpress.py tool-permission-policy --json", "tags":["permissions","policy","approval","safety","tools"]},
        {"name":"agentpress.mcp_catalog_export", "description":"Export AgentPress tools as a static MCP-style catalog for Cline/Roo/MCP tool discovery.", "command":"python3 scripts/agentpress.py mcp-catalog-export --json", "tags":["mcp","tools","catalog","discovery","static"]},
        {"name":"agentpress.community_radar", "description":"Map public agent-builder communities, recurring painpoints, and next AgentPress features to build.", "command":"python3 scripts/agentpress.py community-radar --json", "tags":["community","research","painpoints","agents","roadmap"]},
        {"name":"agentpress.docs_command_check", "description":"Lint documented AgentPress CLI commands for stale command names and obvious stale flags.", "command":"python3 scripts/agentpress.py docs-command-check --json", "tags":["docs","commands","lint","cli","drift"]},
        {"name":"agentpress.integration_sdk_kit", "description":"Generate zero-dependency Python/JavaScript SDK clients and read-only integration quickstart.", "command":"python3 scripts/agentpress.py integration-sdk-kit --json", "tags":["sdk","integration","python","javascript","client"]},
        {"name":"agentpress.sdk_smoke", "description":"Smoke-test SDK integration endpoints and Python SDK compileability.", "command":"python3 scripts/agentpress.py sdk-smoke --json", "tags":["sdk","smoke","integration","endpoints"]},
        {"name":"agentpress.queue_adapter_kit", "description":"Generate static/local durable queue adapter schema, retry policy, idempotency, health, and dead-letter examples.", "command":"python3 scripts/agentpress.py queue-adapter-kit --json", "tags":["queue","retry","workflow","handoff","idempotency"]},
        {"name":"agentpress.marketplace_compare", "description":"Compare marketplace services for a capability with no-spend quote simulation.", "command":"python3 scripts/agentpress.py marketplace-compare --capability agent_onboard --json", "tags":["marketplace","compare","quote","routing","no-spend"]},
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
    if external_receipts == 0:
        items.append({"rank":rank,"priority":"P0","source":"adoption_gap","feature":"automatic proof ingestion and scoring from submitted third-party proof/blocker packs","persona":"proof_agent","why":"Protocol features are shipped, but independent external adoption receipts remain zero.","acceptance":["proof ingest CLI validates external proof directory","reputation/proof index updates from accepted proofs","secret scan rejects unsafe submissions","live proof status JSON returns 200"],"blocked":False}); rank+=1
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
    if completed:
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
    p = sub.add_parser("tool-permission-policy"); p.add_argument("root", nargs="?", default="."); p.add_argument("--tools", default="agentpress/tools/agentpress-tools.json"); p.add_argument("--out", default="agentpress/policies/tool-permission-policy.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("mcp-catalog-export"); p.add_argument("root", nargs="?", default="."); p.add_argument("--tools", default="agentpress/tools/agentpress-tools.json"); p.add_argument("--out", default="agentpress/mcp/mcp-static-catalog.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("community-radar"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/community/community-radar.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("docs-command-check"); p.add_argument("root", nargs="?", default="."); p.add_argument("--path", action="append"); p.add_argument("--out", default="agentpress/evidence/docs-command-check.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--max-results", type=int, default=500); p.add_argument("--allow-failures", action="store_true"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("integration-sdk-kit"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/integrations/sdk"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--json", action="store_true")
    p = sub.add_parser("sdk-smoke"); p.add_argument("--out", default="agentpress/integrations/sdk/sdk-smoke.json"); p.add_argument("--python-sdk", default="agentpress/integrations/sdk/python/agentpress_sdk.py"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--timeout-seconds", type=int, default=10); p.add_argument("--max-bytes", type=int, default=1048576); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("queue-adapter-kit"); p.add_argument("--out", default="agentpress/queue"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("marketplace-compare"); p.add_argument("root", nargs="?", default="."); p.add_argument("--capability", default=""); p.add_argument("--max-amount", type=float, default=0.0); p.add_argument("--allow-paid-quotes", action="store_true"); p.add_argument("--out", default="agentpress/marketplace/marketplace-compare.example.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("marketplace-trust"); p.add_argument("root", nargs="?", default="."); p.add_argument("--marketplace", default="agentpress/marketplace/marketplace-index.json"); p.add_argument("--out", default="agentpress/marketplace/marketplace-trust-index.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
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
    p = sub.add_parser("package-registry-plan"); p.add_argument("root", nargs="?", default="."); p.add_argument("--out", default="agentpress/package-registry/package-registry-plan.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
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
    p = sub.add_parser("feature-build-queue"); p.add_argument("root", nargs="?", default="."); p.add_argument("--coverage", default="agentpress/tools/tool-coverage.json"); p.add_argument("--painpoints", default="agentpress/painpoints/agent-painpoints.json"); p.add_argument("--adoption", default="agentpress/adoption/adoption-status.json"); p.add_argument("--out", default="agentpress/planning/feature-build-queue.json"); p.add_argument("--base-url", default=CANONICAL_BASE_URL); p.add_argument("--include-blocked", action="store_true"); p.add_argument("--no-write", action="store_true"); p.add_argument("--json", action="store_true")
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
    if args.cmd == "package-registry-plan": return package_registry_plan(args)
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
