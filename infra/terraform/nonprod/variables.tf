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
