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

## Billing-account grant

Use temporary predefined role `roles/billing.costsManager` at billing account
`011C4A-DC4303-9B2787`. Required permissions used are
`billing.budgets.create`, `billing.budgets.get`, `billing.budgets.list`,
`billing.budgets.update`, and `billing.budgets.delete`. The role includes broader
cost and budget administration but not Billing Account Administrator authority.
It is removed immediately after recovery convergence or any failed attempt.

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
The maximum window is 60 minutes. Only the separately authorized recovery workflow
may execute during the window. The project/billing owner applies the approved grants;
Cloud Platform records the timestamp and validates them using the permission preflight.

Revocation is triggered immediately by successful convergence, failed recovery,
integrity failure, timeout, or PMO hold. The same owner removes the custom project
role binding and Billing Account Costs Manager binding. A second preflight must then
fail for bootstrap permissions while confirming the permanent read/state baseline.
Failure to revoke opens a security incident and blocks every infrastructure workflow.

## Preventive permission gate

The Apply workflow authenticates as the real WIF principal and calls the project,
billing-account, and Cloud Storage `testIamPermissions` endpoints. It records every
required, granted, and missing permission in a JSON report, hashes the report, and
uploads it for 30 days. Any missing permission or evaluation error fails closed before
Terraform setup or final-plan generation. Because the Apply job depends on the final
plan job, a failed preflight cannot reach protected-environment eligibility.

`testIamPermissions` evaluates only the caller and requested resource at evaluation
time. It cannot prove future availability, rule out deny-policy changes after the
test, or validate business authorization. Exact-plan integrity, protected approval,
concurrency controls, state locking, QA, and PMO authorization remain mandatory.

## Architecture impact recommendation

This proposal preserves the existing WIF principal and creates no key or new trust
relationship. It introduces a temporary project custom role and time-bounded billing
role, so Architecture should review it as an implementation refinement to the B1 IAM
model. No permanent elevated CI privilege is proposed.
