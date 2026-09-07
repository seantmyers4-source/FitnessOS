#!/usr/bin/env python3
"""Fail-closed permission preflight for the FitnessOS NONPROD Terraform identity."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_PERMISSIONS = {
    "resourcemanager.projects.get",
    "serviceusage.services.get",
    "serviceusage.services.list",
    "serviceusage.services.use",
    "serviceusage.services.enable",
    "serviceusage.services.disable",
    "serviceusage.operations.get",
    "iam.serviceAccounts.create",
    "iam.serviceAccounts.delete",
    "iam.serviceAccounts.get",
    "iam.serviceAccounts.list",
    "iam.serviceAccounts.update",
    "artifactregistry.locations.get",
    "artifactregistry.locations.list",
    "artifactregistry.repositories.create",
    "artifactregistry.repositories.delete",
    "artifactregistry.repositories.get",
    "artifactregistry.repositories.list",
    "artifactregistry.repositories.update",
    "secretmanager.locations.get",
    "secretmanager.locations.list",
    "secretmanager.secrets.create",
    "secretmanager.secrets.delete",
    "secretmanager.secrets.get",
    "secretmanager.secrets.list",
    "secretmanager.secrets.update",
    "logging.buckets.get",
    "logging.buckets.update",
}

BILLING_PERMISSIONS = {
    "billing.budgets.create",
    "billing.budgets.delete",
    "billing.budgets.get",
    "billing.budgets.list",
    "billing.budgets.update",
}

BUCKET_PERMISSIONS = {
    "storage.objects.create",
    "storage.objects.delete",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.update",
}

REQUIRED = {
    "project": PROJECT_PERMISSIONS,
    "billing_account": BILLING_PERMISSIONS,
    "state_bucket": BUCKET_PERMISSIONS,
}


def _access_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _post_test_permissions(url: str, permissions: set[str], token: str) -> set[str]:
    body = json.dumps({"permissions": sorted(permissions)}).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return set(json.load(response).get("permissions", []))


def _bucket_test_permissions(bucket: str, permissions: set[str], token: str) -> set[str]:
    query = urllib.parse.urlencode(
        [("permissions", permission) for permission in sorted(permissions)]
    )
    bucket_name = urllib.parse.quote(bucket, safe="")
    url = (
        f"https://storage.googleapis.com/storage/v1/b/{bucket_name}"
        f"/iam/testPermissions?{query}"
    )
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return set(json.load(response).get("permissions", []))


def evaluate(granted: dict[str, set[str]]) -> dict[str, object]:
    scopes: dict[str, object] = {}
    all_complete = True
    for scope, required in REQUIRED.items():
        actual = granted.get(scope, set())
        missing = sorted(required - actual)
        scopes[scope] = {
            "required": sorted(required),
            "granted": sorted(actual & required),
            "missing": missing,
            "result": "PASS" if not missing else "FAIL",
        }
        all_complete = all_complete and not missing
    return {"result": "PASS" if all_complete else "FAIL", "scopes": scopes}


def _load_fixtures(path: Path) -> dict[str, set[str]]:
    return {
        scope: set(json.loads((path / f"{scope}.json").read_text()).get("permissions", []))
        for scope in REQUIRED
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--billing-account", required=True)
    parser.add_argument("--state-bucket", required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fixture-dir", type=Path)
    args = parser.parse_args()

    try:
        if args.fixture_dir:
            granted = _load_fixtures(args.fixture_dir)
        else:
            token = _access_token()
            granted = {
                "project": _post_test_permissions(
                    f"https://cloudresourcemanager.googleapis.com/v1/projects/{args.project}:testIamPermissions",
                    PROJECT_PERMISSIONS,
                    token,
                ),
                "billing_account": _post_test_permissions(
                    f"https://cloudbilling.googleapis.com/v1/billingAccounts/{args.billing_account}:testIamPermissions",
                    BILLING_PERMISSIONS,
                    token,
                ),
                "state_bucket": _bucket_test_permissions(
                    args.state_bucket, BUCKET_PERMISSIONS, token
                ),
            }
        report = evaluate(granted)
    except Exception as exc:  # Fail closed without exposing credential material.
        report = {"result": "FAIL", "error": f"permission evaluation failed: {type(exc).__name__}"}

    report.update(
        {
            "principal": args.principal,
            "project": args.project,
            "billing_account": args.billing_account,
            "state_bucket": args.state_bucket,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
