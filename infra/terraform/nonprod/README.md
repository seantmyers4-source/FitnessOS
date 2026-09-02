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
- The apply workflow runs only from `main`, requires the exact `APPLY-NONPROD` confirmation, uses a protected GitHub environment, and serializes applies.
- Terraform state is versioned and protected by uniform bucket-level access and public-access prevention.

## Workflow model

1. Pull request runs formatting, initialization, validation, and plan.
2. PMO reviews the plan and cost implications.
3. Approved changes merge to `main`.
4. An authorized operator dispatches the apply workflow through the `fitnessos-nonprod` environment.
5. Weekly drift detection fails visibly when Terraform reports changes.

## State recovery

1. Stop all apply workflows.
2. Record the affected state generation and commit SHA.
3. Download the current and prior GCS object generations for evidence.
4. Validate the prior generation against the matching repository commit.
5. Restore only the approved generation.
6. Run `terraform plan -refresh-only`.
7. Resume applies only after PMO records the recovery decision.

Never delete the state bucket or object history as a rollback shortcut.
