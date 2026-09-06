# FitnessOS NONPROD Terraform Foundation

This directory is the controlled Terraform root for EP-FOS-007.

## Authority

- Project: `fitnessos-nonprod`
- Region: `us-west1`
- Environment: NONPROD only
- Certified application SHA: `18e4edfe6f0b8cbfa0c77ad86204c51bacbf5410`
- Terraform state: `gs://fitnessos-nonprod-tfstate-578189272278/fitnessos/nonprod/foundation`

## Tranche B plan-only candidate

The candidate declares required APIs, a regional Docker repository, keyless runtime and deployment identities, two empty secret containers, a private scale-to-zero Cloud Run service, 30-day default-log retention, an instance-cap alert, and a $75 monthly budget with 50/75/90/100-percent alerts.

The all-zero image digest is an intentional plan-only placeholder. It is not deployable and must be replaced by the immutable digest built from the certified application SHA before any Apply authorization. No public invoker IAM binding exists.

Cloud SQL, VPC connectors, NAT, secret values, service-account keys, production resources, and production Garmin connectivity are excluded.

## Safety controls

- Production project creation is prohibited.
- Live Garmin production synchronization remains disabled.
- Production Garmin credentials are prohibited.
- Material recurring-cost resources require PMO approval.
- Cloud Run has zero minimum instances, one maximum instance, 1 vCPU, 512 MiB, CPU only while processing, internal-only ingress, and deletion protection.
- State access uses GitHub OIDC and Workload Identity Federation; no service-account key is allowed.
- Provider selections are committed in `.terraform.lock.hcl`; CI initializes with `-lockfile=readonly`.
- Budget alerts are monitoring controls, not hard spending caps.

## Plan and apply integrity

1. Pull requests generate a saved binary plan, human-readable plan, provider record, metadata record, and SHA-256 checksums.
2. Approved changes merge to `main`.
3. An authorized operator dispatches the apply workflow with the exact `APPLY-NONPROD` confirmation.
4. A dedicated final-plan job creates and uploads the final binary plan artifact.
5. The `fitnessos-nonprod` protected environment pauses the apply job for human approval.
6. Apply downloads the artifact created by the same workflow run.
7. Apply verifies repository SHA, Terraform version, provider lock, project, region, environment, certified application SHA, and plan checksum.
8. Apply executes the exact saved plan and never generates a replacement plan.

Concurrent applies are prohibited. Apply remains outside the Tranche B plan-only authorization.

## Deletion and rollback

Before any future authorized deletion, preserve plan, state generation, logs, and immutable image digest. Disable new revisions, retain evidence, and remove resources only through a separately approved Terraform plan. Cloud Run deletion protection must be removed in a reviewed change before deletion.

For state recovery: stop applies, record the state generation and commit SHA, validate the prior GCS generation against the matching repository commit, restore only the approved generation, and run `terraform plan -refresh-only`. Never delete state history as a rollback shortcut.
