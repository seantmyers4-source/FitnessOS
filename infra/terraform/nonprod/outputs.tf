output "foundation_control" {
  description = "Non-sensitive EP-FOS-007 foundation control record."
  value       = terraform_data.foundation_guard.output
}

output "b1_identity_emails" {
  description = "Reserved keyless identities; B1 grants them no operational roles."
  value = {
    runtime    = google_service_account.runtime.email
    deployment = google_service_account.deployment.email
  }
}

output "b1_empty_secret_container" {
  description = "Empty metadata container; no secret version or accessor binding is created."
  value       = google_secret_manager_secret.app_config.secret_id
}
