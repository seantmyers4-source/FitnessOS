from __future__ import annotations

import base64
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
MANIFEST_PATH = ROOT / "config/cloud/iam-wif-activation.json"


def module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


ACTIVATION = module("scripts/cloud/iam_wif_activation.py", "activation")
OIDC = module("scripts/cloud/oidc_claim_evidence.py", "oidc")
MANIFEST = json.loads(MANIFEST_PATH.read_text())


def token(claims: dict[str, object]) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


def claims(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "repository": "seantmyers4-source/FitnessOS",
        "repository_owner": "seantmyers4-source",
        "workflow_ref": (
            "seantmyers4-source/FitnessOS/.github/workflows/"
            "terraform-nonprod-plan.yml@refs/heads/main"
        ),
        "event_name": "push",
        "ref": "refs/heads/main",
        "sha": "abc",
        "run_id": "1",
        "run_attempt": "1",
        "sub": "not-retained",
        "aud": "not-retained",
    }
    value.update(overrides)
    return value


def test_manifest_passes() -> None:
    ACTIVATION.validate_manifest(MANIFEST)


def test_plan_and_apply_identities_are_distinct() -> None:
    assert MANIFEST["identities"]["plan"] != MANIFEST["identities"]["apply"]


def test_custom_roles_are_distinct_and_exact() -> None:
    plan = MANIFEST["custom_roles"]["plan"]
    apply = MANIFEST["custom_roles"]["apply"]
    assert plan["id"] != apply["id"]
    assert plan["permissions"] == apply["permissions"]
    assert len(plan["permissions"]) == 15


@pytest.mark.parametrize("role", ["plan", "apply"])
def test_missing_or_extra_read_permission_is_rejected(role: str) -> None:
    for mutation in ("missing", "extra"):
        candidate = copy.deepcopy(MANIFEST)
        if mutation == "missing":
            candidate["custom_roles"][role]["permissions"].pop()
        else:
            candidate["custom_roles"][role]["permissions"].append("resourcemanager.projects.setIamPolicy")
        with pytest.raises(ACTIVATION.ActivationError):
            ACTIVATION.validate_manifest(candidate)


def test_backend_condition_and_names_are_exact() -> None:
    backend = MANIFEST["backend"]
    assert backend["state_object"].endswith("/default.tfstate")
    assert backend["lock_object"].endswith("/default.tfstate.tflock")
    assert backend["condition"] == f'resource.name.startsWith("{backend["canonical_prefix"]}")'


@pytest.mark.parametrize("change", ["condition", "canonical_prefix"])
def test_bucket_wide_or_wrong_prefix_is_rejected(change: str) -> None:
    candidate = copy.deepcopy(MANIFEST)
    candidate["backend"][change] = "projects/_/buckets/fitnessos-nonprod-tfstate-578189272278/"
    with pytest.raises(ACTIVATION.ActivationError):
        ACTIVATION.validate_manifest(candidate)


def test_job_workflow_ref_is_rejected() -> None:
    candidate = copy.deepcopy(MANIFEST)
    candidate["wif"]["attribute_mapping"]["attribute.workflow_ref"] = (
        "assertion.job_workflow_ref"
    )
    with pytest.raises(ACTIVATION.ActivationError):
        ACTIVATION.validate_manifest(candidate)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository", "someone/FitnessOS"),
        ("repository_owner", "someone"),
        ("event_name", "schedule"),
        ("ref", "refs/heads/feature"),
    ],
)
def test_wrong_trust_claim_is_rejected(field: str, value: str) -> None:
    assert not OIDC.match_claims(MANIFEST, "plan", claims(**{field: value}))


@pytest.mark.parametrize("base_ref", [None, "refs/heads/develop"])
def test_wrong_or_missing_pr_base_ref_is_rejected(base_ref: str | None) -> None:
    value = claims(
        workflow_ref=(
            "seantmyers4-source/FitnessOS/.github/workflows/"
            "terraform-nonprod-plan.yml@refs/pull/20/merge"
        ),
        event_name="pull_request",
        ref="refs/pull/20/merge",
        base_ref=base_ref,
    )
    assert not OIDC.match_claims(MANIFEST, "plan", value)


def test_cross_identity_impersonation_is_rejected() -> None:
    plan_claims = claims()
    apply_claims = claims(
        workflow_ref=(
            "seantmyers4-source/FitnessOS/.github/workflows/"
            "terraform-nonprod-apply.yml@refs/heads/main"
        ),
        event_name="workflow_dispatch",
    )
    assert not OIDC.match_claims(MANIFEST, "apply", plan_claims)
    assert not OIDC.match_claims(MANIFEST, "plan", apply_claims)


def test_etag_conflict_fails_closed() -> None:
    policy = {"version": 3, "etag": "current", "bindings": []}
    with pytest.raises(ACTIVATION.ActivationError):
        ACTIVATION.insert_binding(policy, {"role": "x", "members": ["y"]}, expected_etag="stale")


def test_unrelated_bindings_are_preserved() -> None:
    existing = {"role": "roles/viewer", "members": ["user:operator@example.invalid"]}
    policy = {"version": 3, "etag": "e", "bindings": [existing]}
    binding = {"role": "roles/custom", "members": ["serviceAccount:example.invalid"]}
    result = ACTIVATION.insert_binding(policy, binding, expected_etag="e")
    assert result["bindings"][0] == existing


def test_activation_and_revocation_are_idempotent() -> None:
    policy = {"version": 3, "etag": "e", "bindings": []}
    binding = {"role": "roles/custom", "members": ["serviceAccount:example.invalid"]}
    once = ACTIVATION.insert_binding(policy, binding, expected_etag="e")
    twice = ACTIVATION.insert_binding(once, binding, expected_etag="e")
    assert once == twice
    removed = ACTIVATION.remove_binding(once, binding, expected_etag="e")
    assert ACTIVATION.remove_binding(removed, binding, expected_etag="e") == removed


@pytest.mark.parametrize(
    ("maximum", "minimum"),
    [(61, 20), (60, 19)],
)
def test_invalid_temporary_window_is_rejected(maximum: int, minimum: int) -> None:
    candidate = copy.deepcopy(MANIFEST)
    candidate["temporary_recovery"]["maximum_minutes"] = maximum
    candidate["temporary_recovery"]["minimum_remaining_minutes"] = minimum
    with pytest.raises(ACTIVATION.ActivationError):
        ACTIVATION.validate_manifest(candidate)


def test_self_extension_is_rejected() -> None:
    candidate = copy.deepcopy(MANIFEST)
    candidate["temporary_recovery"]["self_extension"] = True
    with pytest.raises(ACTIVATION.ActivationError):
        ACTIVATION.validate_manifest(candidate)


def test_raw_tokens_and_sensitive_claims_are_not_evidence() -> None:
    report = OIDC.evidence(MANIFEST, "plan", token(claims()))
    serialized = json.dumps(report)
    assert report["result"] == "PASS"
    assert report["raw_token_retained"] is False
    assert "not-retained" not in serialized
    assert "signature" not in serialized


def test_validation_contains_no_terraform_apply_or_cloud_write() -> None:
    for path in (
        ROOT / "scripts/cloud/iam_wif_activation.py",
        ROOT / "scripts/cloud/oidc_claim_evidence.py",
    ):
        source = path.read_text()
        assert "terraform apply" not in source
        assert "set-iam-policy" not in source
        assert "setIamPolicy" not in source
