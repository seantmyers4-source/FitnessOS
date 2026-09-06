output "foundation_control" {
  description = "Non-sensitive EP-FOS-007 foundation control record."
  value       = terraform_data.foundation_guard.output
}

output "tranche_b_inventory" {
  description = "Non-sensitive inventory for PMO plan review."
  value = {
    artifact_repository     = google_artifact_registry_repository.application.name
    runtime_service_account = google_service_account.runtime.email
    deploy_service_account  = google_service_account.deployment.email
    cloud_run_service       = google_cloud_run_v2_service.athlete_api.name
    secret_containers       = sort(tolist(local.secret_containers))
    monthly_budget_usd      = var.monthly_budget_usd
    public_access           = false
    min_instances           = 0
    max_instances           = 1
    live_garmin_sync        = false
  }
}
