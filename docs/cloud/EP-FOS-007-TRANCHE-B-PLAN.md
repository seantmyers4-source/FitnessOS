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

Estimated monthly minimum: **$0–$1** with no requests, no image beyond negligible metadata, and no secret versions.

Estimated configured maximum: **$25** under the stated operational assumptions: one Cloud Run instance active no more than 100 hours/month, 1 vCPU and 512 MiB, 100,000 requests, 2 GB Artifact Registry storage, 2 GiB log ingestion, 10,000 Secret Manager accesses after separately authorized secret versions, and no internet egress. The estimate deliberately retains contingency below the $75 governance ceiling.

Usage beyond those assumptions must be reviewed. The one-instance cap limits concurrency growth but does not create a monetary hard stop; operators must suspend the service if alerts show unexpected consumption.

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

Cloud Run ingress is internal-only. No `roles/run.invoker` grant to `allUsers` or `allAuthenticatedUsers` exists. Authentication is mandatory. No VPC connector, NAT gateway, public endpoint, custom egress appliance, production credential, or live Garmin route is introduced.

## Secrets

The plan creates only `fitnessos-nonprod-app-config` and `fitnessos-nonprod-database-url` containers. It creates no values or versions. The latter is reserved for a future separately authorized persistence target; Cloud SQL is excluded here.

## Backup, deletion, rollback, and state

Artifact Registry retains ten recent immutable images. Terraform state remains in the existing versioned, access-restricted GCS backend. Serverless definitions contain no database or canonical athlete data, so this tranche creates no database-backup obligation.

Deletion requires a reviewed destroy plan and separate PMO authority. Preserve logs, plan evidence, state generation, and image digest first. Cloud Run deletion protection blocks accidental deletion. Rollback selects a prior immutable image digest through a new reviewed plan; state recovery follows the versioned-backend procedure in the root README.

## Restrictions

The certified application source remains `18e4edfe6f0b8cbfa0c77ad86204c51bacbf5410`. The candidate image digest is deliberately non-deployable until certified artifact construction occurs. Live Garmin synchronization remains disabled. No Apply is authorized.
