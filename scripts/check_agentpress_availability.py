#!/usr/bin/env python3
"""Check AgentPress public/local availability and machine-readable assets."""
import argparse, json, pathlib, sys, urllib.request, urllib.error
from urllib.parse import urljoin

REQUIRED_PATHS = [
    "",
    "llms.txt",
    "sitemap.xml",
    "agentpress/",
    "agentpress/agentpress-registry.json",
    "agentpress/GLOBAL_READINESS_GAP_LIST.md",
    "agentpress/examples/api-docs-handoff/",
    "agentpress/examples/api-docs-handoff/agent-task-card.json",
    "agentpress/examples/api-docs-handoff/.well-known/ai-ingestion.json",
]


def check_url(base: str) -> int:
    failures = []
    for path in REQUIRED_PATHS:
        url = urljoin(base if base.endswith('/') else base + '/', path)
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'AgentPressAvailability/1.0 (+https://github.com/barneywohl/agentpress)'
            })
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read()
                code = resp.status
        except urllib.error.HTTPError as e:
            failures.append(f"{e.code} {url}")
            continue
        except Exception as e:
            failures.append(f"ERROR {url}: {e}")
            continue
        print(f"{code} {len(body)} {url}")
        if code != 200:
            failures.append(f"{code} {url}")
        if path.endswith('.json'):
            try:
                json.loads(body.decode('utf-8'))
            except Exception as e:
                failures.append(f"invalid json {url}: {e}")
    if failures:
        print("availability failures:", file=sys.stderr)
        for f in failures:
            print(f"- {f}", file=sys.stderr)
        return 1
    return 0


def check_local(root: pathlib.Path) -> int:
    failures = []
    for path in REQUIRED_PATHS:
        p = root / path
        if path.endswith('/') or path == '':
            p = p / 'index.html'
        if not p.exists():
            failures.append(f"missing {p}")
            continue
        print(f"LOCAL {p}")
        if p.suffix == '.json':
            try:
                json.loads(p.read_text(encoding='utf-8'))
            except Exception as e:
                failures.append(f"invalid json {p}: {e}")
    if failures:
        print("local availability failures:", file=sys.stderr)
        for f in failures:
            print(f"- {f}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-url', help='Public base URL to check')
    ap.add_argument('--root', default='.', help='Local repo root to check')
    args = ap.parse_args()
    if args.base_url:
        return check_url(args.base_url)
    return check_local(pathlib.Path(args.root))

if __name__ == '__main__':
    raise SystemExit(main())
