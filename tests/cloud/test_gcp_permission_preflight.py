from __future__ import annotations

import datetime as dt
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


NOW = dt.datetime(2026, 9, 7, 12, 10, tzinfo=dt.UTC)
PRINCIPAL = "fitnessos-tf-nonprod@fitnessos-nonprod.iam.gserviceaccount.com"


def conditional_policy(role: str, *, activation: str, expiration: str) -> dict:
    return {
        "version": 3,
        "bindings": [
            {
                "role": role,
                "members": [f"serviceAccount:{PRINCIPAL}"],
                "condition": {
                    "title": "fitnessos-b1-recovery-expiration",
                    "description": (
                        f"activation_utc={activation};expiration_utc={expiration};"
                        "maximum_minutes=60"
                    ),
                    "expression": f'request.time < timestamp("{expiration}")',
                },
            }
        ],
    }


def validate(policy: dict, role: str, activation: str, expiration: str) -> dict:
    return MODULE.validate_temporary_binding(
        policy,
        role=role,
        principal=PRINCIPAL,
        activation_time=activation,
        expiration_time=expiration,
        execution_time=NOW,
        minimum_remaining_minutes=20,
    )


@pytest.mark.parametrize("role", [MODULE.EXPECTED_PROJECT_ROLE, MODULE.EXPECTED_BILLING_ROLE])
def test_valid_sixty_minute_condition_passes(role: str) -> None:
    activation, expiration = "2026-09-07T12:00:00Z", "2026-09-07T13:00:00Z"
    assert (
        validate(
            conditional_policy(role, activation=activation, expiration=expiration),
            role,
            activation,
            expiration,
        )["result"]
        == "PASS"
    )


@pytest.mark.parametrize("role", [MODULE.EXPECTED_PROJECT_ROLE, MODULE.EXPECTED_BILLING_ROLE])
def test_unconditional_binding_fails(role: str) -> None:
    policy = {
        "version": 3,
        "bindings": [{"role": role, "members": [f"serviceAccount:{PRINCIPAL}"]}],
    }
    result = validate(policy, role, "2026-09-07T12:00:00Z", "2026-09-07T13:00:00Z")
    assert result["result"] == "FAIL"


@pytest.mark.parametrize("role", [MODULE.EXPECTED_PROJECT_ROLE, MODULE.EXPECTED_BILLING_ROLE])
def test_expiration_over_sixty_minutes_fails(role: str) -> None:
    activation, expiration = "2026-09-07T12:00:00Z", "2026-09-07T13:00:01Z"
    assert (
        validate(
            conditional_policy(role, activation=activation, expiration=expiration),
            role,
            activation,
            expiration,
        )["result"]
        == "FAIL"
    )


def test_expired_project_binding_fails() -> None:
    activation, expiration = "2026-09-07T11:00:00Z", "2026-09-07T12:00:00Z"
    policy = conditional_policy(
        MODULE.EXPECTED_PROJECT_ROLE, activation=activation, expiration=expiration
    )
    assert (
        validate(policy, MODULE.EXPECTED_PROJECT_ROLE, activation, expiration)["result"] == "FAIL"
    )


def test_malformed_project_condition_fails() -> None:
    activation, expiration = "2026-09-07T12:00:00Z", "2026-09-07T13:00:00Z"
    policy = conditional_policy(
        MODULE.EXPECTED_PROJECT_ROLE, activation=activation, expiration=expiration
    )
    policy["bindings"][0]["condition"]["expression"] = "true"
    assert (
        validate(policy, MODULE.EXPECTED_PROJECT_ROLE, activation, expiration)["result"] == "FAIL"
    )


def test_self_extension_capability_fails() -> None:
    granted = complete_permissions()
    granted["project"].add("resourcemanager.projects.setIamPolicy")
    report = MODULE.evaluate(granted, {"project": MODULE.PROJECT_PROHIBITED_PERMISSIONS})
    assert report["result"] == "FAIL"
    assert (
        "resourcemanager.projects.setIamPolicy"
        in report["scopes"]["project"]["prohibited_detected"]
    )


def test_unsupported_billing_condition_fails_closed() -> None:
    result = validate(
        {"version": 1, "bindings": []},
        MODULE.EXPECTED_BILLING_ROLE,
        "2026-09-07T12:00:00Z",
        "2026-09-07T13:00:00Z",
    )
    assert result["result"] == "FAIL"
