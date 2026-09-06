resource "terraform_data" "foundation_guard" {
  input = {
    project_id                = var.project_id
    region                    = var.region
    environment               = var.environment
    certified_application_sha = var.certified_application_sha
    live_garmin_sync          = local.mandatory_controls.live_garmin_production_sync
    production_project        = local.mandatory_controls.production_project
    material_costs            = local.mandatory_controls.material_costs
  }

  lifecycle {
    prevent_destroy = true
  }
}
