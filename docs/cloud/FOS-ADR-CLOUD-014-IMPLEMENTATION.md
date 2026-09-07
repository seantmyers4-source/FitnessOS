# FOS-ADR-CLOUD-014 — Plan/Apply Identity Separation Implementation

Status: DRAFT IMPLEMENTATION — NO IAM CHANGE OR APPLY AUTHORIZED

## Identity decision

| Function | Service account | Permanent posture |
| --- | --- | --- |
| Plan | `fitnessos-tf-plan-np@fitnessos-nonprod.iam.gserviceaccount.com` | Read/refresh plus state-lock lifecycle only |
| Apply | `fitnessos-tf-nonprod@fitnessos-nonprod.iam.gserviceaccount.com` | Read/refresh plus state-lock lifecycle; mutation only through separately authorized conditional bindings |

The existing `fitnessos-tf-nonprod` identity becomes the dedicated Apply identity.
It is not retired, so the current backend, evidence, and recovery lineage remain intact.
The Plan identity is new but is only proposed by this PR; it is not created or bound.
Neither identity may impersonate the other or administer its own IAM policy.

## Keyless WIF trust design

The existing pool and provider remain unchanged during this assignment. A future
activation package proposes extending the provider mapping with:

```text
google.subject              = assertion.sub
attribute.repository        = assertion.repository
attribute.repository_owner  = assertion.repository_owner
attribute.ref               = assertion.ref
attribute.base_ref          = assertion.base_ref
attribute.event_name        = assertion.event_name
attribute.workflow_ref      = assertion.workflow_ref
```

Provider condition:

```text
assertion.repository_owner == "seantmyers4-source" &&
assertion.repository == "seantmyers4-source/FitnessOS"
```

Service-account impersonation bindings are separate and conditional:

| Target | PrincipalSet | Required binding condition |
| --- | --- | --- |
| Plan | repository attribute for `seantmyers4-source/FitnessOS` | Direct workflow is exactly Plan or Drift; event and branch claims must match the matrix below |
| Apply | repository attribute for `seantmyers4-source/FitnessOS` | Direct workflow is exactly `terraform-nonprod-apply.yml`; event is `workflow_dispatch`; ref is `refs/heads/main` |

The Apply workflow additionally depends on the protected `fitnessos-nonprod`
environment before the Apply job. Repository membership alone is insufficient.
No wildcard workflow trust, service-account key, cross-impersonation binding, or
Plan-to-Apply elevation is permitted.

### Event, ref, and base-ref trust matrix

These are direct workflows. `assertion.workflow_ref` identifies the workflow that
GitHub is executing. `assertion.job_workflow_ref` is not mapped or accepted; it is
reserved for a separately reviewed reusable-workflow design.

All rows require the exact repository owner `seantmyers4-source`, exact repository
`seantmyers4-source/FitnessOS`, and the exact workflow path shown. An exact path
prefix ending in `.yml@` permits Git refs to follow the path but does not permit a
different workflow file.

| Identity | Direct workflow | Event | Required ref | Required base_ref |
| --- | --- | --- | --- | --- |
| Plan | `terraform-nonprod-plan.yml` | `pull_request` | GitHub-generated PR merge ref | `refs/heads/main` |
| Plan | `terraform-nonprod-plan.yml` | `push` | `refs/heads/main` | not used |
| Plan | `terraform-nonprod-drift.yml` | `schedule` | `refs/heads/main` | not used |
| Plan | `terraform-nonprod-drift.yml` | `workflow_dispatch` | `refs/heads/main` | not used |
| Apply | `terraform-nonprod-apply.yml` | `workflow_dispatch` | `refs/heads/main` | not used |

The Plan service-account binding is the logical OR of these four Plan rows. The
Apply service-account binding contains only the Apply row. In particular:

```text
pull_request => assertion.base_ref == "refs/heads/main"
push | schedule | workflow_dispatch => assertion.ref == "refs/heads/main"
direct workflow identity => assertion.workflow_ref
reusable workflow identity => not authorized; assertion.job_workflow_ref is not mapped
```

A PR's `assertion.ref` is its GitHub-generated pull-request ref and is never used
as evidence that the PR targets `main`. Missing or non-main `base_ref` rejects
PR authentication. Plan and Drift paths cannot satisfy the Apply binding, and the
Apply path cannot satisfy the Plan binding.

## Permanent Plan permission matrix

The proposed project custom role is
`projects/fitnessos-nonprod/roles/fitnessosTerraformPlanRead`. It contains only:

| Permission | Resource | Operation / necessity | Excess authority and risk | Validation |
| --- | --- | --- | --- | --- |
| `resourcemanager.projects.get` | project | Provider project refresh and single-project budget association | Reveals project metadata | remove-one regression and live `testIamPermissions` |
| `serviceusage.services.get`, `serviceusage.services.list` | project | Refresh five `google_project_service` objects | Reveals enabled-service inventory | remove-one regression and live test |
| `iam.serviceAccounts.get`, `iam.serviceAccounts.list` | project | Refresh two service-account metadata objects | Reveals service-account metadata; no token/key/IAM authority | remove-one regression and live test |
| `artifactregistry.locations.get`, `artifactregistry.locations.list`, `artifactregistry.repositories.get`, `artifactregistry.repositories.list` | project/repository | Refresh repository and resolve supported location | Reveals repository metadata; no artifact read/write | remove-one regression and live test |
| `secretmanager.locations.get`, `secretmanager.locations.list`, `secretmanager.secrets.get`, `secretmanager.secrets.list` | project/secret | Refresh empty secret-container metadata | Reveals container metadata; no payload/version access | remove-one regression and live test |
| `logging.buckets.get` | project `_Default` bucket | Refresh retention configuration | Reveals bucket configuration; no log-entry read | remove-one regression and live test |
| `billing.resourcebudgets.read` | project | Preferred single-project budget refresh path | Reveals only project-scoped budget metadata | remove-one regression; live validation deferred until budget exists |

No predefined project role is selected because Viewer and service-specific viewer
roles contain unrelated reads. A custom role is viable and minimizes excess.

## Permanent Apply read baseline

The Apply identity uses a separate custom role,
`projects/fitnessos-nonprod/roles/fitnessosTerraformApplyRead`, with the same B1
provider-refresh reads above. Its separate definition prevents changes to the Plan
profile from silently changing Apply authority. It receives no permanent create,
update, delete, IAM-policy, secret-payload, publication, or service-account token/key
permission. Temporary mutation remains the conditional roles specified by
FOS-ADR-CLOUD-013 v1.2 and expires within 60 minutes.

## GCS backend analysis

Both identities require the following at bucket scope for ordinary Terraform plan,
refresh, locking, and saved-plan generation:

```text
storage.objects.get
storage.objects.list
storage.objects.create
storage.objects.delete
```

`get/list` read state and discover objects. `create/delete` are required to acquire
and release the backend lock object. Object creation also permits writing an object,
so even the Plan identity retains bounded backend mutation risk. Ordinary `plan`
does not intentionally persist refreshed infrastructure state, but lock-object writes
still occur. Apply needs the same four permissions to lock and persist the resulting
state object. `storage.objects.update` is not required by the GCS object lifecycle and
is excluded from the proposed narrow custom role.

Replacing `roles/storage.objectAdmin` with a custom bucket role is technically viable.
The future binding should use an IAM condition restricting `resource.name` to the
`fitnessos/nonprod/foundation/` object prefix, including its lock object. Exact object
names must be confirmed from a read-only backend trace before activation. Removing
create/delete breaks state locking; removing get/list breaks initialization or state
refresh. No backend permission changes occur in this PR.

## Billing-budget read determination

Google Cloud documents two valid read paths for a single-project budget:

1. project-scoped `resourcemanager.projects.get` plus
   `billing.resourcebudgets.read`; or
2. billing-account-scoped `billing.budgets.get` and `billing.budgets.list`.

The architecture selects option 1 because it avoids permanent billing-account access.
The Google provider identifies `google_billing_budget` by billing-account/budget name,
but the Cloud Billing API authorizes Get/List for a single-project budget through the
project-scoped alternative. This is documented capability, not yet live provider proof:
the B1 budget does not exist and no test resource may be created. Live provider refresh
validation is therefore deferred until controlled B1 provisioning. If provider refresh
does not honor the project-scoped path, stop; evaluate a billing-account custom role
containing only `billing.budgets.get/list`. Permanent `roles/billing.viewer` and
`roles/billing.costsManager` remain prohibited.

## Workflow mapping

| Workflow | Identity | Preflight | Mutation |
| --- | --- | --- | --- |
| Pull-request and main validation | Plan | Plan profile before Terraform setup | None |
| Scheduled drift detection | Plan | Plan profile before Terraform setup | None |
| Post-Apply convergence | Plan | Plan profile before Terraform setup | None |
| Protected Apply/recovery | Apply | Apply profile with exact temporary conditions | Temporary, conditional, separately authorized |
| Destroy/rollback | Apply | Separate future authorization | Not authorized here |

## Bootstrap and activation procedure

The authorized human bootstrap actor creates the Plan identity and both custom read
roles, retrieves each current IAM policy at version 3, preserves its `etag`, inserts
only the reviewed WIF and role bindings, and writes the policy with the same `etag`.
A conflict or changed policy stops the procedure; it is never blindly retried.
Unrelated bindings are byte-for-byte preserved. Verification confirms exact identities,
conditions, permissions, keyless authentication, and absence of cross-impersonation.

Rollback removes only bindings introduced by the approved change using the latest
policy and its current `etag`, then verifies both identities are unable to authenticate.
The Apply temporary-binding activation/revocation package remains separate: it must
prove minimal conditional insertion, conflict rejection, exact removal, and
post-revocation verification before PMO may authorize it.

## Restrictions and evidence status

This PR changes repository controls only. It creates no identity, role, IAM binding,
WIF mapping, Terraform state, plan, or cloud resource. B1 remains held; B2 and live
Garmin synchronization remain disabled.

## Authoritative references

- Google Cloud Billing Budget API access control:
  <https://cloud.google.com/billing/docs/how-to/budget-api-access-control>
- Terraform GCS backend:
  <https://developer.hashicorp.com/terraform/language/backend/gcs>
- GitHub OIDC claims for reusable and referenced workflows:
  <https://docs.github.com/actions/reference/security/oidc>
- Workload Identity Federation deployment pipelines:
  <https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines>

