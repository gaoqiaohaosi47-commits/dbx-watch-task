# 動作確認用のリソース

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.80.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = ">= 1.12.0"
    }
  }
}

#####################################
# variable
#####################################
variable "subscription_id" {
  type    = string
}

variable "resource_group_name" {
  type    = string
}

#####################################
# Provider
#####################################
provider "azurerm" {
  features {}
  subscription_id = var.subscription_id

  # Enterprise / CSP 環境で必須
  # skip_provider_registration = true
}

provider "azapi" {
  subscription_id = var.subscription_id
}

data "azurerm_client_config" "current" {}

#####################################
# Resource Group
#####################################
data "azurerm_resource_group" "rg" {
  name = var.resource_group_name
}

#####################################
# Log Analytics Workspace
#####################################
resource "azurerm_log_analytics_workspace" "la" {
  name                = "law-example"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

#####################################
# Custom Table (AzAPI)
# 必須：DCR 作成より先に存在している必要あり
#####################################
resource "azapi_resource" "custom_table" {
  type      = "Microsoft.OperationalInsights/workspaces/tables@2022-10-01"
  name      = "AppLogs_CL" # ✅ _CL必須（Custom_ は不要）
  parent_id = azurerm_log_analytics_workspace.la.id

  body = {
    properties = {
      schema = {
        name = "AppLogs_CL" # ✅ テーブル名と一致
        columns = [
          { name = "TimeGenerated",      type = "datetime" },
          { name = "workspace_url",      type = "string" },
          { name = "api_status_code",    type = "int" },
          { name = "api_error_message",  type = "string" },
          { name = "endpoint_name",      type = "string" },
          { name = "endpoint_state",     type = "string" },
          { name = "endpoint_raw_data",  type = "dynamic" }
        ]
      }
      retentionInDays = 30
    }
  }

  # テーブル作成後、少し待機
  lifecycle {
    ignore_changes = [body]
  }
}

#####################################
# Data Collection Endpoint (DCE)
#####################################
resource "azurerm_monitor_data_collection_endpoint" "dce" {
  name                = "dce-example"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name

  lifecycle {
    create_before_destroy = true
  }
}

#####################################
# Data Collection Rule (DCR)
# Logs Ingestion API 用 - AzAPI を使用
#####################################
resource "azapi_resource" "dcr" {
  type      = "Microsoft.Insights/dataCollectionRules@2022-06-01"
  name      = "dcr-custom-logs"
  location  = data.azurerm_resource_group.rg.location
  parent_id = data.azurerm_resource_group.rg.id

  depends_on = [azapi_resource.custom_table]

  body = {
    properties = {
      dataCollectionEndpointId = azurerm_monitor_data_collection_endpoint.dce.id

      # ✅ ストリーム定義（入力スキーマ）
      streamDeclarations = {
        "Custom-AppLogs" = {
          columns = [
            { name = "TimeGenerated",      type = "datetime" },
            { name = "workspace_url",      type = "string" },
            { name = "api_status_code",    type = "int" },
            { name = "api_error_message",  type = "string" },
            { name = "endpoint_name",      type = "string" },
            { name = "endpoint_state",     type = "string" },
            { name = "endpoint_raw_data",  type = "dynamic" }
          ]
        }
      }

      # ✅ 出力先定義
      destinations = {
        logAnalytics = [
          {
            name                = "la-destination"
            workspaceResourceId = azurerm_log_analytics_workspace.la.id
          }
        ]
      }

      # ✅ データフロー
      dataFlows = [
        {
          streams      = ["Custom-AppLogs"]
          destinations = ["la-destination"]
          transformKql = "source" # そのまま保存
          outputStream = "Custom-AppLogs_CL"
        }
      ]
    }
  }
}

#####################################
# RBAC: Terraform 実行者に付与（テスト用）
# ✅ 正しいロール名に修正
#####################################
resource "azurerm_role_assignment" "dcr_ingest_self" {
  scope                = azapi_resource.dcr.id
  role_definition_name = "Monitoring Metrics Publisher"
  principal_id         = data.azurerm_client_config.current.object_id

  # 同時作成時の競合を避ける
  depends_on = [azapi_resource.dcr]
}

#####################################
# Outputs（Python で使用）
#####################################
output "dce_endpoint" {
  value       = azurerm_monitor_data_collection_endpoint.dce.logs_ingestion_endpoint
  description = "Logs Ingestion API のエンドポイント"
}

output "dcr_immutable_id" {
  value       = azapi_resource.dcr.output.properties.immutableId
  description = "DCR の Immutable ID（API 呼び出しで使用）"
}

output "stream_name" {
  value       = "Custom-AppLogs"
  description = "API 呼び出し時に指定するストリーム名"
}

output "table_name" {
  value       = "AppLogs_CL"
  description = "Log Analytics のテーブル名"
}

output "workspace_id" {
  value       = azurerm_log_analytics_workspace.la.id
  description = "Log Analytics Workspace ID"
}
