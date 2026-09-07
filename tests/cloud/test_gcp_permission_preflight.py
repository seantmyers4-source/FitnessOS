from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts/cloud/gcp_permission_preflight.py"
SPEC = importlib.util.spec_from_file_location("gcp_permission_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def complete_permissions() -> dict[str, set[str]]:
    return {scope: set(permissions) for scope, permissions in MODULE.REQUIRED.items()}


@pytest.mark.parametrize(
    ("scope", "permission"),
    [
        ("project", "serviceusage.services.enable"),
        ("project", "iam.serviceAccounts.create"),
        ("billing_account", "billing.budgets.create"),
        ("project", "artifactregistry.repositories.create"),
        ("project", "secretmanager.secrets.create"),
        ("project", "logging.buckets.update"),
        ("state_bucket", "storage.objects.get"),
    ],
)
def test_missing_permission_fails_closed(scope: str, permission: str) -> None:
    granted = complete_permissions()
    granted[scope].remove(permission)

    report = MODULE.evaluate(granted)

    assert report["result"] == "FAIL"
    assert permission in report["scopes"][scope]["missing"]


def test_complete_permission_set_passes() -> None:
    report = MODULE.evaluate(complete_permissions())

    assert report["result"] == "PASS"
    assert all(scope["result"] == "PASS" for scope in report["scopes"].values())
