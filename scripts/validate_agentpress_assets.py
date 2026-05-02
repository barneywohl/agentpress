#!/usr/bin/env python3
"""Validate all AgentPress example assets in one command."""
import json
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = ROOT / 'agentpress/examples'


def discover_examples() -> list[pathlib.Path]:
    if not EXAMPLES_ROOT.exists():
        return []
    return sorted(
        p for p in EXAMPLES_ROOT.iterdir()
        if p.is_dir() and (p / 'agent-task-card.json').exists()
    )


def parse_repo_json_xml() -> None:
    for p in ROOT.rglob('*.json'):
        if '.git' in p.parts or '__pycache__' in p.parts:
            continue
        json.loads(p.read_text(encoding='utf-8'))
    for p in ROOT.rglob('*.xml'):
        if '.git' in p.parts or '__pycache__' in p.parts:
            continue
        ET.parse(p)


def validate_article_database(examples: list[pathlib.Path]) -> None:
    article_index = ROOT / 'agentpress/articles/article-index.json'
    if not article_index.exists():
        raise SystemExit('missing agentpress/articles/article-index.json; run scripts/agentpress.py index-articles')
    data = json.loads(article_index.read_text(encoding='utf-8'))
    rows = data.get('articles') or []
    expected = {p.name for p in examples}
    indexed = {r.get('slug') for r in rows}
    missing = sorted(expected - indexed)
    extra = sorted(indexed - expected)
    if missing or extra or data.get('count') != len(rows):
        raise SystemExit(f'article index mismatch: missing={missing} extra={extra} count={data.get("count")} rows={len(rows)}')
    for ex in examples:
        card = ex / 'article-card.json'
        if not card.exists():
            raise SystemExit(f'missing {card.relative_to(ROOT)}; run scripts/agentpress.py index-articles')
        payload = json.loads(card.read_text(encoding='utf-8'))
        for key in ['type', 'slug', 'canonical_url', 'summary_for_agents', 'machine_entrypoints']:
            if key not in payload:
                raise SystemExit(f'{card.relative_to(ROOT)} missing {key}')
        if payload.get('type') != 'agentpress_article':
            raise SystemExit(f'{card.relative_to(ROOT)} has wrong type {payload.get("type")!r}')


def run(cmd):
    print('+', ' '.join(str(c) for c in cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    examples = discover_examples()
    if not examples:
        print('no AgentPress examples found', file=sys.stderr)
        return 1
    run(['python3', 'scripts/agentpress.py', 'index-articles'])
    for ex in examples:
        rel = ex.relative_to(ROOT)
        run(['python3', 'scripts/agentpress.py', 'validate', str(rel)])
        run(['python3', 'scripts/agentpress.py', 'audit', str(rel)])
        run(['python3', 'scripts/agentpress.py', 'score', str(rel)])
    validate_article_database(examples)
    run(['python3', 'scripts/agentpress.py', 'eval', 'agentpress/examples'])
    run(['python3', 'scripts/agentpress.py', 'check-registry'])
    run(['python3', 'scripts/agentpress.py', 'check-openapi'])
    parse_repo_json_xml()
    print(f'agentpress asset validation ok ({len(examples)} examples)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
