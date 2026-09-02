terraform {
  backend "gcs" {
    bucket = "fitnessos-nonprod-tfstate-578189272278"
    prefix = "fitnessos/nonprod/foundation"
  }
}
