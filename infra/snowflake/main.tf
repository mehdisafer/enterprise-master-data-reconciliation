terraform {
  required_version = ">= 1.6.0, < 2.0.0"
  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "2.22.1"
    }
  }
}

# Credentials are external provider environment/config, never Terraform values.
# SNOWFLAKE_ORGANIZATION_NAME, SNOWFLAKE_ACCOUNT_NAME, SNOWFLAKE_USER,
# SNOWFLAKE_PRIVATE_KEY (PEM), SNOWFLAKE_ROLE are required for the approved deployer.
# Resource-monitor assignment requires an administrator authorized for this task.
provider "snowflake" {
  authenticator   = "SNOWFLAKE_JWT"
  login_timeout  = 15
  request_timeout = 30
}

resource "snowflake_resource_monitor" "mdm" {
  name                      = "${var.prefix}_MONITOR"
  credit_quota              = var.total_credit_quota
  frequency                 = "NEVER"
  start_timestamp           = "IMMEDIATELY"
  suspend_trigger           = 90
  suspend_immediate_trigger = 100

  lifecycle {
    precondition {
      condition     = var.environment_authorized
      error_message = "An authorized dedicated Snowflake environment and explicit credit quota are required before apply."
    }
  }
}

resource "snowflake_warehouse" "mdm" {
  name                                = "${var.prefix}_XS"
  warehouse_type                      = "STANDARD"
  warehouse_size                      = "XSMALL"
  min_cluster_count                   = 1
  max_cluster_count                   = 1
  auto_suspend                        = 60
  auto_resume                         = "true"
  initially_suspended                 = true
  enable_query_acceleration           = "false"
  max_concurrency_level               = 2
  statement_timeout_in_seconds        = 120
  statement_queued_timeout_in_seconds = 30
  resource_monitor                    = snowflake_resource_monitor.mdm.fully_qualified_name
  comment                             = "Dedicated enterprise MDM qualification warehouse; bounded synthetic workload."
}

resource "snowflake_database" "mdm" {
  name                        = var.prefix
  is_transient                = false
  data_retention_time_in_days  = 1
  comment                     = "Synthetic enterprise MDM integration data."
  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = var.environment_authorized
      error_message = "Set environment_authorized only after the account, scope and budget are approved."
    }
  }
}

resource "snowflake_schema" "raw" {
  database                    = snowflake_database.mdm.name
  name                        = "MDM_RAW"
  with_managed_access         = "true"
  is_transient                = "false"
  data_retention_time_in_days  = 1
  lifecycle {
    prevent_destroy = true
  }
}

resource "snowflake_schema" "analytics" {
  database                    = snowflake_database.mdm.name
  name                        = "ANALYTICS"
  with_managed_access         = "true"
  is_transient                = "false"
  data_retention_time_in_days  = 1
  lifecycle {
    prevent_destroy = true
  }
}

output "database" {
  value = snowflake_database.mdm.name
}

output "warehouse" {
  value = snowflake_warehouse.mdm.name
}

output "source_schema" {
  value = snowflake_schema.raw.name
}
