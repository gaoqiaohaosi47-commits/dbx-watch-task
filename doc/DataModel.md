# Data Model

## レコード種別

Log Analytics に送信するレコードは2種類。いずれも同じスキーマ（フィールド構成）を持ち、
成功/失敗の違いはフィールドの Null 有無で表現する。

### フィールド定義

| Pythonフィールド名（snake_case） | LAカラム名 | LA型 | Null許容 | 備考 |
|---|---|---|---|---|
| `time_generated` | `TimeGenerated` | datetime | No | LA標準フィールド。ISO 8601 UTC形式 |
| `workspace_id` | `workspace_id` | string | No | DatabricksワークスペースID |
| `workspace_url` | `workspace_url` | string | No | DatabricksワークスペースURL |
| `api_status_code` | `api_status_code` | int | No | HTTP成功時:200、HTTP失敗時:HTTPコード、非HTTPエラー時:0 |
| `api_error_message` | `api_error_message` | string | Yes | 成功時:null、失敗時:エラー内容 |
| `endpoint_name` | `endpoint_name` | string | Yes | 成功時:エンドポイント名、失敗時:null |
| `endpoint_state` | `endpoint_state` | string | Yes | 成功時:`READY`/`NOT_READY`、失敗時:null |
| `endpoint_raw_data` | `endpoint_raw_data` | dynamic | Yes | 成功時:DatabricksAPIレスポンスのエンドポイント単位JSON、失敗時:null |

> **memo.md との対応**（日本語 → 英語）
>
> | memo.md（日本語） | 本定義（英語） |
> |---|---|
> | タイムスタンプ | TimeGenerated |
> | ワークスペース識別子 | workspace_id / workspace_url |
> | Databricks REST API実行結果 | api_status_code |
> | Databricks REST API実行エラー内容 | api_error_message |
> | サービングエンドポイント情報_エンドポイント名 | endpoint_name |
> | サービングエンドポイント情報_エンドポイントState | endpoint_state |
> | サービングエンドポイントREST API結果の生情報(raw data) | endpoint_raw_data |

---

## JSONレコードイメージ

### 成功時（エンドポイント1件につき1レコード）

```json
{
    "TimeGenerated": "2026-04-11T10:00:00.123456Z",
    "workspace_url": "https://adb-1991908275471167.7.azuredatabricks.net",
    "api_status_code": 200,
    "api_error_message": null,
    "endpoint_name": "my-endpoint",
    "endpoint_state": "READY",
    "endpoint_raw_data": {
        "name": "my-endpoint",
        "state": {
            "ready": "READY",
            "config_update": "NOT_UPDATING"
        },
        "config": {
            "served_models": [
                {
                    "name": "my-model-1",
                    "model_name": "my-model",
                    "model_version": "3",
                    "workload_size": "Small",
                    "scale_to_zero_enabled": true
                }
            ]
        },
        "creation_timestamp": 1712345678000,
        "last_updated_timestamp": 1712345678000
    }
}
```

### 失敗時（ワークスペース1件につき1レコード）

```json
{
    "TimeGenerated": "2026-04-11T10:00:00.123456Z",
    "workspace_url": "https://adb-9999999999999999.9.azuredatabricks.net",
    "api_status_code": 403,
    "api_error_message": "Permission denied: User does not have VIEW privilege on serving endpoints.",
    "endpoint_name": null,
    "endpoint_state": null,
    "endpoint_raw_data": null
}
```

### 非HTTPエラー時（ネットワーク断など）

```json
{
    "TimeGenerated": "2026-04-11T10:00:00.123456Z",
    "workspace_url": "https://adb-unreachable.azuredatabricks.net",
    "api_status_code": 0,
    "api_error_message": "Connection timeout: HTTPSConnectionPool(host='adb-unreachable.azuredatabricks.net', port=443)",
    "endpoint_name": null,
    "endpoint_state": null,
    "endpoint_raw_data": null
}
```

---

## レコード数の計算

| 状況 | レコード数 |
|---|---|
| 成功: WSが N個、各WSにエンドポイントが M個 | N × M 件 |
| 失敗: WSが N個すべて失敗 | N 件（エラーレコード） |
| 混在: 一部成功・一部失敗 | 成功WS数 × エンドポイント数 + 失敗WS数 |
| あるWSのエンドポイントが0件 | そのWSは0件（レコード生成なし） |

---

## Python DataClass 定義（参照先）

実装は [app/domain/model.py](../app/domain/model.py) を参照。

```python
@dataclass
class WorkspaceConfig:
    workspace_id: str
    workspace_url: str
    monitor_enabled: bool

@dataclass
class EndpointRecord:
    time_generated: str       # ISO 8601 UTC
    workspace_url: str
    api_status_code: int
    api_error_message: Optional[str]
    endpoint_name: Optional[str]
    endpoint_state: Optional[str]
    endpoint_raw_data: Optional[Dict[str, Any]]

    # to_log_dict() はヘキサゴナルアーキ整合のため LogAnalyticsAdapter へ移動
    # LAフィールド名変換は adapters/log_analytics_adapter.py が担う
```

---

## Log Analyticsカスタムテーブル定義

`infra/main.tf`（`AppLogs_CL`）のスキーマ:

| カラム名 | 型 | 説明 |
|---|---|---|
| TimeGenerated | datetime | 必須（LAシステムフィールド） |
| workspace_id | string | |
| workspace_url | string | |
| api_status_code | int | |
| api_error_message | string | |
| endpoint_name | string | |
| endpoint_state | string | |
| endpoint_raw_data | dynamic | JSON格納 |
