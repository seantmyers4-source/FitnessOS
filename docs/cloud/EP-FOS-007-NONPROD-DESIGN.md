# EP-FOS-007 — FitnessOS NONPROD Runtime Foundation Design

Status: DESIGN / COST GATE — NO MATERIAL RUNTIME PROVISIONING AUTHORIZED

## 1. Deployment topology

The proposed managed topology is:

- Artifact Registry (Docker, regional `us-west1`) for immutable images.
- Cloud Run with request-based billing, zero minimum instances, one maximum instance initially, CPU only during requests, and ingress restricted to the approved verification path.
- Cloud SQL for PostgreSQL in `us-west1`, private connectivity preferred, smallest appropriate shared-core NONPROD tier, zonal availability, automated backups, and deletion protection.
- Secret Manager for NONPROD-only configuration. No production Garmin secret may exist.
- Dedicated runtime and migration service accounts.
- Cloud Logging, Monitoring, uptime checks, alert policies, and budget notifications.
- Existing protected GCS backend for Terraform state.

## 2. Scope-B isolation

Mandatory controls:

- no production Garmin credentials;
- no production athlete identities;
- no live Garmin webhooks;
- no scheduled live synchronization;
- no production historical backfill;
- outbound Garmin production access denied where practical;
- synthetic fixtures only;
- `FITNESSOS_ENVIRONMENT=nonprod`;
- `FITNESSOS_RELEASE_SCOPE=garmin-scope-a`;
- `FITNESSOS_SOURCE_SHA=18e4edfe6f0b8cbfa0c77ad86204c51bacbf5410`.

## 3. Proposed resource inventory

| Resource | Initial configuration | Cost posture |
|---|---|---|
| Artifact Registry | Regional Docker repository; lifecycle cleanup | Usually under $2/month at small volume |
| Cloud Run | Request billing; min 0; max 1; 1 vCPU; 512 MiB | Often $0–$5/month for light verification |
| Cloud SQL PostgreSQL | Smallest suitable shared-core NONPROD tier; zonal; 10 GB SSD | Primary cost driver; planning allowance $20–$45/month |
| Cloud SQL backups | 7 daily backups; PITR initially disabled unless required | Planning allowance $2–$10/month |
| Secret Manager | Small number of NONPROD secrets | Typically under $1/month |
| Logging/Monitoring | Short retention; no raw payload logging | $0–$5/month at low volume |
| Networking | Private access/connectivity and limited egress | $0–$10/month depending on connector choice |
| Terraform state | Existing small versioned GCS bucket | Typically under $1/month |

Estimated initial envelope: **$25–$75/month**. This is a planning range, not a quote. PMO approval and a current Google Cloud Pricing Calculator estimate are required before material provisioning.

## 4. Cost controls

- Billing budget thresholds at 50%, 75%, 90%, and 100% of a PMO-approved monthly budget.
- Email/Pub/Sub notification path before material deployment.
- Cloud Run minimum instances fixed at zero and maximum instances fixed at one initially.
- Cloud SQL uses no high availability, read replica, or production capacity in this phase.
- Artifact cleanup removes untagged images after 30 days while preserving certified digests.
- Log exclusions prevent raw payloads and excessive low-value telemetry.
- Weekly cost review during the deployment-validation phase.
- Shutdown order: disable jobs, set Cloud Run traffic to zero/delete service, export required evidence, snapshot or export database, then remove recurring-cost resources through Terraform.

## 5. IAM and service identities

| Identity | Purpose | Proposed permissions |
|---|---|---|
| `fitnessos-tf-nonprod` | Terraform plan/apply | State object admin plus narrowly scoped resource administration approved per module |
| `fitnessos-runtime-nonprod` | Cloud Run runtime | Secret accessor for named NONPROD secrets, Cloud SQL client, telemetry writer |
| `fitnessos-migrate-nonprod` | Controlled Alembic migrations | Cloud SQL client and database migration credential access |
| GitHub OIDC principal | Keyless CI entry | Workload Identity User on Terraform service account only |
| Account owner | Break-glass administration | Existing owner role; not used by CI |

No service-account JSON key is permitted.

## 6. Required APIs before runtime provisioning

Proposed additions, subject to the cost gate:

- `artifactregistry.googleapis.com`
- `run.googleapis.com`
- `sqladmin.googleapis.com`
- `secretmanager.googleapis.com`
- `compute.googleapis.com`
- `servicenetworking.googleapis.com`
- `logging.googleapis.com`
- `monitoring.googleapis.com`
- `cloudbuild.googleapis.com` only if the approved build design requires it
- `billingbudgets.googleapis.com`

## 7. Immutable build and deployment provenance

The application image must be built from a clean checkout of the certified SHA, not from the infrastructure head. Required recorded evidence:

- repository and certified source SHA;
- build workflow/run ID;
- Python and dependency resolution;
- image name and immutable digest;
- Artifact Registry location;
- deployment revision;
- configuration version;
- database revision before and after;
- synthetic verification results;
- rollback result.

Mutable tags may assist operators but cannot serve as release identity.

## 8. Database and rollback controls

- Capture Alembic revision before migration.
- Run only migrations present at the certified SHA.
- Capture revision after migration.
- Preserve pre-migration backup/export evidence.
- Roll back the Cloud Run revision independently of database state.
- Downgrade the database only where the migration contract explicitly supports it; otherwise restore from the approved recovery point.
- Never delete evidence or state history to complete rollback.

## 9. Risks and dependencies

- FOS-RISK-002: Cloud SQL is the primary recurring-cost driver.
- FOS-RISK-003: Private Cloud SQL connectivity may add networking complexity or connector cost.
- FOS-RISK-004: Terraform CI needs additional resource-specific roles before runtime planning.
- FOS-RISK-005: GitHub environment protection must be configured before any material apply.
- AG-ENG-005 remains open but is not currently a cloud-foundation blocker.

## 10. Recommended next PMO gate

Approve the design and a monthly NONPROD budget ceiling before enabling runtime APIs or provisioning Artifact Registry, Cloud Run, Cloud SQL, Secret Manager, networking, or monitoring resources.
