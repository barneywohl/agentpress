#!/usr/bin/env python3
import argparse, json, pathlib, shutil, sys, tarfile, tempfile, urllib.request, hashlib
from urllib.parse import urljoin

def read_url(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def main():
    ap=argparse.ArgumentParser(description='Install AgentPress offline package from static release index')
    ap.add_argument('--base-url', default='https://barneywohl.github.io/agentpress/')
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
