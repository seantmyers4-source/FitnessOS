# FOS-CAR-CLOUD-003 — Exact IAM and Permission-Preflight Specification

Status: DRAFT CORRECTIVE SPECIFICATION — NO IAM CHANGE OR APPLY AUTHORIZED

## Fixed identities and scopes

- Principal: `fitnessos-tf-nonprod@fitnessos-nonprod.iam.gserviceaccount.com`
- Project: `fitnessos-nonprod`
- Billing account: `011C4A-DC4303-9B2787`
- State bucket: `fitnessos-nonprod-tfstate-578189272278`
- Activation: one PMO-approved recovery window, maximum 60 minutes
- Grant/revocation actor: project and billing owner `seantmyers4-source`

## Recommended temporary project custom role

- Role ID: `projects/fitnessos-nonprod/roles/fitnessosB1Recovery`
- Title: `FitnessOS B1 Recovery`
- Stage: `GA`
- Lifecycle owner: FitnessOS Cloud Platform under PMO control
- Versioning: definition committed and reviewed before role creation; any permission
  change requires a new revision and PMO approval

Included permissions:

```text
artifactregistry.locations.get
artifactregistry.locations.list
artifactregistry.repositories.create
artifactregistry.repositories.delete
artifactregistry.repositories.get
artifactregistry.repositories.list
artifactregistry.repositories.update
iam.serviceAccounts.create
iam.serviceAccounts.delete
iam.serviceAccounts.get
iam.serviceAccounts.list
iam.serviceAccounts.update
logging.buckets.get
logging.buckets.update
resourcemanager.projects.get
secretmanager.locations.get
secretmanager.locations.list
secretmanager.secrets.create
secretmanager.secrets.delete
secretmanager.secrets.get
secretmanager.secrets.list
secretmanager.secrets.update
serviceusage.operations.get
serviceusage.services.disable
serviceusage.services.enable
serviceusage.services.get
serviceusage.services.list
serviceusage.services.use
resourcemanager.projects.getIamPolicy
```

Explicit exclusions:

```text
iam.serviceAccountKeys.*
iam.serviceAccounts.actAs
iam.serviceAccounts.getAccessToken
iam.serviceAccounts.setIamPolicy
secretmanager.versions.*
secretmanager.secrets.getIamPolicy
secretmanager.secrets.setIamPolicy
resourcemanager.projects.setIamPolicy
artifactregistry.repositories.setIamPolicy
```

The role is disabled and deleted after the incident is closed and no approved
recovery or destroy procedure depends on it.

The Terraform principal never receives `iam.roles.create`, `iam.roles.update`,
`resourcemanager.projects.setIamPolicy`, or `billing.accounts.setIamPolicy` and
therefore cannot create, bind, renew, or extend its own recovery access.

## Predefined-role evaluation and privilege difference

The following predefined roles were evaluated against the exact B1 recovery
operations. They are not proposed at project scope because each contains unrelated
administrative permissions. The custom role above is the narrower practical choice.

| Role ID | Title / scope | Required permissions used | Material excess and consequence | Disposition |
| --- | --- | --- | --- | --- |
| `roles/serviceusage.serviceUsageAdmin` | Service Usage Admin / project | service enable, disable, get, list, use; operation get | quota and consumer-policy administration extends beyond enabling the five certified B1 APIs | Reject; include only enumerated Service Usage permissions in temporary custom role |
| `roles/iam.serviceAccountAdmin` | Service Account Admin / project | service-account create, delete, get, list, update | service-account IAM-policy administration and administration of unrelated service accounts could enable impersonation paths | Reject; exclude `setIamPolicy`, `actAs`, token, and key permissions |
| `roles/artifactregistry.admin` | Artifact Registry Administrator / project | repository and location create/read/update/delete | package, version, file, attachment, tag, rule, upload, download, and repository IAM administration could alter unrelated artifacts or access policy | Reject; retain repository lifecycle metadata permissions only |
| `roles/secretmanager.admin` | Secret Manager Admin / project | secret-container metadata create/read/update/delete and locations read | secret-version lifecycle and IAM-policy administration could create credential material or delegate secret access | Reject; exclude all `secretmanager.versions.*` and secret IAM permissions |
| `roles/logging.configWriter` | Logs Configuration Writer / project | logging bucket get/update | sink, exclusion, view, metric, link, and broader logging configuration could redirect, suppress, or expose logs | Reject; retain only `_Default` bucket get/update |
| `roles/billing.costsManager` | Costs Manager / billing account | budget create/read/update/delete/list | broader cost visibility, cost export configuration, and budget administration affects the billing account beyond this project | Accept temporarily because budget permissions are billing-account scoped and no practical project custom role can grant them; revoke immediately after recovery |
| `roles/viewer` | Viewer / project | broad read-only planning and refresh | exposes metadata for unrelated project services and does not supply required create/update/delete permissions | Reject as a permanent blanket planning grant; retain only existing service-use consumer access and resource-specific reads in the temporary custom role |
| `roles/storage.objectAdmin` | Storage Object Admin / state bucket only | state/lock object create, delete, get, list, update | compromise could corrupt or delete Terraform state objects in the bucket | Retain permanently at bucket scope; versioning, public-access prevention, WIF, workflow controls, and concurrency mitigate risk |

Any future predefined-role substitution requires a fresh authoritative role
description, a required-versus-excess comparison, Architecture review, and PMO
approval. No role containing service-account key creation, secret payload access,
project IAM administration, or unrelated resource administration is acceptable.

## Billing-account grant

Use temporary predefined role `roles/billing.costsManager` at billing account
`011C4A-DC4303-9B2787`. Required permissions used are
`billing.budgets.create`, `billing.budgets.get`, `billing.budgets.list`,
`billing.budgets.update`, and `billing.budgets.delete`. The role includes broader
cost and budget administration but not Billing Account Administrator authority.
It is removed immediately after recovery convergence or any failed attempt.

## Technically enforced conditional bindings

Google Cloud documents temporary access using conditional allow-policy bindings and
states that date/time attributes are recognized by all Google Cloud services. Cloud
Billing accounts expose versioned IAM allow-policy get/set methods. Therefore the
billing-account binding supports the same `request.time` condition model; no
manual-only fallback is required or permitted.

Both bindings use policy version 3 and the exact structure below. `ACTIVATION_UTC`
and `EXPIRATION_UTC` are RFC 3339 UTC timestamps recorded by the grant implementer.
`EXPIRATION_UTC` must be no later than 60 minutes after `ACTIVATION_UTC`.

```yaml
role: projects/fitnessos-nonprod/roles/fitnessosB1Recovery
members:
  - serviceAccount:fitnessos-tf-nonprod@fitnessos-nonprod.iam.gserviceaccount.com
condition:
  title: fitnessos-b1-recovery-expiration
  description: activation_utc=ACTIVATION_UTC;expiration_utc=EXPIRATION_UTC;maximum_minutes=60
  expression: request.time < timestamp("EXPIRATION_UTC")
```

```yaml
role: roles/billing.costsManager
members:
  - serviceAccount:fitnessos-tf-nonprod@fitnessos-nonprod.iam.gserviceaccount.com
condition:
  title: fitnessos-b1-recovery-expiration
  description: activation_utc=ACTIVATION_UTC;expiration_utc=EXPIRATION_UTC;maximum_minutes=60
  expression: request.time < timestamp("EXPIRATION_UTC")
```

The grant implementer must fetch the current policy with requested version 3, retain
its `etag`, add only the approved conditional binding, and set policy version 3 with
the retained `etag`. An unconditional temporary binding is prohibited. These are
future grant instructions only; this corrective PR creates no binding.

## Certification boundary for PR #14

PR #14 certifies only the read-only, fail-closed permission preflight. It does not
implement or certify an IAM grant, renewal, extension, or revocation mechanism and
contains no IAM-policy write behavior. Actual activation and revocation are a
separate future certification object requiring Architecture, independent QA, and
PMO approval before use.

That future activation package must independently demonstrate version-3 policy
retrieval, preservation of the current `etag`, minimal insertion of exactly one
approved conditional binding, rejection of concurrent-policy overwrite, exact
removal of that binding, and post-revocation verification. A stale or changed
`etag` must fail closed; retry may occur only after retrieving and reviewing the
new policy. Nothing in PR #14 authorizes or supplies this future IAM-write path.

## Exact operation-to-permission matrix

| Resource class | Operation | Exact permission | Scope | Lifecycle |
| --- | --- | --- | --- | --- |
| Project | refresh | `resourcemanager.projects.get` | project | temporary |
| Required APIs | create/refresh/destroy | `serviceusage.services.enable`, `get`, `list`, `use`, `disable`; `serviceusage.operations.get` | project | temporary |
| Service-account identities | create/read/update/destroy | `iam.serviceAccounts.create`, `get`, `list`, `update`, `delete` | project | temporary |
| Artifact Registry repository | create/read/update/destroy | `artifactregistry.locations.get`, `locations.list`, `repositories.create`, `get`, `list`, `update`, `delete` | project | temporary |
| Empty secret container | create/read/update/destroy | `secretmanager.locations.get`, `locations.list`, `secrets.create`, `get`, `list`, `update`, `delete` | project | temporary |
| `_Default` log bucket | read/update | `logging.buckets.get`, `logging.buckets.update` | project | temporary |
| Billing budget | create/read/update/destroy | `billing.budgets.create`, `get`, `list`, `update`, `delete` | billing account | temporary |
| Terraform backend | state and lock lifecycle | `storage.objects.create`, `delete`, `get`, `list`, `update` | state bucket | permanent |
| Service consumption | plan/API consumption | permissions in `roles/serviceusage.serviceUsageConsumer` | project | permanent |

The temporary project binding is granted with a project IAM-policy binding to the
custom role. Creating or updating that role requires `iam.roles.create` and
`iam.roles.update`; those permissions belong to the project owner acting as grant
implementer and are never granted to the Terraform principal.

## Existing permanent residual access

- Project: `roles/serviceusage.serviceUsageConsumer`
- State bucket: `roles/storage.objectAdmin`
- Billing account: no residual role
- User-managed service-account keys: none

The state-bucket role permits object create, delete, get, list, and update. These
permissions are required for backend state and lock lifecycle but could corrupt or
delete state if the CI identity were compromised. Bucket versioning, workflow
protection, concurrency control, and keyless WIF reduce but do not eliminate that
risk.

## Temporary activation and revocation

The earliest grant is after Architecture and PMO approve this exact specification.
The maximum window is 60 minutes and is enforced by each binding's absolute
`request.time` condition. A separate timer/alarm and manual revocation remain mandatory
defense in depth. The PMO grant approver authorizes the window. Project and billing
owner `seantmyers4-source` implements both bindings. Only the separately authorized
recovery workflow may execute during the window; unrelated infrastructure workflows
remain prohibited. Cloud Platform records the activation and expiration timestamps
and validates the live bindings using the permission preflight.

Revocation is triggered immediately by successful convergence, failed recovery,
integrity failure, timeout, or PMO hold. The same owner removes the custom project
role binding and Billing Account Costs Manager binding. A second preflight must then
fail for bootstrap permissions while confirming the permanent read/state baseline.
Failure to revoke opens a security incident and blocks every infrastructure workflow.
Revocation is required at the earliest of successful convergence, failed recovery,
preflight failure, Terraform failure, unexpected plan change, PMO hold, security
condition, manual abort, or the 60-minute maximum.

Post-revocation verification fetches both version-3 policies and confirms the custom
role binding and Costs Manager binding are absent or ineffective. It then confirms no
permanent billing role, keyless WIF authentication, and zero user-managed service-
account keys. The permission preflight must fail for the removed recovery permissions
while the permanent Service Usage Consumer and bucket state access remain effective.

## Preventive permission gate

The Apply workflow authenticates as the real WIF principal, fetches the project and
billing IAM policies at version 3, and calls the project, billing-account, and Cloud
Storage `testIamPermissions` endpoints. It records the principal, scopes, live role
bindings, exact condition expressions, activation and expiration timestamps, execution
timestamp, remaining duration, required and missing permissions, prohibited permissions,
and evaluation errors. It hashes the JSON report and retains it for 30 days.

The gate fails before Terraform setup or final-plan generation for an absent,
duplicate, unconditional, expired, over-60-minute, malformed, not-yet-active, mismatched,
or insufficient-remaining-window binding; missing required permissions; detected
prohibited permissions; or any policy/permission evaluation error. Because the Apply
job depends on the final-plan job, a failed preflight cannot reach protected-environment
eligibility. The governed minimum remaining duration is 20 minutes.

`testIamPermissions` evaluates only the caller and requested resource at evaluation
time. It cannot prove future availability, rule out deny-policy changes after the
test, or validate business authorization. Exact-plan integrity, protected approval,
concurrency controls, state locking, QA, and PMO authorization remain mandatory.

## Architecture impact recommendation

This proposal preserves the existing WIF principal and creates no key or new trust
relationship. It introduces a temporary project custom role and time-bounded billing
role, so Architecture should review it as an implementation refinement to the B1 IAM
model. No permanent elevated CI privilege is proposed.

## Authoritative references

- Google Cloud IAM predefined roles and permission index:
  <https://cloud.google.com/iam/docs/roles-permissions>
- Service Usage IAM roles and permissions:
  <https://cloud.google.com/iam/docs/roles-permissions/serviceusage>
- Service account creation permission requirements:
  <https://cloud.google.com/iam/docs/service-accounts-create>
- Artifact Registry roles and permissions:
  <https://cloud.google.com/iam/docs/roles-permissions/artifactregistry>
- Secret Manager access control:
  <https://cloud.google.com/secret-manager/docs/access-control>
- Cloud Logging access control:
  <https://cloud.google.com/logging/docs/access-control>
- Cloud Billing access control and predefined roles:
  <https://cloud.google.com/billing/docs/how-to/billing-access>
- Cloud Storage IAM permissions and roles:
  <https://cloud.google.com/storage/docs/access-control/iam-roles>
- Resource Manager `projects.testIamPermissions`:
  <https://cloud.google.com/resource-manager/reference/rest/v1/projects/testIamPermissions>
- Cloud Billing `billingAccounts.testIamPermissions`:
  <https://cloud.google.com/billing/docs/reference/rest/v1/billingAccounts/testIamPermissions>
- Cloud Billing `billingAccounts.getIamPolicy` and `setIamPolicy`:
  <https://cloud.google.com/billing/docs/reference/rest/v1/billingAccounts/getIamPolicy>
  and <https://cloud.google.com/billing/docs/reference/rest/v1/billingAccounts/setIamPolicy>
- Cloud Storage `buckets.testIamPermissions`:
  <https://cloud.google.com/storage/docs/json_api/v1/buckets/testIamPermissions>

