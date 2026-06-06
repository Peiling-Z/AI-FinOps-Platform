terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "service_name" {
  type    = string
  default = "ai-finops-platform"
}

resource "google_cloud_run_v2_service" "api" {
  name     = var.service_name
  location = var.region

  template {
    containers {
      image = "gcr.io/${var.project_id}/${var.service_name}:latest"
      ports {
        container_port = 8000
      }
      env {
        name  = "MOCK_LLM"
        value = "true"
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_service_iam_member" "public" {
  location = google_cloud_run_v2_service.api.location
  service  = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "service_url" {
  value = google_cloud_run_v2_service.api.uri
}
