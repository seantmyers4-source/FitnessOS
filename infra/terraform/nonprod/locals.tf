locals {
  labels = {
    application = "fitnessos"
    environment = var.environment
    managed_by  = "terraform"
    program     = "ep-fos-007"
    scope       = "garmin-scope-a"
    tranche     = "b"
  }

  mandatory_controls = {
    live_garmin_production_sync = "disabled"
    production_project          = "prohibited"
    production_credentials      = "prohibited"
    material_costs              = "pmo-approval-required"
  }

  required_services = toset([
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
  ])

  secret_containers = toset([
    "fitnessos-nonprod-app-config",
    "fitnessos-nonprod-database-url",
  ])
}
