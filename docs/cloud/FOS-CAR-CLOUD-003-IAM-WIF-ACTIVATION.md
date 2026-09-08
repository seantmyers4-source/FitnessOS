# FOS-CAR-CLOUD-003 — IAM/WIF Activation Package

Status: DRAFT / NON-ACTIVATING / NO CLOUD CHANGE AUTHORIZED

## Release object

This package is a reviewable activation design. Its scripts validate manifests, model
version-3 IAM policy insertion/removal, and sanitize OIDC claims. They do not call a
Google Cloud write API. Opening, synchronizing, approving, or merging the PR cannot
activate IAM.

## Activation inventory

| Object | Exact identity or scope | Activation |
| --- | --- | --- |
| Plan service account | `fitnessos-tf-plan-np@fitnessos-nonprod.iam.gserviceaccount.com` | Separate future authorization |
| Apply service account | `fitnessos-tf-nonprod@fitnessos-nonprod.iam.gserviceaccount.com` | Existing; no change here |
| Plan read role | `projects/fitnessos-nonprod/roles/fitnessosTerraformPlanRead` | Separate future authorization |
| Apply read role | `projects/fitnessos-nonprod/roles/fitnessosTerraformApplyRead` | Separate future authorization |
| Backend role | `projects/fitnessos-nonprod/roles/fitnessosTerraformBackend` | Separate future authorization |
| WIF provider | `projects/578189272278/locations/global/workloadIdentityPools/github-fitnessos/providers/github-actions` | Update only after conflict review |
| State bucket | `fitnessos-nonprod-tfstate-578189272278` | Conditional bindings only |

The authoritative machine-readable inventory is
`config/cloud/iam-wif-activation.json`. Plan and Apply roles have independent role
IDs and independent future bindings; changing one cannot modify the other.

## Permanent permissions

Each Plan and Apply read role contains exactly the 15 permissions approved by
FOS-ADR-CLOUD-014 v1.2. The backend role contains only
`storage.objects.get/list/create/delete`. No predefined Viewer, Editor, Owner,
Billing Viewer, or permanent Billing Costs Manager role is used.

`create/delete` are required only for GCS lock-object lifecycle. State reads require
`get/list`; Apply state persistence uses object creation semantics. No bucket IAM or
unrelated object access is included.

## Exact backend namespace

```text
STATE OBJECT:
fitnessos/nonprod/foundation/default.tfstate

LOCK OBJECT:
fitnessos/nonprod/foundation/default.tfstate.tflock

CANONICAL PREFIX:
projects/_/buckets/fitnessos-nonprod-tfstate-578189272278/objects/fitnessos/nonprod/foundation/

IAM CONDITION:
resource.name.startsWith("projects/_/buckets/fitnessos-nonprod-tfstate-578189272278/objects/fitnessos/nonprod/foundation/")
```

The state object is verified from the current backend inventory. The lock name follows
the GCS backend state-lock naming for this object. Before activation, a read-only
backend trace must reconfirm both names. A mismatch stops activation.

## WIF mapping and trust

The exact mapping is stored in the manifest and uses
`attribute.workflow_ref = assertion.workflow_ref`. It maps `base_ref` separately.
`job_workflow_ref`, reusable-workflow trust, wildcard workflow paths, and
repository-only trust are prohibited.

The five manifest trust rows encode:

1. Plan PR: exact Plan workflow, `pull_request`, PR ref prefix, base `main`.
2. Plan push: exact Plan workflow, `push`, ref `main`.
3. Drift schedule: exact Drift workflow, `schedule`, ref `main`.
4. Drift dispatch: exact Drift workflow, `workflow_dispatch`, ref `main`.
5. Apply: exact Apply workflow, `workflow_dispatch`, ref `main`, protected
   `fitnessos-nonprod` environment.

Every row also requires exact owner and repository. Plan and Apply bindings are
separate. Neither identity may impersonate the other or administer its own binding.

## Sanitized OIDC evidence

`scripts/cloud/oidc_claim_evidence.py` decodes a supplied GitHub OIDC JWT in memory,
retains only repository, owner, workflow, event, ref, base-ref, SHA, run ID, and
attempt, then validates those values against the manifest. It never retains the raw
token, subject, audience, credential response, access token, or refresh token.

Live evidence must be collected from the actual Plan PR, Plan push, Drift schedule,
Drift dispatch, and Apply dispatch workflow contexts. Only the Plan PR context can be
safely exercised from this Draft candidate. Adding instrumentation to the certified
workflows or dispatching Drift/Apply is outside this authorization. Therefore all
five live claim captures remain an explicit pre-activation gate. Missing or different
claims fail closed.

Required artifact naming:

```text
github-oidc-claims-<workflow>-<run-id>-<attempt>
retention: 30 days
contents: sanitized claims JSON and SHA256 checksum only
```

## IAM policy safety and phases

The dry-run implementation requires policy version 3 and an exact current `etag`.
A stale etag, malformed policy, or concurrent update stops processing. Insertion and
removal operate on an exact binding while preserving unrelated bindings. Both are
idempotent. No blind replacement or automatic retry is permitted.

Future execution phases are separate:

1. VALIDATE — manifest, current identities, current policies, state lineage, and claims.
2. DRY RUN — generate exact redacted policy deltas and checksums.
3. ACTIVATE PERMANENT READ BASELINE — separately authorized human operator only.
4. VERIFY — refetch policies and test exact effective permissions.
5. ACTIVATE TEMPORARY RECOVERY — separate PMO authority; maximum 60 minutes.
6. VERIFY — require at least 20 minutes remaining and reject self-extension.
7. REVOKE — manual removal at the earliest terminal condition.
8. VERIFY REVOCATION — prove conditional bindings absent or ineffective.
9. ROLLBACK PERMANENT BASELINE — separate approval, exact introduced bindings only.

Project, service-account, billing, bucket, and provider changes each use their own
current version/etag or equivalent concurrency token. Custom-role updates use the
current role etag. Any conflict stops the package; unrelated bindings are preserved.

## State preservation

Before activation, read-only evidence must confirm bucket identity, no active lock,
serial `2`, lineage `f285f528-7515-e12d-6012-5908c9e041bc`, and exactly:

```text
terraform_data.foundation_guard
google_project_service.required["iam.googleapis.com"]
google_project_service.required["logging.googleapis.com"]
```

Also list unmanaged collision candidates. No import, state removal, edit, replacement,
rollback, destroy, or Apply is part of this package.

## Budget validation

After the Plan identity is activated under separate authority, refresh only
`google_billing_budget.nonprod` using
`resourcemanager.projects.get` and `billing.resourcebudgets.read`. Sanitize the
provider result and fail closed on any error. Do not add billing-account access
silently. If this model fails, document the result and return the proposed
`billing.budgets.get/list` fallback to Architecture and PMO.

## Revocation, rollback, and incident containment

Temporary bindings are manually removed after success, failure, preflight failure,
Terraform failure, unexpected plan, PMO hold, security condition, manual abort, or
60-minute expiry. Post-revocation verification checks exact absence, keyless WIF,
no user-managed keys, and no permanent billing role.

On partial activation, stop all later phases, retain sanitized logs and policy etags,
inventory exact successful and failed changes, revoke temporary access, and open an
incident return. Permanent rollback removes only package-introduced bindings using
fresh policies and etags. No resource or Terraform rollback is implied.

## Evidence and approvals

Retain dry-run reports, sanitized claims, checksums, policy-delta hashes, CI results,
operator identity, timestamps, and post-verification results. Never retain tokens,
credential files, secret values, or raw auth responses.

Checkpoints are: Architecture exact-candidate review; independent QA; PMO merge;
post-merge validation; separate activation authorization; activation QA; separate
recovery-plan authorization; separate Apply decision.

Operator responsibility belongs to the authorized account owner or Cloud Platform
operator named by PMO. No script in this PR may independently cross an approval gate.

## Current restrictions

No IAM, WIF, custom role, service account, state, Terraform plan, Apply, resource,
production, B2, or Garmin connectivity change is performed. B1 remains held and live
Garmin production synchronization remains disabled.
