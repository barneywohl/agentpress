#!/usr/bin/env python3
"""Build SHA256 manifest for canonical AgentPress public assets."""
from pathlib import Path
import datetime, hashlib, json
ROOT=Path(__file__).resolve().parents[1]
manifest_path=ROOT/'discovery/all-assets-manifest.json'
assets=json.loads(manifest_path.read_text())['assets']
rows=[]
for a in assets:
    p=ROOT/a['path']
    if p.exists() and p.is_file():
        b=p.read_bytes()
        rows.append({'path':a['path'],'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'github_pages_url':a.get('github_pages_url'),'raw_githubusercontent_url':a.get('raw_githubusercontent_url')})
out={'schema_version':'2026-05-02.agentpress-hash-manifest.v1','generated_at_utc':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),'asset_count':len(rows),'algorithm':'sha256','assets':rows}
(ROOT/'agentpress/hash-manifest.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print(f'wrote agentpress/hash-manifest.json assets={len(rows)}')
