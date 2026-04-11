# Architecture

## パターン: ヘキサゴナルアーキテクチャ（Ports & Adapters）

### 採用理由

Azure特有の依存（マネージドID認証、Log Analytics Ingestion API、Databricks SDK）をアダプター層に閉じ込める。  
将来AWS環境でも稼働させる際は、新しいアダプター実装（IAM認証・CloudWatchなど）を追加するだけでよく、ドメイン層・ポート層は変更不要。

---

## コンポーネント図

```
┌─────────────────────────────────────────────────────────────┐
│                   Azure Functions Runtime                    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  function_app.py（エントリーポイント）                  │   │
│  │  - Timer Trigger ハンドラ                             │   │
│  │  - DI組み立て（credential → adapters → service）       │   │
│  │  - Config.from_env() 呼び出し                         │   │
│  │  - 実行結果ログ出力                                    │   │
│  └────────────────────┬─────────────────────────────────┘   │
│                       │                                     │
│  ┌────────────────────▼─────────────────────────────────┐   │
│  │  domain/service.py（EndpointMonitorService）          │   │
│  │  - ワークスペース毎のループ処理                         │   │
│  │  - monitor_enabled フィルタ                           │   │
│  │  - エラー分離（1件失敗でも他WS継続）                    │   │
│  │  - レコード集約                                        │   │
│  └─────────────┬──────────────────────┬─────────────────┘   │
│                │                      │                     │
│  ┌─────────────▼──────────┐  ┌────────▼────────────────┐    │
│  │  ports/                │  │  ports/                 │    │
│  │  serving_endpoint_port │  │  log_sender_port        │    │
│  │  （ABC）                │  │  （ABC）                 │    │
│  └─────────────┬──────────┘  └────────┬────────────────┘    │
│                │                      │                     │
│  ┌─────────────▼──────────┐  ┌────────▼────────────────┐    │
│  │  adapters/             │  │  adapters/              │    │
│  │  DatabricksAdapter     │  │  LogAnalyticsAdapter    │    │
│  └─────────────┬──────────┘  └────────┬────────────────┘    │
│                │                      │                     │
└────────────────┼──────────────────────┼─────────────────────┘
                 │                      │
    ┌────────────▼──────────┐  ┌────────▼────────────────┐
    │  Databricks SDK       │  │  Azure Monitor           │
    │  WorkspaceClient      │  │  LogsIngestionClient     │
    │  (serving_endpoints   │  │  (Logs Ingestion API)    │
    │   .list())            │  │                         │
    └───────────────────────┘  └─────────────────────────┘
            │                            │
    ┌───────▼────────────┐    ┌──────────▼──────────────┐
    │  Databricks REST   │    │  Azure Log Analytics     │
    │  API               │    │  (DCE / DCR)             │
    │  GET /api/2.0/     │    │                         │
    │  serving-endpoints │    │                         │
    └────────────────────┘    └─────────────────────────┘
```

---

## データフロー（処理順）

```
1. Timer Trigger 起動（cron: 0 */5 * * * *）
   │
2. function_app.py
   ├─ Config.from_env() で設定ロード
   │    WORKSPACE_LIST / DCE_ENDPOINT / DCR_IMMUTABLE_ID / DCR_STREAM_NAME
   ├─ DefaultAzureCredential（or ManagedIdentityCredential）生成
   ├─ DatabricksAdapter(credential) 生成
   ├─ LogAnalyticsAdapter(credential, dce, dcr_id, stream) 生成
   └─ EndpointMonitorService(endpoint_port, log_sender_port) 生成
   │
3. EndpointMonitorService.run(workspace_list)
   │
   ├─ [ワークスペースAループ] monitor_enabled=False → スキップ
   │
   ├─ [ワークスペースBループ]
   │   └─ DatabricksAdapter.fetch_endpoints(workspace)
   │       ├─ credential.get_token("2ff814a6.../.default")
   │       ├─ WorkspaceClient(host=workspace_url, token=token.token)
   │       └─ serving_endpoints.list() → endpoint.as_dict() × N件
   │       │
   │       成功 → EndpointRecord × N件（エンドポイント毎）生成
   │       失敗 → EndpointRecord × 1件（エラー）生成、次WSへ継続
   │
   └─ 全レコード結合
   │
4. LogAnalyticsAdapter.send(all_records)
   ├─ records が空 → 早期リターン
   ├─ record.to_log_dict() で LAフィールド名に変換
   └─ LogsIngestionClient.upload(rule_id, stream_name, logs) 一括送信
   │
5. function_app.py
   └─ 送信件数・結果をログ出力（logging.info）
   │
6. 処理終了
```

---

## モジュール依存関係

```
function_app.py
  ├── config.py
  │     └── domain/model.py (WorkspaceConfig)
  ├── domain/service.py
  │     ├── domain/model.py
  │     ├── ports/serving_endpoint_port.py
  │     └── ports/log_sender_port.py
  ├── adapters/databricks_adapter.py
  │     ├── ports/serving_endpoint_port.py
  │     ├── domain/model.py
  │     └── [databricks-sdk, azure-identity]
  └── adapters/log_analytics_adapter.py
        ├── ports/log_sender_port.py
        ├── domain/model.py
        └── [azure-monitor-ingestion, azure-identity]
```

**依存の方向**: 外側（アダプター）→ 内側（ポート・ドメイン）のみ。逆方向依存なし。

---

## 将来のAWS移植対応

| Azure コンポーネント | AWS 相当 | 差し替え範囲 |
|---|---|---|
| `DefaultAzureCredential` | `boto3` セッション / IAM ロール | `adapters/` のみ |
| `LogsIngestionClient` (Log Analytics) | CloudWatch Logs / S3 | `adapters/log_analytics_adapter.py` 差し替え |
| `azure-identity` | `botocore` | `requirements.txt` |
| `function_app.py` の Timer Trigger | Lambda + EventBridge | エントリーポイントのみ |
| Databricks SDK (WorkspaceClient) | 同一（Databricks SDK はマルチクラウド対応） | 変更不要 |

`domain/` および `ports/` は変更不要。
