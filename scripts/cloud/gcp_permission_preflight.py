#!/usr/bin/env python3
"""Fail-closed permission preflight for the FitnessOS NONPROD Terraform identity."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_PERMISSIONS = {
    "resourcemanager.projects.get",
    "resourcemanager.projects.getIamPolicy",
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

PROJECT_PROHIBITED_PERMISSIONS = {
    "artifactregistry.repositories.setIamPolicy",
    "iam.roles.create",
    "iam.roles.update",
    "iam.serviceAccountKeys.create",
    "iam.serviceAccounts.actAs",
    "iam.serviceAccounts.getAccessToken",
    "iam.serviceAccounts.setIamPolicy",
    "resourcemanager.projects.setIamPolicy",
    "secretmanager.secrets.setIamPolicy",
    "secretmanager.versions.access",
    "secretmanager.versions.add",
    "secretmanager.versions.destroy",
    "secretmanager.versions.disable",
    "secretmanager.versions.enable",
}

BILLING_PERMISSIONS = {
    "billing.budgets.create",
    "billing.budgets.delete",
    "billing.budgets.get",
    "billing.budgets.list",
    "billing.budgets.update",
}

BILLING_PROHIBITED_PERMISSIONS = {"billing.accounts.setIamPolicy"}

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

EXPECTED_PROJECT_ROLE = "projects/fitnessos-nonprod/roles/fitnessosB1Recovery"
EXPECTED_BILLING_ROLE = "roles/billing.costsManager"
CONDITION_RE = re.compile(r"^request\.time\s*<\s*timestamp\([\'\"]([^\'\"]+)[\'\"]\)$")
DESCRIPTION_RE = re.compile(r"^activation_utc=([^;]+);expiration_utc=([^;]+);maximum_minutes=60$")


def _utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        raise ValueError("timestamp must be UTC")
    return parsed.astimezone(dt.UTC)


def validate_temporary_binding(
    policy: dict[str, object],
    *,
    role: str,
    principal: str,
    activation_time: str,
    expiration_time: str,
    execution_time: dt.datetime,
    minimum_remaining_minutes: int,
) -> dict[str, object]:
    member = f"serviceAccount:{principal}"
    matches = [
        binding
        for binding in policy.get("bindings", [])
        if binding.get("role") == role and member in binding.get("members", [])
    ]
    errors: list[str] = []
    if len(matches) != 1:
        errors.append("expected exactly one temporary binding")
        return {"result": "FAIL", "errors": errors}

    condition = matches[0].get("condition")
    if not isinstance(condition, dict):
        return {"result": "FAIL", "errors": ["temporary binding is unconditional"]}

    expression = condition.get("expression", "")
    expression_match = CONDITION_RE.fullmatch(expression.strip())
    description_match = DESCRIPTION_RE.fullmatch(condition.get("description", "").strip())
    if not expression_match:
        errors.append("condition expression is malformed")
    if not description_match:
        errors.append("condition description is malformed")
    if errors:
        return {"result": "FAIL", "errors": errors, "expression": expression}

    encoded_expiration = expression_match.group(1)
    encoded_activation, described_expiration = description_match.groups()
    try:
        activation = _utc(activation_time)
        expiration = _utc(expiration_time)
        expression_expiration = _utc(encoded_expiration)
        description_activation = _utc(encoded_activation)
        description_expiration = _utc(described_expiration)
    except ValueError:
        return {"result": "FAIL", "errors": ["condition timestamp is malformed"]}

    if not (
        activation == description_activation
        and expiration == expression_expiration == description_expiration
    ):
        errors.append("binding timestamps do not match approved workflow inputs")
    duration = expiration - activation
    remaining = expiration - execution_time
    if duration <= dt.timedelta(0) or duration > dt.timedelta(minutes=60):
        errors.append("activation window is not within 0–60 minutes")
    if execution_time < activation:
        errors.append("activation window has not started")
    if remaining <= dt.timedelta(0):
        errors.append("temporary binding has expired")
    if remaining < dt.timedelta(minutes=minimum_remaining_minutes):
        errors.append("remaining recovery window is insufficient")

    return {
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "role": role,
        "condition_title": condition.get("title"),
        "condition_expression": expression,
        "activation_utc": activation.isoformat().replace("+00:00", "Z"),
        "expiration_utc": expiration.isoformat().replace("+00:00", "Z"),
        "maximum_minutes": 60,
        "remaining_minutes": max(0, int(remaining.total_seconds() // 60)),
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


def _get_policy(url: str, token: str) -> dict[str, object]:
    body = json.dumps({"options": {"requestedPolicyVersion": 3}}).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        policy = json.load(response)
    if policy.get("version") != 3:
        raise ValueError("IAM policy version 3 is required")
    return policy


def _bucket_test_permissions(bucket: str, permissions: set[str], token: str) -> set[str]:
    query = urllib.parse.urlencode(
        [("permissions", permission) for permission in sorted(permissions)]
    )
    bucket_name = urllib.parse.quote(bucket, safe="")
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/iam/testPermissions?{query}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return set(json.load(response).get("permissions", []))


def evaluate(
    granted: dict[str, set[str]], prohibited: dict[str, set[str]] | None = None
) -> dict[str, object]:
    scopes: dict[str, object] = {}
    all_complete = True
    for scope, required in REQUIRED.items():
        actual = granted.get(scope, set())
        missing = sorted(required - actual)
        detected = sorted((prohibited or {}).get(scope, set()) & actual)
        scopes[scope] = {
            "required": sorted(required),
            "granted": sorted(actual & required),
            "missing": missing,
            "prohibited_detected": detected,
            "result": "PASS" if not missing and not detected else "FAIL",
        }
        all_complete = all_complete and not missing and not detected
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
    parser.add_argument("--activation-time", required=True)
    parser.add_argument("--expiration-time", required=True)
    parser.add_argument("--minimum-remaining-minutes", type=int, default=20)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fixture-dir", type=Path)
    args = parser.parse_args()

    try:
        if args.fixture_dir:
            granted = _load_fixtures(args.fixture_dir)
        else:
            token = _access_token()
            project_policy = _get_policy(
                f"https://cloudresourcemanager.googleapis.com/v1/projects/{args.project}:getIamPolicy",
                token,
            )
            billing_policy = _get_policy(
                f"https://cloudbilling.googleapis.com/v1/billingAccounts/{args.billing_account}:getIamPolicy",
                token,
            )
            requested_project_permissions = PROJECT_PERMISSIONS | PROJECT_PROHIBITED_PERMISSIONS
            requested_billing_permissions = BILLING_PERMISSIONS | BILLING_PROHIBITED_PERMISSIONS
            granted = {
                "project": _post_test_permissions(
                    f"https://cloudresourcemanager.googleapis.com/v1/projects/{args.project}:testIamPermissions",
                    requested_project_permissions,
                    token,
                ),
                "billing_account": _post_test_permissions(
                    f"https://cloudbilling.googleapis.com/v1/billingAccounts/{args.billing_account}:testIamPermissions",
                    requested_billing_permissions,
                    token,
                ),
                "state_bucket": _bucket_test_permissions(
                    args.state_bucket, BUCKET_PERMISSIONS, token
                ),
            }
        prohibited = {
            "project": PROJECT_PROHIBITED_PERMISSIONS,
            "billing_account": BILLING_PROHIBITED_PERMISSIONS,
        }
        report = evaluate(granted, prohibited)
        if not args.fixture_dir:
            execution_time = dt.datetime.now(dt.UTC)
            bindings = {
                "project": validate_temporary_binding(
                    project_policy,
                    role=EXPECTED_PROJECT_ROLE,
                    principal=args.principal,
                    activation_time=args.activation_time,
                    expiration_time=args.expiration_time,
                    execution_time=execution_time,
                    minimum_remaining_minutes=args.minimum_remaining_minutes,
                ),
                "billing_account": validate_temporary_binding(
                    billing_policy,
                    role=EXPECTED_BILLING_ROLE,
                    principal=args.principal,
                    activation_time=args.activation_time,
                    expiration_time=args.expiration_time,
                    execution_time=execution_time,
                    minimum_remaining_minutes=args.minimum_remaining_minutes,
                ),
            }
            report["bindings"] = bindings
            report["execution_timestamp"] = execution_time.isoformat().replace("+00:00", "Z")
            if any(binding["result"] != "PASS" for binding in bindings.values()):
                report["result"] = "FAIL"
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
