#!/usr/bin/env python3
"""Fail-closed preflight for the dedicated read-only Terraform Plan identity."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PLAN_PRINCIPAL = "fitnessos-tf-plan-np@fitnessos-nonprod.iam.gserviceaccount.com"
APPLY_PRINCIPAL = "fitnessos-tf-nonprod@fitnessos-nonprod.iam.gserviceaccount.com"

PROJECT_READ_PERMISSIONS = {
    "artifactregistry.locations.get",
    "artifactregistry.locations.list",
    "artifactregistry.repositories.get",
    "artifactregistry.repositories.list",
    "billing.resourcebudgets.read",
    "iam.serviceAccounts.get",
    "iam.serviceAccounts.list",
    "logging.buckets.get",
    "resourcemanager.projects.get",
    "secretmanager.locations.get",
    "secretmanager.locations.list",
    "secretmanager.secrets.get",
    "secretmanager.secrets.list",
    "serviceusage.services.get",
    "serviceusage.services.list",
}

BACKEND_PERMISSIONS = {
    "storage.objects.create",
    "storage.objects.delete",
    "storage.objects.get",
    "storage.objects.list",
}

BACKEND_PROHIBITED_PERMISSIONS = {
    "storage.buckets.setIamPolicy",
    "storage.objects.update",
}

PROHIBITED_PERMISSIONS = {
    "artifactregistry.repositories.create",
    "artifactregistry.repositories.delete",
    "artifactregistry.repositories.setIamPolicy",
    "artifactregistry.repositories.update",
    "billing.accounts.setIamPolicy",
    "billing.budgets.create",
    "billing.budgets.delete",
    "billing.budgets.update",
    "billing.resourcebudgets.write",
    "iam.roles.create",
    "iam.roles.update",
    "iam.serviceAccountKeys.create",
    "iam.serviceAccounts.actAs",
    "iam.serviceAccounts.create",
    "iam.serviceAccounts.delete",
    "iam.serviceAccounts.getAccessToken",
    "iam.serviceAccounts.setIamPolicy",
    "iam.serviceAccounts.update",
    "logging.buckets.update",
    "resourcemanager.projects.setIamPolicy",
    "secretmanager.secrets.create",
    "secretmanager.secrets.delete",
    "secretmanager.secrets.setIamPolicy",
    "secretmanager.secrets.update",
    "secretmanager.versions.access",
    "secretmanager.versions.add",
    "secretmanager.versions.destroy",
    "secretmanager.versions.disable",
    "secretmanager.versions.enable",
    "serviceusage.services.disable",
    "serviceusage.services.enable",
} | BACKEND_PROHIBITED_PERMISSIONS

ALLOWED_WORKFLOWS = {
    ".github/workflows/terraform-nonprod-plan.yml",
    ".github/workflows/terraform-nonprod-drift.yml",
}


def evaluate(
    *, principal: str, workflow_ref: str, project_granted: set[str], backend_granted: set[str]
) -> dict[str, object]:
    missing_project = sorted(PROJECT_READ_PERMISSIONS - project_granted)
    missing_backend = sorted(BACKEND_PERMISSIONS - backend_granted)
    prohibited = sorted(PROHIBITED_PERMISSIONS & (project_granted | backend_granted))
    workflow_path = workflow_ref.split("@", 1)[0].removeprefix("seantmyers4-source/FitnessOS/")
    errors: list[str] = []
    if principal != PLAN_PRINCIPAL:
        errors.append("unexpected Plan principal")
    if principal == APPLY_PRINCIPAL:
        errors.append("Apply principal is prohibited in Plan workflows")
    if workflow_path not in ALLOWED_WORKFLOWS:
        errors.append("workflow is not authorized for the Plan identity")
    if missing_project:
        errors.append("required project read permissions are missing")
    if missing_backend:
        errors.append("required backend state/lock permissions are missing")
    if prohibited:
        errors.append("prohibited mutation permission detected")
    return {
        "result": "PASS" if not errors else "FAIL",
        "terraform_eligible": not errors,
        "principal": principal,
        "workflow_ref": workflow_ref,
        "missing_project_permissions": missing_project,
        "missing_backend_permissions": missing_backend,
        "prohibited_permissions_detected": prohibited,
        "errors": errors,
    }


def _access_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _active_account() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _post_permissions(url: str, permissions: set[str], token: str) -> set[str]:
    request = urllib.request.Request(
        url,
        data=json.dumps({"permissions": sorted(permissions)}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("permissions", []), list):
        raise ValueError("unexpected permission API response")
    return set(payload.get("permissions", []))


def _bucket_permissions(bucket: str, permissions: set[str], token: str) -> set[str]:
    query = urllib.parse.urlencode(
        [("permissions", permission) for permission in sorted(permissions)]
    )
    name = urllib.parse.quote(bucket, safe="")
    request = urllib.request.Request(
        f"https://storage.googleapis.com/storage/v1/b/{name}/iam/testPermissions?{query}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("permissions", []), list):
        raise ValueError("unexpected Storage permission API response")
    return set(payload.get("permissions", []))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--state-bucket", required=True)
    parser.add_argument("--expected-principal", default=PLAN_PRINCIPAL)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fixture-dir", type=Path)
    args = parser.parse_args()
    try:
        if args.fixture_dir:
            principal = (args.fixture_dir / "principal.txt").read_text().strip()
            project = set(
                json.loads((args.fixture_dir / "project.json").read_text())["permissions"]
            )
            backend = set(
                json.loads((args.fixture_dir / "state_bucket.json").read_text())["permissions"]
            )
        else:
            token = _access_token()
            principal = _active_account()
            project = _post_permissions(
                f"https://cloudresourcemanager.googleapis.com/v1/projects/{args.project}:testIamPermissions",
                PROJECT_READ_PERMISSIONS | PROHIBITED_PERMISSIONS,
                token,
            )
            backend = _bucket_permissions(
                args.state_bucket,
                BACKEND_PERMISSIONS | BACKEND_PROHIBITED_PERMISSIONS,
                token,
            )
        report = evaluate(
            principal=principal,
            workflow_ref=args.workflow_ref,
            project_granted=project,
            backend_granted=backend,
        )
        if args.expected_principal != PLAN_PRINCIPAL:
            report["result"] = "FAIL"
            report["terraform_eligible"] = False
            report["errors"].append("configured Plan principal differs from architecture")
    except Exception as exc:
        report = {
            "result": "FAIL",
            "terraform_eligible": False,
            "error": f"Plan permission evaluation failed: {type(exc).__name__}",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
