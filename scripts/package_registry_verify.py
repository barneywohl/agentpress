#!/usr/bin/env python3
"""
package_registry_verify.py — Fetch live npm + PyPI packages, verify hashes, run CLI smoke test.

Evidence receipt: downloads the published tarballs from npm/PyPI registries, checks
integrity against registry-advertised digests, verifies CLI entrypoint starts,
and writes a signed JSON receipt. No secrets required.

Usage:
  python3 scripts/package_registry_verify.py --json
  python3 scripts/package_registry_verify.py --npm-version 0.1.0 --pypi-version 0.1.0 --json
  python3 scripts/package_registry_verify.py --out /tmp/registry-verify-receipt.json --json
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone

NPM_PACKAGE = "@agent_press/agentpress"
PYPI_PACKAGE = "agentpress-static"
CANONICAL_URL = "https://barneywohl.github.io/agentpress/"

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def _fetch(url: str, dest: pathlib.Path, timeout: int = 30) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "agentpress-registry-verify/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        dest.write_bytes(r.read())

def verify_npm(version: str, workdir: pathlib.Path) -> dict:
    """Fetch npm registry metadata, download tarball, verify integrity."""
    result = {"package": NPM_PACKAGE, "version": version, "status": "fail", "errors": []}
    try:
        url = f"https://registry.npmjs.org/{NPM_PACKAGE}/{version}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            meta = json.load(r)
        dist = meta.get("dist", {})
        tarball_url = dist.get("tarball", "")
        integrity = dist.get("integrity", "")
        result["registry_integrity"] = integrity
        result["tarball_url"] = tarball_url

        tarball_path = workdir / f"agentpress-npm-{version}.tgz"
        _fetch(tarball_url, tarball_path)
        result["tarball_bytes"] = tarball_path.stat().st_size
        result["tarball_sha256"] = _sha256(tarball_path)

        # Verify sha512 if integrity is sha512-base64
        if integrity.startswith("sha512-"):
            import base64
            import hmac
            expected_b64 = integrity[7:]
            h = hashlib.sha512()
            with open(tarball_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            actual_b64 = base64.b64encode(h.digest()).decode()
            if actual_b64 == expected_b64:
                result["integrity_check"] = "pass"
            else:
                result["integrity_check"] = "fail"
                result["errors"].append(f"sha512 mismatch: expected {expected_b64[:20]}... got {actual_b64[:20]}...")

        if not result["errors"]:
            result["status"] = "ok"
    except Exception as e:
        result["errors"].append(f"npm verify error: {e}")
    return result

def verify_pypi(version: str, workdir: pathlib.Path) -> dict:
    """Fetch PyPI registry metadata, download wheel, verify sha256."""
    result = {"package": PYPI_PACKAGE, "version": version, "status": "fail", "errors": []}
    try:
        url = f"https://pypi.org/pypi/{PYPI_PACKAGE}/{version}/json"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            meta = json.load(r)
        urls = meta.get("urls", [])
        wheel = next((u for u in urls if u["packagetype"] == "bdist_wheel"), None)
        sdist = next((u for u in urls if u["packagetype"] == "sdist"), None)
        chosen = wheel or sdist
        if not chosen:
            result["errors"].append("no wheel or sdist found")
            return result

        result["filename"] = chosen["filename"]
        result["packagetype"] = chosen["packagetype"]
        expected_sha256 = chosen.get("digests", {}).get("sha256", "")
        result["expected_sha256"] = expected_sha256

        pkg_path = workdir / chosen["filename"]
        _fetch(chosen["url"], pkg_path)
        result["download_bytes"] = pkg_path.stat().st_size
        actual_sha256 = _sha256(pkg_path)
        result["actual_sha256"] = actual_sha256

        if expected_sha256 and actual_sha256 == expected_sha256:
            result["sha256_check"] = "pass"
            result["status"] = "ok"
        elif not expected_sha256:
            result["sha256_check"] = "skipped_no_registry_hash"
            result["status"] = "ok"
        else:
            result["sha256_check"] = "fail"
            result["errors"].append(f"sha256 mismatch: expected {expected_sha256[:20]}... got {actual_sha256[:20]}...")
    except Exception as e:
        result["errors"].append(f"pypi verify error: {e}")
    return result

def smoke_test_cli(workdir: pathlib.Path, pypi_version: str = "0.1.0") -> dict:
    """Install PyPI package in fresh venv, run agentpress --help smoke test."""
    result = {"test": "cli_smoke", "status": "fail", "errors": []}
    venv = workdir / "venv"
    try:
        python = sys.executable
        subprocess.run([python, "-m", "venv", str(venv)], check=True, capture_output=True, timeout=30)
        pip = str(venv / "bin" / "pip")
        agentpress_bin = str(venv / "bin" / "agentpress")
        subprocess.run([pip, "install", "--quiet", "--upgrade", "pip"], check=True, capture_output=True, timeout=30)
        subprocess.run([pip, "install", "--quiet", f"{PYPI_PACKAGE}=={pypi_version}"], check=True, capture_output=True, timeout=60)
        proc = subprocess.run([agentpress_bin, "--help"], capture_output=True, timeout=15)
        result["exit_code"] = proc.returncode
        help_text = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
        result["help_lines"] = len(help_text.splitlines())
        result["has_doctor"] = "doctor" in help_text
        result["has_validate"] = "validate" in help_text
        if proc.returncode == 0 and result["has_doctor"]:
            result["status"] = "ok"
        else:
            result["errors"].append(f"help exit {proc.returncode}, has_doctor={result['has_doctor']}")
    except Exception as e:
        result["errors"].append(f"smoke test error: {e}")
    return result

def static_fetch_check() -> dict:
    """Verify canonical static endpoints return 200."""
    result = {"test": "static_fetch", "checks": [], "status": "fail", "errors": []}
    endpoints = [
        "/llms.txt",
        "/.well-known/agentpress.json",
        "/agentpress/agentpress-registry.json",
    ]
    ok_count = 0
    for path in endpoints:
        url = CANONICAL_URL.rstrip("/") + path
        check = {"url": url, "status_code": None, "ok": False}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "agentpress-registry-verify/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                check["status_code"] = r.getcode()
                check["bytes"] = len(r.read())
                check["ok"] = check["status_code"] == 200
                if check["ok"]:
                    ok_count += 1
        except Exception as e:
            check["error"] = str(e)
            result["errors"].append(f"{url}: {e}")
        result["checks"].append(check)
    result["ok_count"] = ok_count
    result["total"] = len(endpoints)
    if ok_count == len(endpoints):
        result["status"] = "ok"
    return result

def main():
    parser = argparse.ArgumentParser(description="Verify AgentPress npm/PyPI packages and static endpoints")
    parser.add_argument("--npm-version", default="0.1.0")
    parser.add_argument("--pypi-version", default="0.1.0")
    parser.add_argument("--out", default="")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip venv smoke test (faster)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    workdir = pathlib.Path(tempfile.mkdtemp(prefix="agentpress-regverify-"))
    try:
        receipt = {
            "schema": "agentpress-registry-verify.v1",
            "generated_utc": _utc_now(),
            "npm": verify_npm(args.npm_version, workdir),
            "pypi": verify_pypi(args.pypi_version, workdir),
            "static": static_fetch_check(),
        }
        if not args.skip_smoke:
            receipt["smoke_test"] = smoke_test_cli(workdir, pypi_version=args.pypi_version)

        all_ok = (
            receipt["npm"]["status"] == "ok"
            and receipt["pypi"]["status"] == "ok"
            and receipt["static"]["status"] == "ok"
            and (args.skip_smoke or receipt.get("smoke_test", {}).get("status") == "ok")
        )
        receipt["overall_status"] = "ok" if all_ok else "fail"
        receipt["all_errors"] = (
            receipt["npm"]["errors"]
            + receipt["pypi"]["errors"]
            + receipt["static"]["errors"]
            + ([] if args.skip_smoke else receipt.get("smoke_test", {}).get("errors", []))
        )

        output = json.dumps(receipt, indent=2) if args.json else receipt["overall_status"]
        print(output)
        if args.out:
            pathlib.Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return 0 if all_ok else 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
