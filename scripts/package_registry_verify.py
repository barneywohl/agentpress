#!/usr/bin/env python3
"""Verify package registry tarball integrity metadata.

Small, dependency-free checker for npm-style Subresource Integrity strings
(`sha512-...` or `sha256-...`). It is intentionally safe for local smoke tests:
without a tarball/integrity pair it reports a skipped check instead of touching
network registries or credentials.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash_b64(path: pathlib.Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return base64.b64encode(h.digest()).decode("ascii")


def _write_feedback_receipt(feedback_out: pathlib.Path, verification: dict) -> dict:
    feedback_out.parent.mkdir(parents=True, exist_ok=True)
    verification_snapshot = {k: v for k, v in verification.items() if k != "feedback_receipt"}
    rating = 5 if verification.get("status") == "ok" else 1
    entry = {
        "schema_version": "2026-05-06.agentpress-feedback.v1",
        "generated_utc": _utc_now(),
        "feedback_type": "package_registry_verify_receipt",
        "source": "package-registry-verify",
        "target": verification.get("tarball_path") or "package-registry-metadata",
        "rating": rating,
        "evidence": f"package registry verify {verification.get('status')} integrity_check={verification.get('integrity_check')}",
        "metadata": {"verification": verification_snapshot},
        "feedback_path": str(feedback_out),
    }
    with feedback_out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def verify_integrity(tarball_path: pathlib.Path | None, integrity: str | None) -> dict:
    result = {
        "schema_version": "2026-05-06.agentpress-package-registry-verify.v1",
        "status": "ok",
        "generated_utc": _utc_now(),
        "tarball_path": str(tarball_path) if tarball_path else None,
        "integrity": integrity or "",
        "integrity_check": None,
        "errors": [],
    }

    if not tarball_path or not integrity:
        result["integrity_check"] = "skipped_no_tarball_or_integrity"
        return result

    if not tarball_path.exists():
        result["status"] = "fail"
        result["integrity_check"] = "fail"
        result["errors"].append(f"missing tarball: {tarball_path}")
        return result

    if integrity.startswith("sha512-"):
        algorithm = "sha512"
        expected_b64 = integrity[len("sha512-"):]
    elif integrity.startswith("sha256-"):
        algorithm = "sha256"
        expected_b64 = integrity[len("sha256-"):]
    else:
        result["integrity_check"] = "skipped_no_recognized_scheme"
        result["errors"].append("No recognized integrity scheme (sha256/sha512) in registry metadata")
        return result

    actual_b64 = _hash_b64(tarball_path, algorithm)
    if actual_b64 == expected_b64:
        result["integrity_check"] = "pass"
    else:
        result["status"] = "fail"
        result["integrity_check"] = "fail"
        result["errors"].append(
            f"{algorithm} mismatch: expected {expected_b64[:20]}... got {actual_b64[:20]}..."
        )
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tarball", nargs="?", help="Path to registry tarball to verify")
    ap.add_argument("--integrity", help="npm-style integrity string, e.g. sha512-... or sha256-...")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--feedback-out", help="Append verification receipt to AgentPress feedback JSONL")
    args = ap.parse_args(argv)

    payload = verify_integrity(pathlib.Path(args.tarball) if args.tarball else None, args.integrity)
    if args.feedback_out and payload["status"] == "ok":
        payload["feedback_receipt"] = _write_feedback_receipt(pathlib.Path(args.feedback_out), payload)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"{payload['status']} integrity_check={payload['integrity_check']}")
        for err in payload["errors"]:
            print(f"error: {err}", file=sys.stderr)
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
