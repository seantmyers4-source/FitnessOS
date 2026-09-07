from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
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


def test_future_project_binding_fails() -> None:
    activation, expiration = "2026-09-07T12:20:00Z", "2026-09-07T13:00:00Z"
    policy = conditional_policy(
        MODULE.EXPECTED_PROJECT_ROLE, activation=activation, expiration=expiration
    )
    assert (
        validate(policy, MODULE.EXPECTED_PROJECT_ROLE, activation, expiration)["result"] == "FAIL"
    )


def test_duplicate_project_binding_fails() -> None:
    activation, expiration = "2026-09-07T12:00:00Z", "2026-09-07T13:00:00Z"
    policy = conditional_policy(
        MODULE.EXPECTED_PROJECT_ROLE, activation=activation, expiration=expiration
    )
    policy["bindings"].append(dict(policy["bindings"][0]))
    assert (
        validate(policy, MODULE.EXPECTED_PROJECT_ROLE, activation, expiration)["result"] == "FAIL"
    )


def test_project_activation_timestamp_mismatch_fails() -> None:
    activation, expiration = "2026-09-07T12:00:00Z", "2026-09-07T13:00:00Z"
    policy = conditional_policy(
        MODULE.EXPECTED_PROJECT_ROLE,
        activation="2026-09-07T12:01:00Z",
        expiration=expiration,
    )
    assert (
        validate(policy, MODULE.EXPECTED_PROJECT_ROLE, activation, expiration)["result"] == "FAIL"
    )


def test_project_expiration_timestamp_mismatch_fails() -> None:
    activation, expiration = "2026-09-07T12:00:00Z", "2026-09-07T13:00:00Z"
    policy = conditional_policy(
        MODULE.EXPECTED_PROJECT_ROLE,
        activation=activation,
        expiration="2026-09-07T12:59:00Z",
    )
    assert (
        validate(policy, MODULE.EXPECTED_PROJECT_ROLE, activation, expiration)["result"] == "FAIL"
    )


def test_expired_billing_binding_fails() -> None:
    activation, expiration = "2026-09-07T11:00:00Z", "2026-09-07T12:00:00Z"
    policy = conditional_policy(
        MODULE.EXPECTED_BILLING_ROLE, activation=activation, expiration=expiration
    )
    assert (
        validate(policy, MODULE.EXPECTED_BILLING_ROLE, activation, expiration)["result"] == "FAIL"
    )


def test_malformed_billing_condition_fails() -> None:
    activation, expiration = "2026-09-07T12:00:00Z", "2026-09-07T13:00:00Z"
    policy = conditional_policy(
        MODULE.EXPECTED_BILLING_ROLE, activation=activation, expiration=expiration
    )
    policy["bindings"][0]["condition"]["expression"] = "request.time <"
    assert (
        validate(policy, MODULE.EXPECTED_BILLING_ROLE, activation, expiration)["result"] == "FAIL"
    )


@pytest.mark.parametrize(
    ("expiration", "expected"),
    [
        pytest.param("2026-09-07T12:29:59Z", "FAIL", id="less-than-20-minutes"),
        pytest.param("2026-09-07T12:30:00Z", "PASS", id="exactly-20-minutes-inclusive"),
    ],
)
def test_minimum_remaining_window_boundary(expiration: str, expected: str) -> None:
    activation = "2026-09-07T12:00:00Z"
    policy = conditional_policy(
        MODULE.EXPECTED_PROJECT_ROLE, activation=activation, expiration=expiration
    )
    assert (
        validate(policy, MODULE.EXPECTED_PROJECT_ROLE, activation, expiration)["result"] == expected
    )


QA_PROHIBITED_PERMISSIONS = {
    "artifactregistry.repositories.setIamPolicy",
    "billing.accounts.setIamPolicy",
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
AUTHORITATIVE_PROHIBITED = {
    "project": MODULE.PROJECT_PROHIBITED_PERMISSIONS,
    "billing_account": MODULE.BILLING_PROHIBITED_PERMISSIONS,
}


def test_prohibited_permission_inventory_matches_qa_baseline() -> None:
    implemented = set().union(*AUTHORITATIVE_PROHIBITED.values())
    assert implemented == QA_PROHIBITED_PERMISSIONS


@pytest.mark.parametrize(
    ("scope", "permission"),
    [
        (scope, permission)
        for scope, permissions in AUTHORITATIVE_PROHIBITED.items()
        for permission in sorted(permissions)
    ],
)
def test_each_prohibited_permission_independently_fails_closed(scope: str, permission: str) -> None:
    granted = complete_permissions()
    granted[scope].add(permission)

    report = MODULE.evaluate(granted, AUTHORITATIVE_PROHIBITED)

    assert report["result"] == "FAIL"
    assert report["scopes"][scope]["result"] == "FAIL"
    assert report["scopes"][scope]["prohibited_detected"] == [permission]


def _valid_live_policy(role: str, activation: str, expiration: str) -> dict:
    return conditional_policy(role, activation=activation, expiration=expiration)


def _run_main_with_api_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> tuple[int, dict]:
    execution = dt.datetime.now(dt.UTC)
    activation = (execution - dt.timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    expiration = (execution + dt.timedelta(minutes=55)).isoformat().replace("+00:00", "Z")
    output = tmp_path / "preflight.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--project",
            "fitnessos-nonprod",
            "--billing-account",
            "011C4A-DC4303-9B2787",
            "--state-bucket",
            "fitnessos-nonprod-tfstate-578189272278",
            "--principal",
            PRINCIPAL,
            "--activation-time",
            activation,
            "--expiration-time",
            expiration,
            "--output",
            str(output),
        ],
    )

    secret_marker = "SECRET-TOKEN-OR-RAW-EXCEPTION"

    def get_policy(url: str, _token: str) -> dict:
        if failure == "project-policy-retrieval" and "cloudresourcemanager" in url:
            raise RuntimeError(secret_marker)
        if failure == "billing-policy-retrieval" and "cloudbilling" in url:
            raise RuntimeError(secret_marker)
        if failure == "malformed-project-policy" and "cloudresourcemanager" in url:
            return {"version": 1, "bindings": "invalid"}
        if failure == "malformed-billing-policy" and "cloudbilling" in url:
            return {"version": 1, "bindings": "invalid"}
        role = (
            MODULE.EXPECTED_PROJECT_ROLE
            if "cloudresourcemanager" in url
            else MODULE.EXPECTED_BILLING_ROLE
        )
        return _valid_live_policy(role, activation, expiration)

    def test_permissions(url: str, permissions: set[str], _token: str) -> set[str]:
        if failure == "project-test-permissions" and "cloudresourcemanager" in url:
            raise RuntimeError(secret_marker)
        if failure == "billing-test-permissions" and "cloudbilling" in url:
            raise RuntimeError(secret_marker)
        if failure == "unexpected-api-response":
            raise TypeError(secret_marker)
        return permissions - (
            MODULE.PROJECT_PROHIBITED_PERMISSIONS | MODULE.BILLING_PROHIBITED_PERMISSIONS
        )

    if failure == "access-token":
        monkeypatch.setattr(
            MODULE, "_access_token", lambda: (_ for _ in ()).throw(RuntimeError(secret_marker))
        )
    else:
        monkeypatch.setattr(MODULE, "_access_token", lambda: "RAW-ACCESS-TOKEN")
    monkeypatch.setattr(MODULE, "_get_policy", get_policy)
    monkeypatch.setattr(MODULE, "_post_test_permissions", test_permissions)
    if failure == "state-bucket-test-permissions":
        monkeypatch.setattr(
            MODULE,
            "_bucket_test_permissions",
            lambda *_args: (_ for _ in ()).throw(RuntimeError(secret_marker)),
        )
    else:
        monkeypatch.setattr(
            MODULE,
            "_bucket_test_permissions",
            lambda _bucket, permissions, _token: permissions,
        )

    result = MODULE.main()
    raw_evidence = output.read_text()
    assert secret_marker not in raw_evidence
    assert "RAW-ACCESS-TOKEN" not in raw_evidence
    return result, json.loads(raw_evidence)


@pytest.mark.parametrize(
    "failure",
    [
        "access-token",
        "project-policy-retrieval",
        "billing-policy-retrieval",
        "project-test-permissions",
        "billing-test-permissions",
        "state-bucket-test-permissions",
        "malformed-project-policy",
        "malformed-billing-policy",
        "unexpected-api-response",
    ],
)
def test_api_and_policy_failures_block_terraform_eligibility(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> None:
    exit_code, report = _run_main_with_api_failure(monkeypatch, tmp_path, failure)

    assert exit_code != 0
    assert report["result"] == "FAIL"
    assert "error" in report or "bindings" in report
    assert report.get("terraform_eligible", False) is False

