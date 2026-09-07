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
  for_each           = local.required_services
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "application" {
  project                = var.project_id
  location               = var.region
  repository_id          = "fitnessos-nonprod"
  description            = "Reserved immutable FitnessOS NONPROD application images; B1 attaches no image"
  format                 = "DOCKER"
  labels                 = local.labels
  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "delete-untagged-after-7-days"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s"
    }
  }

  cleanup_policies {
    id     = "retain-ten-recent-versions"
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
  display_name = "FitnessOS NONPROD runtime (reserved)"
  description  = "Keyless identity reserved for B2; B1 grants no runtime permissions"
}

resource "google_service_account" "deployment" {
  project      = var.project_id
  account_id   = "fitnessos-deploy-np"
  display_name = "FitnessOS NONPROD deployment (reserved)"
  description  = "Keyless identity reserved for B2; B1 grants no deployment permissions"
}

resource "google_secret_manager_secret" "app_config" {
  project   = var.project_id
  secret_id = "fitnessos-nonprod-app-config"
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

resource "google_logging_project_bucket_config" "default" {
  project        = var.project_id
  location       = "global"
  bucket_id      = "_Default"
  retention_days = 30

  depends_on = [google_project_service.required]
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

  all_updates_rule {
    disable_default_iam_recipients = false
  }

  depends_on = [google_project_service.required]
}
