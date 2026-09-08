#!/usr/bin/env python3
"""Sanitize and validate GitHub OIDC claims without retaining a token."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Any

ALLOWED_OUTPUT = {
    "repository", "repository_owner", "workflow_ref", "event_name",
    "ref", "base_ref", "sha", "run_id", "run_attempt",
}


class ClaimError(ValueError):
    """Fail-closed OIDC claim error."""


def decode_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ClaimError("malformed JWT")
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    value = json.loads(base64.urlsafe_b64decode(padded))
    if not isinstance(value, dict):
        raise ClaimError("claim payload must be an object")
    return value


def sanitize(claims: dict[str, Any]) -> dict[str, Any]:
    return {key: claims.get(key) for key in sorted(ALLOWED_OUTPUT)}


def match_claims(manifest: dict[str, Any], identity: str, claims: dict[str, Any]) -> bool:
    required = {"repository", "repository_owner", "workflow_ref", "event_name", "ref"}
    if not required.issubset(claims):
        return False
    if claims["repository"] != "seantmyers4-source/FitnessOS":
        return False
    if claims["repository_owner"] != "seantmyers4-source":
        return False
    workflow = str(claims["workflow_ref"]).split("@", 1)[0]
    for rule in manifest["trust"]:
        if rule["identity"] != identity or rule["workflow"] != workflow:
            continue
        if rule["event"] != claims["event_name"]:
            continue
        if "ref" in rule and rule["ref"] != claims["ref"]:
            continue
        if "ref_prefix" in rule and not str(claims["ref"]).startswith(rule["ref_prefix"]):
            continue
        if "base_ref" in rule and rule["base_ref"] != claims.get("base_ref"):
            continue
        return True
    return False


def evidence(manifest: dict[str, Any], identity: str, token: str) -> dict[str, Any]:
    claims = decode_payload(token)
    safe = sanitize(claims)
    passed = match_claims(manifest, identity, claims)
    return {
        "result": "PASS" if passed else "FAIL",
        "identity_class": identity,
        "claims": safe,
        "raw_token_retained": False,
        "terraform_eligible": False,
        "cloud_mutation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--identity", choices=("plan", "apply"), required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    token = args.token_file.read_text().strip()
    report = evidence(manifest, args.identity, token)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
