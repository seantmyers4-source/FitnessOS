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

resource "google_project_service" "required" {
  for_each = local.required_services

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "application" {
  project       = var.project_id
  location      = var.region
  repository_id = "fitnessos-nonprod"
  description   = "Immutable FitnessOS NONPROD application images"
  format        = "DOCKER"
  labels        = local.labels

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "delete-untagged-after-30-days"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "2592000s"
    }
  }

  cleanup_policies {
    id     = "retain-recent-images"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = "fitnessos-runtime-np"
  display_name = "FitnessOS NONPROD runtime"
  description  = "Keyless Cloud Run runtime identity for Garmin Scope A"
}

resource "google_service_account" "deployment" {
  project      = var.project_id
  account_id   = "fitnessos-deploy-np"
  display_name = "FitnessOS NONPROD deployment"
  description  = "Keyless deployment identity; no service-account keys permitted"
}

resource "google_project_iam_member" "runtime_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "deployment_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deployment.email}"
}

resource "google_service_account_iam_member" "deployment_acts_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployment.email}"
}

resource "google_secret_manager_secret" "containers" {
  for_each = local.secret_containers

  project   = var.project_id
  secret_id = each.value
  labels    = local.labels

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_iam_member" "runtime_access" {
  for_each = google_secret_manager_secret.containers

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_cloud_run_v2_service" "athlete_api" {
  project             = var.project_id
  name                = "fitnessos-athlete-api-nonprod"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = true
  labels              = local.labels

  template {
    service_account = google_service_account.runtime.email
    labels          = local.labels

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = var.candidate_image

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      env {
        name  = "FITNESSOS_ENVIRONMENT"
        value = "nonprod"
      }
      env {
        name  = "FITNESSOS_RELEASE_SCOPE"
        value = "garmin-scope-a"
      }
      env {
        name  = "FITNESSOS_SOURCE_SHA"
        value = var.certified_application_sha
      }
      env {
        name  = "LIVE_GARMIN_PRODUCTION_SYNCHRONIZATION"
        value = "disabled"
      }

      ports {
        container_port = 8080
      }

      startup_probe {
        initial_delay_seconds = 1
        timeout_seconds       = 2
        period_seconds        = 5
        failure_threshold     = 12
        http_get {
          path = "/health/live"
        }
      }

      liveness_probe {
        initial_delay_seconds = 5
        timeout_seconds       = 2
        period_seconds        = 10
        failure_threshold     = 3
        http_get {
          path = "/health/live"
        }
      }
    }
  }

  depends_on = [
    google_artifact_registry_repository.application,
    google_project_service.required,
  ]
}

resource "google_logging_project_bucket_config" "default" {
  project        = var.project_id
  location       = "global"
  bucket_id      = "_Default"
  retention_days = 30
}

resource "google_monitoring_alert_policy" "unexpected_instance_count" {
  project      = var.project_id
  display_name = "FitnessOS NONPROD Cloud Run instance cap violation"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Cloud Run instance count exceeds one"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/container/instance_count\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "Investigate immediately. NONPROD is capped at one instance and live Garmin synchronization must remain disabled."
    mime_type = "text/markdown"
  }

  user_labels = local.labels
  depends_on  = [google_project_service.required]
}

resource "google_billing_budget" "nonprod" {
  billing_account = var.billing_account_id
  display_name    = "FitnessOS NONPROD monthly governance ceiling"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_usd)
    }
  }

  dynamic "threshold_rules" {
    for_each = toset([0.50, 0.75, 0.90, 1.00])
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "CURRENT_SPEND"
    }
  }

  depends_on = [google_project_service.required]
}
