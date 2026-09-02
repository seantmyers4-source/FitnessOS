locals {
  labels = {
    application = "fitnessos"
    environment = var.environment
    managed_by  = "terraform"
    program     = "ep-fos-007"
    scope       = "garmin-scope-a"
  }

  mandatory_controls = {
    live_garmin_production_sync = "disabled"
    production_project          = "prohibited"
    production_credentials      = "prohibited"
    material_costs              = "pmo-approval-required"
  }
}
