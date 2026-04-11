# Implementation Plan

## 1. プロジェクト概要

**目的**: Azure Function（Timer Trigger）でDatabricksワークスペースのサービングエンドポイント情報を定期収集し、Azure Log Analytics（LA）へ一括転送する監視ジョブ。

**処理サマリ**:
```
Timer Trigger 起動
  → 環境変数から監視対象ワークスペース一覧をロード
  → ワークスペース毎にDatabricks REST API呼び出し
      成功: エンドポイント単位でレコード生成
      失敗: ワークスペース単位でエラーレコード生成（他WSの処理は継続）
  → 全レコードをLog Ingestion APIで一括送信
  → 実行ログ出力 → 終了
```

**実行環境**: Azure Functions v4 / Python 3.12

---

## 2. アーキテクチャ方針

**パターン**: ヘキサゴナルアーキテクチャ（Ports & Adapters）

**採用理由**:
- Azure特有の依存（マネージドID認証・LA Ingestion API・Databricks SDK）をアダプター層に閉じ込める
- 将来AWS環境へ移植する際、ドメイン層・ポート層は変更不要。アダプターのみ差し替え

**層の責務**:

| 層 | ディレクトリ/ファイル | 責務 |
|---|---|---|
| エントリーポイント | `function_app.py` | Timer Triggerハンドラ、DI組み立て |
| 設定 | `config.py` | 環境変数ロード・バリデーション |
| ドメイン（モデル） | `domain/model.py` | データクラス定義（Azure/Databricks依存なし） |
| ドメイン（サービス） | `domain/service.py` | ビジネスロジック・オーケストレーション |
| ポート（抽象） | `ports/` | 外部依存の抽象インターフェース（ABC） |
| アダプター（実装） | `adapters/` | Azure/Databricks SDK を使った具体実装 |

---

## 3. ファイル構成

```
app/
├── function_app.py                   # エントリーポイント（Timer Trigger・DI配線）
├── config.py                         # 設定ロード
├── requirements.txt                  # Python依存パッケージ
├── host.json
├── local.settings.json
├── domain/
│   ├── __init__.py
│   ├── model.py                      # WorkspaceConfig, EndpointRecord
│   └── service.py                    # EndpointMonitorService
├── ports/
│   ├── __init__.py
│   ├── serving_endpoint_port.py      # ServingEndpointPort (ABC)
│   └── log_sender_port.py            # LogSenderPort (ABC)
└── adapters/
    ├── __init__.py
    ├── databricks_adapter.py         # DatabricksAdapter
    └── log_analytics_adapter.py      # LogAnalyticsAdapter
```

---

## 4. 主要設計決定

### 4-1. WorkspaceClientはWS毎に初期化

Databricks SDK の `WorkspaceClient` は1ホストに束縛されるため、
`WORKSPACE_LIST` の要素毎（ホストURLが異なる）に新規インスタンスを作成する。
`credential` オブジェクトは共有して再利用。

### 4-2. Databricksトークン明示取得パターン

POC（`local/poc.py`）の実績パターンを採用:
```python
token = credential.get_token(f"{AZURE_DATABRICKS_RESOURCE_ID}/.default")
w = WorkspaceClient(host=workspace_url, token=token.token)
```
DatabricksリソースID（`2ff814a6-3304-4ab8-85cb-cd0e6f879c1d`）はAzure全体で固定の定数。

### 4-3. `endpoint_raw_data` は `as_dict()` 結果をそのまま格納

Databricks SDK の `ServingEndpointDetailed` オブジェクトを `as_dict()` でdict化し、
`endpoint_raw_data` に格納する。LAのカラム定義変更なしに全フィールドをクエリ可能。

### 4-4. 非HTTPエラー時の `api_status_code`

ネットワーク断・タイムアウトなどHTTPステータスがない例外の場合:
- `api_status_code = 0`
- `api_error_message` = 例外メッセージ

### 4-5. フィールド名変換の一元化

`EndpointRecord`（Pythonic snake_case）→ Log Analytics フィールド名（`TimeGenerated`等）への
変換は `EndpointRecord.to_log_dict()` 内のみで行う。アダプター側では変換しない。

### 4-6. `monitor_enabled=False` のフィルタはサービス層で処理

設定ロード（`config.py`）ではフィルタせず、`domain/service.py` の `run()` 内で
`monitor_enabled=False` のワークスペースをスキップする（ドメインロジック）。

### 4-7. エラー分離

各ワークスペースの処理を `try/except` で囲み、1件失敗しても他WSの処理を継続する。
失敗ワークスペースはエラーレコード1件を生成してリストに追加。

---

## 5. 依存パッケージ

| パッケージ | 用途 |
|---|---|
| `azure-functions` | Azure Functions ランタイムバインディング |
| `azure-identity` | `DefaultAzureCredential` / `ManagedIdentityCredential` |
| `azure-monitor-ingestion` | `LogsIngestionClient`（Log Ingestion API） |
| `databricks-sdk` | `WorkspaceClient`（サービングエンドポイント取得） |

---

## 6. 認証設定

| 接続先 | 認証方式 | 必要な権限設定 |
|---|---|---|
| Databricks | マネージドIDをサービスプリンシパルとして登録 | Databricksワークスペース上でエンタイトルメント付与 |
| Log Analytics (DCR) | マネージドID | DCRリソースに対して「Monitoring Metrics Publisher」ロール |

ローカル開発: `DefaultAzureCredential` → Azure CLI ログインで認証。

---

## 7. タイマースケジュール

| 設定値 | 意味 |
|---|---|
| `0 */5 * * * *` | 5分毎（実装時に要件に合わせて変更） |

---

## 8. スコープ外

- `infra/main.tf` のカスタムテーブルスキーマ更新（POCスキーマと実データモデルの差異）
- AWS アダプターの実装
- Application Insights の詳細設定
