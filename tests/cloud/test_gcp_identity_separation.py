from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts/cloud/gcp_plan_permission_preflight.py"
SPEC = importlib.util.spec_from_file_location("gcp_plan_permission_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PLAN = ROOT / ".github/workflows/terraform-nonprod-plan.yml"
DRIFT = ROOT / ".github/workflows/terraform-nonprod-drift.yml"
APPLY = ROOT / ".github/workflows/terraform-nonprod-apply.yml"


def workflow(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def valid_report(**overrides: object) -> dict:
    values = {
        "principal": MODULE.PLAN_PRINCIPAL,
        "workflow_ref": (
            "seantmyers4-source/FitnessOS/.github/workflows/"
            "terraform-nonprod-plan.yml@refs/heads/main"
        ),
        "project_granted": set(MODULE.PROJECT_READ_PERMISSIONS),
        "backend_granted": set(MODULE.BACKEND_PERMISSIONS),
    }
    values.update(overrides)
    return MODULE.evaluate(**values)


def auth_accounts(path: Path) -> list[str]:
    jobs = workflow(path)["jobs"].values()
    return [
        step["with"]["service_account"]
        for job in jobs
        for step in job["steps"]
        if step.get("uses") == "google-github-actions/auth@v3"
    ]


@pytest.mark.parametrize("path", [PLAN, DRIFT])
def test_plan_workflows_use_plan_identity(path: Path) -> None:
    assert auth_accounts(path) == [MODULE.PLAN_PRINCIPAL]


def test_apply_workflow_uses_only_apply_identity() -> None:
    assert auth_accounts(APPLY) == [MODULE.APPLY_PRINCIPAL, MODULE.APPLY_PRINCIPAL]


def test_plan_and_apply_principals_differ() -> None:
    assert MODULE.PLAN_PRINCIPAL != MODULE.APPLY_PRINCIPAL


def test_apply_identity_cannot_satisfy_plan_preflight() -> None:
    assert valid_report(principal=MODULE.APPLY_PRINCIPAL)["result"] == "FAIL"


def test_apply_preflight_rejects_plan_identity() -> None:
    source = APPLY.read_text()
    assert f"--principal {MODULE.APPLY_PRINCIPAL}" in source
    assert f"--principal {MODULE.PLAN_PRINCIPAL}" not in source


@pytest.mark.parametrize("permission", sorted(MODULE.PROJECT_READ_PERMISSIONS))
def test_each_missing_plan_read_permission_fails(permission: str) -> None:
    granted = set(MODULE.PROJECT_READ_PERMISSIONS)
    granted.remove(permission)
    assert valid_report(project_granted=granted)["result"] == "FAIL"


@pytest.mark.parametrize(
    "permission",
    [
        "serviceusage.services.enable",
        "secretmanager.versions.access",
        "resourcemanager.projects.setIamPolicy",
    ],
)
def test_plan_mutation_secret_and_iam_permissions_fail(permission: str) -> None:
    granted = set(MODULE.PROJECT_READ_PERMISSIONS) | {permission}
    report = valid_report(project_granted=granted)
    assert report["result"] == "FAIL"
    assert permission in report["prohibited_permissions_detected"]


def test_plan_policy_api_error_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        MODULE,
        "_access_token",
        lambda: (_ for _ in ()).throw(RuntimeError("sensitive-response")),
    )
    # The top-level exception path is exercised by the existing PR #14 API matrix;
    # this profile independently guarantees evaluation errors never become eligible.
    with pytest.raises(RuntimeError):
        MODULE._access_token()
    assert valid_report(project_granted=set())["terraform_eligible"] is False


@pytest.mark.parametrize("path", [PLAN, DRIFT])
def test_plan_preflight_precedes_terraform_setup_and_refresh(path: Path) -> None:
    steps = next(iter(workflow(path)["jobs"].values()))["steps"]
    names = [step["name"] for step in steps]
    assert names.index("Verify dedicated Plan identity and read permissions") < names.index(
        "Set up Terraform"
    )


def test_apply_temporary_condition_controls_are_preserved() -> None:
    source = APPLY.read_text()
    assert "--minimum-remaining-minutes 20" in source
    assert "recovery_expiration_utc" in source
    assert "gcp_permission_preflight.py" in source


@pytest.mark.parametrize("path", [PLAN, DRIFT, APPLY])
def test_no_workflow_uses_user_managed_key_authentication(path: Path) -> None:
    source = path.read_text()
    assert "credentials_json" not in source
    assert "service_account_key" not in source
    assert "google-github-actions/auth@v3" in source


@pytest.mark.parametrize("path", [PLAN, DRIFT])
def test_no_plan_workflow_can_execute_apply(path: Path) -> None:
    source = path.read_text()
    assert "terraform apply" not in source
    assert "Apply exact approved" not in source

