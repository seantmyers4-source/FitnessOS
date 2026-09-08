#!/usr/bin/env python3
"""Validate and dry-run the FitnessOS IAM/WIF activation manifest.

This module never calls a cloud API and never writes an IAM policy.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

POLICY_VERSION = 3


class ActivationError(ValueError):
    """Fail-closed activation package error."""


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ActivationError("manifest must be an object")
    return value


def validate_manifest(manifest: dict[str, Any]) -> None:
    identities = manifest["identities"]
    if identities["plan"] == identities["apply"]:
        raise ActivationError("Plan and Apply identities must differ")
    expected_mapping = {
        "google.subject": "assertion.sub",
        "attribute.repository": "assertion.repository",
        "attribute.repository_owner": "assertion.repository_owner",
        "attribute.ref": "assertion.ref",
        "attribute.base_ref": "assertion.base_ref",
        "attribute.event_name": "assertion.event_name",
        "attribute.workflow_ref": "assertion.workflow_ref",
    }
    if manifest["wif"]["attribute_mapping"] != expected_mapping:
        raise ActivationError("WIF mapping differs from approved mapping")
    if "job_workflow_ref" in json.dumps(manifest["wif"]):
        raise ActivationError("reusable-workflow claim is prohibited")
    plan = set(manifest["custom_roles"]["plan"]["permissions"])
    apply = set(manifest["custom_roles"]["apply"]["permissions"])
    if plan != apply or manifest["custom_roles"]["plan"]["id"] == manifest["custom_roles"]["apply"]["id"]:
        raise ActivationError("independent read roles must have equal contents and distinct IDs")
    backend = set(manifest["custom_roles"]["backend"]["permissions"])
    if backend != {"storage.objects.get", "storage.objects.list", "storage.objects.create", "storage.objects.delete"}:
        raise ActivationError("backend permission ceiling violated")
    prefix = manifest["backend"]["canonical_prefix"]
    expected = (
        "projects/_/buckets/fitnessos-nonprod-tfstate-578189272278/"
        "objects/fitnessos/nonprod/foundation/"
    )
    if prefix != expected or manifest["backend"]["condition"] != f'resource.name.startsWith("{expected}")':
        raise ActivationError("backend namespace condition is not exact")
    if manifest["temporary_recovery"] != {
        "maximum_minutes": 60,
        "minimum_remaining_minutes": 20,
        "self_extension": False,
        "manual_revocation": True,
    }:
        raise ActivationError("temporary recovery boundary changed")


def _canonical(binding: dict[str, Any]) -> str:
    return json.dumps(binding, sort_keys=True, separators=(",", ":"))


def insert_binding(
    policy: dict[str, Any], binding: dict[str, Any], *, expected_etag: str
) -> dict[str, Any]:
    if policy.get("version") != POLICY_VERSION or policy.get("etag") != expected_etag:
        raise ActivationError("version-3 policy or etag mismatch")
    result = copy.deepcopy(policy)
    bindings = result.setdefault("bindings", [])
    if any(_canonical(item) == _canonical(binding) for item in bindings):
        return result
    bindings.append(copy.deepcopy(binding))
    return result


def remove_binding(
    policy: dict[str, Any], binding: dict[str, Any], *, expected_etag: str
) -> dict[str, Any]:
    if policy.get("version") != POLICY_VERSION or policy.get("etag") != expected_etag:
        raise ActivationError("version-3 policy or etag mismatch")
    result = copy.deepcopy(policy)
    result["bindings"] = [
        item for item in result.get("bindings", []) if _canonical(item) != _canonical(binding)
    ]
    return result


def dry_run(manifest: dict[str, Any]) -> dict[str, Any]:
    validate_manifest(manifest)
    return {
        "result": "PASS",
        "mode": "DRY_RUN",
        "cloud_mutation": False,
        "identities": manifest["identities"],
        "custom_role_ids": [role["id"] for role in manifest["custom_roles"].values()],
        "backend_condition": manifest["backend"]["condition"],
        "trust_binding_count": len(manifest["trust"]),
        "state_baseline": manifest["state_baseline"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = dry_run(load_manifest(args.manifest))
    except Exception as exc:
        report = {
            "result": "FAIL",
            "mode": "DRY_RUN",
            "cloud_mutation": False,
            "error": type(exc).__name__,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
