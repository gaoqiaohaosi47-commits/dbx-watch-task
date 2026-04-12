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
    │  requests             │  │  Azure Monitor           │
    │  GET /api/2.0/        │  │  LogsIngestionClient     │
    │  serving-endpoints    │  │  (Logs Ingestion API)    │
    │  ※移行予定            │  │                         │
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
   │       └─ requests.get(workspace_url/api/2.0/serving-endpoints) → endpoints × N件
   │          ※現在は Databricks SDK（WorkspaceClient）を使用。移行予定（→ 後述）
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
  │     └── [requests, azure-identity]  ※移行後（旧: databricks-sdk）
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
| `requests` (Databricks REST API) | 同一（REST API はマルチクラウド共通） | 変更不要 |

`domain/` および `ports/` は変更不要。

---

## DatabricksAdapter REST API 移行検討

### 背景

Databricks SDK（`databricks-sdk`）の `Config.__init__` が内部で `/.well-known/databricks-config` を取得する際、
モジュールレベルのデフォルト `_BaseClient(retry_timeout_seconds=300)` を使用するため、
ユーザー設定の `retry_timeout_seconds` が効かない。
結果として、無効なホスト名（存在しないワークスペース URL など）への接続で最長 5 分のブロックが発生する。

この問題を回避するため、現在は daemon スレッド + `thread.join(timeout=N)` で全体を打ち切っているが、
実装が複雑になっている。

### REST API 直接呼び出しとの比較

| 項目 | Databricks SDK | REST API（requests） |
|---|---|---|
| 行数 | 117 行（スレッド制御含む） | 約 35 行 |
| daemon スレッド | 必要（Config の内部タイムアウト回避） | 不要 |
| タイムアウト制御 | `thread.join(timeout=N)` で全体を打ち切り | `requests.get(timeout=N)` で直接制御 |
| エラー型 | `DatabricksError` サブクラス（型逆引き必要） | `requests.HTTPError`（`response.status_code` 直参照） |
| パッケージ依存 | `databricks-sdk`（重量級） | `requests`（`databricks-sdk` の推移的依存として既存） |
| ページネーション | SDK が自動処理 | `/api/2.0/serving-endpoints` は全件一括返却のため不要 |

### 結論

REST API 直接呼び出しへの移行を推奨。
- `requirements.txt` から `databricks-sdk` を削除可能
- daemon スレッドおよび `_STATUS_FROM_CLASS` 逆引きマップが不要になる
- `requests.get(timeout=N)` で単純かつ確実なタイムアウト制御が実現する

実装タスク: `doc/Todo.md` 参照（`DatabricksAdapter を REST API（requests）に置き換える`）
