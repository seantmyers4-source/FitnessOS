# EP-FOS-007 Tranche B Plan, Cost, Security, and Recovery Record

Status: PLAN ONLY — NO APPLY OR MATERIAL PROVISIONING AUTHORIZED

## Inventory and capacity

| Class | Configuration | Cost control |
|---|---|---|
| APIs | Artifact Registry, Billing Budgets, IAM, Logging, Monitoring, Cloud Run, Secret Manager | API activation itself has no recurring charge |
| Artifact Registry | Regional Docker; retain 10 recent images; remove untagged images after 30 days | Assume 2 GB stored and no external transfer |
| Cloud Run | Internal-only; request billing; min 0; max 1; 1 vCPU; 512 MiB; CPU idle | Scale-to-zero and one-instance cap |
| Secrets | Two regional empty containers; runtime access scoped per secret | No secret versions in this tranche |
| Logging | `_Default` bucket, 30-day retention | No raw athlete payloads or debug flood |
| Monitoring | One instance-cap alert policy | No paid synthetic uptime check |
| Budget | $75 monthly; alerts at 50%, 75%, 90%, 100% | Monitoring control, not a hard cap |

## Cost envelope

Estimated monthly minimum: **$0–$1** with no requests, negligible image metadata, no secret versions, and usage within applicable free allowances.

The configuration does **not** establish a finite enforceable monthly maximum. It caps simultaneous Cloud Run instances at one, but does not cap request count, billable active seconds, log volume, Artifact Registry growth from retained tagged images, or outbound data transfer. The former **$25 maximum is withdrawn**; it is retained only as a low-usage operating scenario and must not be used as an Apply control.

### 31-day continuous-runtime model

A 31-day month contains 2,678,400 seconds. At 1 vCPU and 0.5 GiB under request-based billing:

| Component | Without free allowance | With full published allowance available |
|---|---:|---:|
| CPU | 2,678,400 × $0.000024 = $64.28 | (2,678,400 − 180,000) × $0.000024 = $59.96 |
| Memory | 1,339,200 GiB-s × $0.0000025 = $3.35 | (1,339,200 − 360,000) × $0.0000025 = $2.45 |
| Compute subtotal | **$67.63** | **$62.41** |

Free allowances are billing-account aggregates and may already be consumed elsewhere, so $67.63 is the safer compute subtotal. Requests above two million, Artifact Registry beyond its free storage allowance, logs beyond applicable allowances, secret access beyond its free allowance, and outbound transfer are additional.

Because egress and log volume remain uncapped, the enforceable maximum can exceed the **$75** governance ceiling. Apply must remain blocked pending a separately authorized cost/egress control design or a PMO risk-and-ceiling decision. Taxes, paid support, currency conversion, and negotiated discounts are excluded.

## Actual egress posture

Cloud Run has internal-only **ingress**, which does not restrict outbound connections. The candidate has no VPC connector or Direct VPC egress configuration, so outbound internet access is technically possible through Cloud Run's default platform path. No Terraform network control currently blocks Garmin or other external destinations.

Defense in depth currently consists of:

- no production Garmin credentials or athlete identities;
- LIVE_GARMIN_PRODUCTION_SYNCHRONIZATION=disabled;
- certified Scope-A application behavior;
- no scheduled sync, webhook, or backfill resource in the plan;
- a non-deployable image placeholder and an Apply-workflow placeholder guard.

These controls prevent authorized deployment from this candidate, but they are not a network-layer egress deny. Enforcing destination-level outbound denial would require a separately reviewed network architecture, such as controlled VPC egress and firewall/proxy policy, which is excluded from this corrective action. Internet egress therefore creates both usage-cost exposure and a future data-exfiltration/dependency-contact risk.

## Budget routing and response

The budget remains scoped to fitnessos-nonprod, with current-spend thresholds at 50%, 75%, 90%, and 100%. It uses Google Cloud's default role-based email delivery to the Billing Account Administrators and Billing Account Users for the linked billing account. The active FitnessOS billing-account administrator role is the monitored destination; no private email address is committed.

| Threshold | Owner | Required response |
|---:|---|---|
| 50% | Cloud Platform | Review service-level cost attribution and forecast; document anomalies. |
| 75% | Cloud Platform + PMO | Freeze discretionary activity and prepare containment action. |
| 90% | PMO release authority | Suspend nonessential workloads; prohibit further promotion. |
| 100% | PMO + billing administrator | Stop the NONPROD service and recurring-cost resources where operationally safe; investigate before restoration. |

Budget emails can be delayed and are not a hard cap. Programmatic Pub/Sub shutdown automation is not included because it would add resources and operational semantics outside the present authorization.

## IAM

| Identity | Binding | Scope |
|---|---|---|
| `fitnessos-runtime-np` | Logging writer; Monitoring metric writer | Project |
| `fitnessos-runtime-np` | Secret accessor | Each named NONPROD secret only |
| `fitnessos-deploy-np` | Cloud Run developer | Project |
| `fitnessos-deploy-np` | Service Account User | Runtime identity only |
| `fitnessos-tf-nonprod` | Existing GitHub WIF target | Existing foundation; no key added |

No service-account keys or long-lived credentials are declared.

## Exposure and authentication

Cloud Run ingress is internal-only. No roles/run.invoker grant to allUsers or allAuthenticatedUsers exists. Authentication is mandatory. No VPC connector, NAT gateway, public endpoint, custom egress appliance, production credential, or live Garmin route is introduced. Outbound internet remains technically reachable because no network-layer egress restriction is present.

## Secrets

The plan creates only `fitnessos-nonprod-app-config` and `fitnessos-nonprod-database-url` containers. It creates no values or versions. The latter is reserved for a future separately authorized persistence target; Cloud SQL is excluded here.

## Backup, deletion, rollback, and state

Artifact Registry retains ten recent immutable images. Terraform state remains in the existing versioned, access-restricted GCS backend. Serverless definitions contain no database or canonical athlete data, so this tranche creates no database-backup obligation.

Deletion requires a reviewed destroy plan and separate PMO authority. Preserve logs, plan evidence, state generation, and image digest first. Cloud Run deletion protection blocks accidental deletion. Rollback selects a prior immutable image digest through a new reviewed plan; state recovery follows the versioned-backend procedure in the root README.

## Restrictions

The certified application source remains 18e4edfe6f0b8cbfa0c77ad86204c51bacbf5410. The candidate image digest is deliberately non-deployable until certified artifact construction occurs. The Apply workflow fails before final-plan generation when the placeholder is present. Live Garmin synchronization remains disabled. No Apply is authorized.
