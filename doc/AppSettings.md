# Application Settings Reference

## Azure Function App Settings（環境変数）

| 設定キー | 必須 | 値の例 | 説明 |
|---|---|---|---|
| `WORKSPACE_LIST` | Yes | `[{"workspace_id":"...","workspace_url":"...","monitor_enabled":true}]` | 監視対象DatabricksワークスペースのJSON配列（1行） |
| `DCE_ENDPOINT` | Yes | `https://<dce-name>.<region>.ingest.monitor.azure.com` | Data Collection Endpoint のURL |
| `DCR_IMMUTABLE_ID` | Yes | `dcr-<immutable-id>` | DCR の Immutable ID |
| `DCR_STREAM_NAME` | Yes | `Custom-AppLogs` | DCRストリーム名（LAカスタムテーブルへのマッピング） |
| `FUNCTIONS_WORKER_RUNTIME` | Yes | `python` | Azure Functionsランタイム指定（自動設定） |
| `AzureWebJobsStorage` | Yes | `UseDevelopmentStorage=true`（開発時） | Timerトリガーの状態管理ストレージ |

---

## `WORKSPACE_LIST` の構造

JSON配列形式で設定する。複数ワークスペースを含む場合も1行のJSONとして設定。

### 配列要素のフィールド

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `workspace_id` | string | Yes | DatabricksワークスペースID（数値IDの文字列） |
| `workspace_url` | string | Yes | ワークスペースのURL（`https://adb-XXXXXXXX.X.azuredatabricks.net`形式） |
| `monitor_enabled` | boolean | Yes | `false` の場合、そのWSはスキップされる |

### 設定例（1ワークスペース）

```json
[{"workspace_id":"<workspace-id>","workspace_url":"https://adb-<workspace-id>.<N>.azuredatabricks.net","monitor_enabled":true}]
```

### 設定例（複数ワークスペース、一部無効化）

```json
[{"workspace_id":"<workspace-id-1>","workspace_url":"https://adb-<workspace-id-1>.<N>.azuredatabricks.net","monitor_enabled":true},{"workspace_id":"<workspace-id-2>","workspace_url":"https://adb-<workspace-id-2>.<N>.azuredatabricks.net","monitor_enabled":false}]
```

---

## `local.settings.json`（ローカル開発用）

> このファイルはソースコード管理対象外（`.gitignore`）。ローカルのみに存在。

開発用の設定例:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "WORKSPACE_LIST": "[{\"workspace_id\":\"<workspace-id>\",\"workspace_url\":\"https://adb-<workspace-id>.<N>.azuredatabricks.net\",\"monitor_enabled\":true}]",
    "DCE_ENDPOINT": "https://<dce-name>.<region>.ingest.monitor.azure.com",
    "DCR_IMMUTABLE_ID": "dcr-<immutable-id>",
    "DCR_STREAM_NAME": "Custom-AppLogs"
  }
}
```

> ローカル実行時は `DefaultAzureCredential` が使用される。事前に `az login` でAzure CLIへログインしておくこと。

---

## マネージドID に必要な権限

Azure Function のシステム割当マネージドIDに以下の権限を付与する。

### Databricks（各監視対象ワークスペース毎）

| 設定場所 | 設定内容 |
|---|---|
| Databricks ワークスペース管理画面 | マネージドIDをサービスプリンシパルとして追加 |
| エンタイトルメント | `Can View` 以上（サービングエンドポイント閲覧に必要） |

手順概要:
1. Azure PortalでFunction AppのマネージドIDの **オブジェクト（プリンシパル）ID** を確認
2. Databricks ワークスペース → Settings → Identity and Access → Service Principals → Add
3. 対象のマネージドIDを追加し、適切なエンタイトルメントを付与

### Log Analytics / DCR

| リソース | ロール | 付与理由 |
|---|---|---|
| DCR（Data Collection Rule） | `Monitoring Metrics Publisher` | Logs Ingestion APIでのデータ書き込み |

手順概要:
1. Azure Portal → DCRリソース → アクセス制御(IAM) → ロール割り当ての追加
2. ロール: `Monitoring Metrics Publisher`
3. メンバー: Function Appのシステム割当マネージドID を選択

---

## Terraform Outputs との対応

`infra/main.tf` の outputs と本設定の対応:

| Terraform Output | 対応するApp Setting |
|---|---|
| `dce_endpoint` | `DCE_ENDPOINT` |
| `dcr_immutable_id` | `DCR_IMMUTABLE_ID` |
| `stream_name` | `DCR_STREAM_NAME` |
