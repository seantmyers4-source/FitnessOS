# EP-FOS-007 B1 Bounded NONPROD Foundation Evidence

Status: DRAFT / PLAN ONLY — NO APPLY OR MATERIAL PROVISIONING AUTHORIZED

Authority: FOS-PMO-RC-013; architecture decision FOS-ADR-CLOUD-012.
This clean replacement supersedes the combined runtime candidate in PR #12.

## Boundary and resource inventory

| Class | B1 configuration | Boundary control |
|---|---|---|
| APIs | Artifact Registry, Billing Budgets, IAM, Logging, Secret Manager | Each API maps to an actual B1 resource below |
| Artifact Registry | One regional Docker repository | No image is attached; untagged versions deleted after 7 days; retain 10 recent versions |
| Identities | Runtime and deployment service accounts | Keyless and permissionless; operational roles deferred to B2 |
| Secrets | One regional `fitnessos-nonprod-app-config` container | Empty metadata only; no version, value, or accessor |
| Logging | Existing `_Default` bucket set to 30-day retention | Bounded retention; B1 creates no workload log producer |
| Monitoring | Billing budget current-spend thresholds | Default IAM recipient email enabled; no runtime alert |
| State | Existing versioned protected GCS backend | No new state resource; existing recovery controls remain |

The database secret container is deferred because B1 has no database or executable
runtime. Cloud Run, image attachment, runtime invocation, runtime egress, instance
alerting, scheduling, synchronization, and all runtime/deployment permissions are
deferred to B2.

## API requirement mapping

| API | B1 resource or control requiring it |
|---|---|
| `artifactregistry.googleapis.com` | Regional Docker repository and cleanup policies |
| `billingbudgets.googleapis.com` | Project-scoped $75 billing budget and thresholds |
| `iam.googleapis.com` | Two keyless service-account identity resources |
| `logging.googleapis.com` | `_Default` logging bucket retention configuration |
| `secretmanager.googleapis.com` | Empty app-configuration secret metadata container |

`run.googleapis.com` and `monitoring.googleapis.com` are deferred because B1 creates
no Cloud Run workload or runtime monitoring resource.

## IAM and secret posture

B1 declares no `google_project_iam_member`, `google_service_account_iam_member`, or
secret IAM resource. The identities have no Cloud Run developer, Service Account
User, Log Writer, Metric Writer, or Secret Accessor grant. Terraform continues to
authenticate through the existing keyless GitHub Workload Identity Federation
foundation. No service-account key or persistent credential is introduced.

The only secret object is an empty metadata container reserved to stabilize the
name and region before B2. There is no `google_secret_manager_secret_version`.
Garmin credentials and athlete authorization material are absent.

## Cost model

Expected monthly minimum: **$0.00**. API enablement, service accounts, IAM metadata,
budget configuration, and an empty secret container do not create a meaningful
standing workload charge. B1 creates no executable workload and no request path.

Plausible adverse monthly exposure under the B1 configuration: **less than $10**,
leaving **more than $65 reserve** below the $75 governance ceiling. This is an
operationally conservative exposure model, not a claim that the budget is a hard cap.

| Dimension | B1 exposure and control |
|---|---|
| Artifact storage | Starts empty. Seven-day deletion for untagged versions and keep-10 policy bound ordinary accumulation; B1 grants neither identity upload permission. Conservative reserve allows several GB-month of storage. |
| Artifact transfer | No image, consumer, or runtime is declared; expected zero. Privileged out-of-band uploads remain an administrative risk outside the B1 execution path. |
| Logging ingestion | B1 has no workload producer; existing platform/admin audit activity is the only plausible path. Retention is 30 days. |
| Monitoring | No runtime metric or alert policy. Budget evaluation is the sole B1 monitoring control. |
| Secret Manager | One empty regional container; no versions or access operations from a workload. |
| Terraform state | Small metadata growth in the existing versioned bucket; no new backend or always-on process. |

Retained variable-cost paths are privileged out-of-band Artifact Registry uploads,
administrative/audit log volume, and versioned Terraform state history. None is
reachable by the two new permissionless identities. Cloud Platform owns monthly
review and cleanup; PMO owns escalation. The budget sends default role-based email
to Billing Account Administrators and Billing Account Users at 50%, 75%, 90%, and
100%. At 50% Cloud Platform investigates; 75% freezes discretionary activity; 90%
suspends nonessential work under PMO; 100% triggers PMO/billing-admin containment.

## Deletion, rollback, and risks

Any deletion requires a separate reviewed destroy plan and PMO authorization.
Rollback uses a new plan from the prior accepted commit; state recovery uses the
versioned backend procedure. Empty identities, repository metadata, and the empty
secret contain no application or athlete data.

For B1, FOS-RISK-CLOUD-002 is mitigated through runtime removal and
FOS-RISK-CLOUD-003 is avoided through absence of runtime. Both remain open for B2,
owned by FitnessOS Cloud Platform, and must be reviewed before B2 approval or
October 7, 2026, whichever occurs first.

## Mandatory restrictions

Certified application SHA remains
`18e4edfe6f0b8cbfa0c77ad86204c51bacbf5410`. LIVE GARMIN PRODUCTION
SYNCHRONIZATION remains DISABLED. No Apply, material resource, B2 implementation,
production project, production credential, public access, or Scope B activation is
authorized or present.
