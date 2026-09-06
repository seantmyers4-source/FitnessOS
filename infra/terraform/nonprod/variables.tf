variable "project_id" {
  description = "Authorized FitnessOS NONPROD Google Cloud project."
  type        = string
  default     = "fitnessos-nonprod"

  validation {
    condition     = var.project_id == "fitnessos-nonprod"
    error_message = "Only the authorized fitnessos-nonprod project may be targeted."
  }
}

variable "region" {
  description = "Authorized FitnessOS NONPROD region."
  type        = string
  default     = "us-west1"

  validation {
    condition     = var.region == "us-west1"
    error_message = "EP-FOS-007 currently authorizes only us-west1."
  }
}

variable "environment" {
  description = "Authorized deployment environment."
  type        = string
  default     = "nonprod"

  validation {
    condition     = var.environment == "nonprod"
    error_message = "Production infrastructure is not authorized."
  }
}

variable "certified_application_sha" {
  description = "Immutable Garmin Scope-A application object certified by FOS-QA-CERT-001."
  type        = string
  default     = "18e4edfe6f0b8cbfa0c77ad86204c51bacbf5410"

  validation {
    condition     = var.certified_application_sha == "18e4edfe6f0b8cbfa0c77ad86204c51bacbf5410"
    error_message = "A replacement application SHA requires Engineering, QA, and PMO authorization."
  }
}

variable "billing_account_id" {
  description = "Billing account that owns the approved NONPROD budget."
  type        = string
  default     = "011C4A-DC4303-9B2787"
}

variable "candidate_image" {
  description = "Plan-only immutable placeholder. It must be replaced by the certified build digest before Apply authorization."
  type        = string
  default     = "us-west1-docker.pkg.dev/fitnessos-nonprod/fitnessos-nonprod/athlete-api@sha256:0000000000000000000000000000000000000000000000000000000000000000"

  validation {
    condition     = can(regex("^us-west1-docker\\.pkg\\.dev/fitnessos-nonprod/fitnessos-nonprod/athlete-api@sha256:[0-9a-f]{64}$", var.candidate_image))
    error_message = "The Cloud Run image must use the approved repository and an immutable SHA-256 digest."
  }
}

variable "monthly_budget_usd" {
  description = "PMO governance ceiling; a monitoring threshold, not a hard spending cap."
  type        = number
  default     = 75

  validation {
    condition     = var.monthly_budget_usd > 0 && var.monthly_budget_usd <= 75
    error_message = "The NONPROD monthly budget must not exceed the approved $75 ceiling."
  }
}
