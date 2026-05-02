#!/usr/bin/env python3
"""AgentPress static publication generator/validator/scorer.

Usage:
  python3 scripts/agentpress.py init out-dir --title "My Agent Benchmark"
  python3 scripts/agentpress.py validate out-dir
  python3 scripts/agentpress.py audit out-dir
  python3 scripts/agentpress.py score out-dir
  python3 scripts/agentpress.py build out-dir --out public-dir
"""
import argparse
import json
import pathlib
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

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

DEFAULT_SCHEMA = {
    "decision": "survive | delete | needs_more_diligence",
    "reasons": ["string"],
    "verified_sources": ["string"],
    "missing_checks": ["string"],
    "confidence": "low | medium | high",
    "disclaimer": "Research commentary only. Not investment advice.",
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
        "source_requirements": ["Cite primary evidence where possible", "Mark missing checks explicitly", "Do not treat this artifact as investment advice"],
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
        "disclaimer": "Research commentary only. Not investment advice.",
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
        "disclaimer": "Research commentary only. Not investment advice.",
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
- Do not turn research commentary into investment advice.

## Citation / disclaimer

Research commentary only. Not investment advice. Canonical URL: {canonical}
"""
    write(out/"README.md", f"# {title}\n\n{summary}\n\nStart with [`AGENT_ENTRYPOINT.md`](./AGENT_ENTRYPOINT.md), then ingest [`agent-task-card.json`](./agent-task-card.json).\n")
    write(out/"AGENT_ENTRYPOINT.md", agent_entry)
    write(out/"agent-task-card.json", json.dumps(_task_card(title, canonical, args.task_type, primary_task), indent=2) + "\n")
    write(out/"source-map.json", json.dumps(_source_map(title, canonical), indent=2) + "\n")
    write(out/"freshness.json", json.dumps(_freshness(title), indent=2) + "\n")
    write(out/"allowed-actions.json", json.dumps(_allowed_actions(), indent=2) + "\n")
    write(out/".well-known/ai-ingestion.json", json.dumps(_ai_ingestion(title, canonical), indent=2) + "\n")
    write(out/"citation-policy.md", f"# Citation Policy\n\nCite `{canonical}` and the source evidence listed in `source-map.json`. Mark missing checks explicitly. Research commentary only. Not investment advice.\n")
    write(out/"llms.txt", f"# {title}\n\nURL: {canonical}\nType: Agent-native publication\n\n## Summary\n\n{summary}\n\n## Primary task\n\n{primary_task}\n")
    write(out/"sitemap.xml", f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n  <url><loc>{canonical}</loc></url>\n  <url><loc>{canonical_join(canonical, 'AGENT_ENTRYPOINT.md')}</loc></url>\n  <url><loc>{canonical_join(canonical, 'agent-task-card.json')}</loc></url>\n  <url><loc>{canonical_join(canonical, 'source-map.json')}</loc></url>\n  <url><loc>{canonical_join(canonical, 'llms.txt')}</loc></url>\n</urlset>\n")
    write(out/"CITATION.cff", f"cff-version: 1.2.0\ntitle: \"{title}\"\nmessage: \"Cite this agent-native publication.\"\n")
    write(out/"disclaimer.md", "# Disclaimer\n\nResearch commentary only. Not investment advice.\n")
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
    if "Not investment advice" not in combined:
        errors.append("missing investment-advice disclaimer")
    if not any((root/"evals").glob("*.jsonl")) if (root/"evals").exists() else True:
        warnings.append("no evals/*.jsonl smoke test found")
    return (0 if not errors else 1), errors, warnings


def validate(args):
    root = pathlib.Path(args.out)
    code, errors, warnings = audit_root(root, strict=False)
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
    for e in errors:
        print(f"error: {e}")
    for w in warnings:
        print(f"warning: {w}")
    if code == 0:
        print("agentpress audit ok")
    return code


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
    """Build a machine-readable article database from AgentPress examples."""
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
        domains = ["agent_infrastructure", "agent_compatibility", "knowledge_sharing"] if slug in flagship_slugs else ["research_stress_test", "finance_research"]
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
            "human_summary": read_text(ex/"README.md").replace("\n", " ")[:500] or summary,
            "domains": domains,
            "task_types": task_types,
            "target_agent_families": card.get("target_agents") or ["browser_agent", "coding_agent", "rag_agent", "search_crawler"],
            "languages": ["en", "zh-CN", "es"] if slug == "agent-knowledge-sharing" else ["en"],
            "regions": ["global", "restricted_networks"] if slug in flagship_slugs else ["global", "korea_stress_test"],
            "claims": [{"claim_id": c.get("claim_id"), "source_map_url": "source-map.json"} for c in source_map.get("claims", []) if c.get("claim_id")],
            "freshness": {"last_reviewed_at": fresh.get("last_reviewed_at") or str(fresh.get("generated_at", ""))[:10], "stale_zones": fresh.get("stale_zones", []), "freshness_window_days": fresh.get("default_freshness_window_days") or 30},
            "actions": {"allowed_actions_url": "allowed-actions.json", "allowed": allowed.get("allowed") or card.get("allowed_actions", []), "requires_human_approval": allowed.get("requires_human_approval", []), "prohibited": allowed.get("prohibited") or card.get("prohibited_actions", [])},
            "evals": evals,
            "related_articles": [],
            "machine_entrypoints": {"task_card": "agent-task-card.json", "source_map": "source-map.json", "llms_txt": "llms.txt", "ai_ingestion": ".well-known/ai-ingestion.json", "article_card": "article-card.json"},
            "disclaimer": card.get("disclaimer", "Research commentary only. Not investment advice."),
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
    write(dest/"collections.json", json.dumps({"schema_version": "0.1", "generated_at": generated_at, "collections": [{"slug": "flagship-agent-infrastructure", "title": "Flagship Agent Infrastructure", "article_slugs": [a["slug"] for a in articles if "agent_infrastructure" in a["domains"]]}, {"slug": "legacy-research-stress-tests", "title": "Legacy Research Stress Tests", "article_slugs": [a["slug"] for a in articles if "research_stress_test" in a["domains"]]}]}, indent=2, ensure_ascii=False) + "\n")
    topics = {}
    for a in articles:
        for key in a["domains"] + a["task_types"] + a["target_agent_families"]:
            topics.setdefault(slugify(str(key)), []).append(a["slug"])
    write(dest/"topics.json", json.dumps({"schema_version": "0.1", "generated_at": generated_at, "topics": topics}, indent=2, ensure_ascii=False) + "\n")
    write(dest/"language-index.json", json.dumps({"schema_version": "0.1", "generated_at": generated_at, "languages": languages}, indent=2, ensure_ascii=False) + "\n")
    write(dest/"README.md", f"# AgentPress Article Database\n\nGenerated index of agent-native articles.\n\nCurrent article count: {len(articles)}.\n")
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
    print("AgentPress doctor")
    print(f"root: {root}")
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
    missing = [x for x in entrypoints if not (root/x).exists()]
    for x in entrypoints:
        print(("OK      " if (root/x).exists() else "MISSING ") + x)
    if missing:
        print("missing required global-agent entrypoints: " + ", ".join(missing), file=sys.stderr)
        return 1
    # Validate the primary neutral reference if present.
    ref = root/"agentpress/examples/agent-knowledge-sharing"
    code, errors, warnings = audit_root(ref, strict=True)
    if code:
        print(json.dumps({"primary_reference_errors": errors, "warnings": warnings}, indent=2), file=sys.stderr)
        return code
    total, detail = score_value(ref)
    print(f"primary_reference_score: {total}/100")
    print("canonical_url: https://barneywohl.github.io/agentpress/")
    print("raw_fallback: https://raw.githubusercontent.com/barneywohl/agentpress/refs/heads/main/")
    return 0

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("out"); p.add_argument("--title", required=True); p.add_argument("--canonical"); p.add_argument("--summary"); p.add_argument("--primary-task"); p.add_argument("--task-type", default="agent_native_publication")
    p = sub.add_parser("validate"); p.add_argument("out")
    p = sub.add_parser("audit"); p.add_argument("out")
    p = sub.add_parser("score"); p.add_argument("out")
    p = sub.add_parser("build"); p.add_argument("out"); p.add_argument("--out", dest="dest", required=True)
    p = sub.add_parser("list"); p.add_argument("root", nargs="?", default="agentpress/examples"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("build-all"); p.add_argument("root", nargs="?", default="agentpress/examples"); p.add_argument("--out", dest="dest", required=True); p.add_argument("--clean", action="store_true")
    p = sub.add_parser("index-articles"); p.add_argument("root", nargs="?", default="agentpress/examples"); p.add_argument("--out", default="agentpress/articles"); p.add_argument("--base-url", default="https://barneywohl.github.io/agentpress")
    p = sub.add_parser("doctor"); p.add_argument("root", nargs="?", default=".")
    p = sub.add_parser("package"); p.add_argument("root", nargs="?", default="."); p.add_argument("--format", choices=["tar", "zip"], default="tar"); p.add_argument("--out", default="dist/agentpress-offline.tar.gz")
    args = ap.parse_args()
    if args.cmd == "init": init(args); return 0
    if args.cmd == "validate": return validate(args)
    if args.cmd == "audit": return audit(args)
    if args.cmd == "score": return score(args)
    if args.cmd == "build": return build(args)
    if args.cmd == "list": return list_examples(args)
    if args.cmd == "build-all": return build_all(args)
    if args.cmd == "index-articles": return index_articles(args)
    if args.cmd == "doctor": return doctor(args)
    if args.cmd == "package": return package_bundle(args)
if __name__ == "__main__":
    sys.exit(main())
