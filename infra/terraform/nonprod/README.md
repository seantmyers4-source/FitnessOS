# FitnessOS NONPROD Terraform Foundation

This directory is the controlled Terraform root for EP-FOS-007.

## Authority

- Project: `fitnessos-nonprod`
- Region: `us-west1`
- Environment: NONPROD only
- Certified application SHA: `18e4edfe6f0b8cbfa0c77ad86204c51bacbf5410`
- Terraform state: `gs://fitnessos-nonprod-tfstate-578189272278/fitnessos/nonprod/foundation`

## Safety controls

- Production project creation is prohibited.
- Live Garmin production synchronization remains disabled.
- Production Garmin credentials are prohibited.
- Material recurring-cost resources require PMO approval.
- State access uses GitHub OIDC and Workload Identity Federation; no service-account key is allowed.
- Provider selections are committed in `.terraform.lock.hcl`; CI initializes with `-lockfile=readonly`.
- Terraform state is versioned and protected by uniform bucket-level access and public-access prevention.

## Plan and apply integrity

1. Pull requests generate a saved binary plan, human-readable plan, provider record, metadata record, and SHA-256 checksums.
2. Approved changes merge to `main`.
3. An authorized operator dispatches the apply workflow with the exact `APPLY-NONPROD` confirmation.
4. A dedicated final-plan job creates and uploads the final binary plan artifact.
5. The `fitnessos-nonprod` protected environment pauses the apply job for human approval.
6. Apply downloads the artifact created by the same workflow run.
7. Apply verifies repository SHA, Terraform version, provider lock, project, region, environment, certified application SHA, and plan checksum.
8. Apply executes the exact saved plan and never generates a replacement plan.

Concurrent applies are prohibited.

## State recovery

1. Stop all apply workflows.
2. Record the affected state generation and commit SHA.
3. Download the current and prior GCS object generations for evidence.
4. Validate the prior generation against the matching repository commit.
5. Restore only the approved generation.
6. Run `terraform plan -refresh-only`.
7. Resume applies only after PMO records the recovery decision.

Never delete the state bucket or object history as a rollback shortcut.
