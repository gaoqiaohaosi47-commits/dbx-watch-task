# ローカルテスト手順

## 前提条件

| 必要なもの | 確認コマンド |
|---|---|
| Dev Container 起動済み（Docker + VS Code） | — |
| Azure CLI ログイン済み | `az account show` |
| 監視対象 Databricks ワークスペースへのアクセス権 | — |
| DCE / DCR / LA ワークスペースが Azure 上に存在すること | `terraform output`（infra/ 配下で実行） |

> Dev Container を使用している場合、Azure Functions Core Tools・Python 3.12・Azurite はコンテナ内にインストール済みです。

---

## 1. Azure CLI ログイン

ローカル実行時は `DefaultAzureCredential` が Azure CLI の認証情報を使用します。

```bash
az login
az account show   # 対象サブスクリプションが表示されることを確認
```

別のサブスクリプションに切り替える場合:

```bash
az account set --subscription <サブスクリプションID>
```

---

## 2. 依存パッケージのインストール

```bash
cd /workspaces/dbx-watch-task/app
pip install -r requirements.txt
```

---

## 3. `local.settings.json` の値を確認・修正

`app/local.settings.json` に設定済みのダミー値を、実際の Azure リソース値に書き換えます。

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "WORKSPACE_LIST": "[{\"workspace_id\":\"<WS_ID>\",\"workspace_url\":\"https://adb-<WS_ID>.<N>.azuredatabricks.net\",\"monitor_enabled\":true}]",
    "DCE_ENDPOINT": "https://<dce-name>.<region>.ingest.monitor.azure.com",
    "DCR_IMMUTABLE_ID": "dcr-<immutable-id>",
    "DCR_STREAM_NAME": "Custom-AppLogs"
  }
}
```

### `WORKSPACE_LIST` の値を生成する

`local.settings.json` の `WORKSPACE_LIST` は **1行のエスケープ済み JSON 文字列** が必要です。  
以下のコマンドで、読みやすい JSON ファイルから変換できます。

**前提:** `workspace_list.json` を用意する（例）

```json
[
  {
    "workspace_id": "1234567890",
    "workspace_url": "https://adb-1234567890.1.azuredatabricks.net",
    "monitor_enabled": true
  }
]
```

**Linux / Bash（jq が必要）**

```bash
jq -c . workspace_list.json | python3 -c \
  "import sys, json; print(json.dumps(sys.stdin.read().strip()))"
```

出力例（この値を `WORKSPACE_LIST` にそのまま貼り付け）:

```
"[{\"workspace_id\":\"1234567890\",\"workspace_url\":\"https://adb-1234567890.1.azuredatabricks.net\",\"monitor_enabled\":true}]"
```

**Windows / PowerShell**

```powershell
$compact = (@(Get-Content workspace_list.json -Raw | ConvertFrom-Json) | ConvertTo-Json -Compress -Depth 10)
'"' + ($compact -replace '"', '\"') + '"'
```

出力形式は Linux と同様です。

---

Terraform を使っている場合は `infra/` ディレクトリで以下を実行すると値を確認できます:

```bash
cd /workspaces/dbx-watch-task/infra
terraform output
```

---

## 4. ローカル実行

### 4-1. Azurite の確認（Dev Container 使用時）

Dev Container では Azurite が常時起動しています（`docker-compose.yml` の `azurite` サービス）。  
`AzureWebJobsStorage=UseDevelopmentStorage=true` で自動的に接続されます。

### 4-2. Functions ホストの起動

```bash
cd /workspaces/dbx-watch-task/app
func start
```

起動成功時のログ例:

```
Azure Functions Core Tools
Core Tools Version:       4.x.x
...
Functions:
        timerTrigger: timerTrigger
...
Host started (27894ms)
```

### 4-3. 手動トリガー実行

Timer Trigger は手動で即時実行できます（スケジュール待ちが不要）。

別ターミナルを開いて:

```bash
curl -X POST http://localhost:7071/admin/functions/timerTrigger \
  -H "Content-Type: application/json" \
  -d "{}"
```

または VS Code の Azure Functions 拡張機能から「Execute Function Now」を選択。

---

## 5. 実行結果の確認

### 5-1. Functions ホストのログ

`func start` を実行しているターミナルに出力されます。

正常終了時:

```
[情報] 取得完了: https://adb-xxxx.azuredatabricks.net - エンドポイント 3 件
[情報] Log Analytics に 3 件を送信しました
[情報] [実行完了] 送信レコード数: 3
```

エラー発生時（例: 認証失敗）:

```
[エラー] ワークスペース https://adb-xxxx.azuredatabricks.net の処理に失敗 (status=403): ...
[情報] Log Analytics に 1 件を送信しました   ← エラーレコード
[情報] [実行完了] 送信レコード数: 1
```

### 5-2. Log Analytics でのレコード確認

Azure Portal → Log Analytics ワークスペース → ログ で以下のクエリを実行:

```kql
AppLogs_CL
| order by TimeGenerated desc
| take 20
```

エンドポイント状態の確認:

```kql
AppLogs_CL
| where TimeGenerated > ago(1h)
| project TimeGenerated, workspace_url, api_status_code, endpoint_name, endpoint_state
| order by TimeGenerated desc
```

エラーレコードのみ抽出:

```kql
AppLogs_CL
| where api_status_code != 200
| project TimeGenerated, workspace_url, api_status_code, api_error_message
| order by TimeGenerated desc
```

---

## 6. ユニットテスト実行

```bash
cd /workspaces/dbx-watch-task/app
pip install pytest pytest-mock
pytest tests/unit/ -v
```

> `tests/unit/` は今後作成予定（`doc/Todo.md` 参照）。

---

## トラブルシューティング

### `az login` 済みでも認証エラーになる

`DefaultAzureCredential` は複数の認証ソースを試行します。明示的に Azure CLI 認証を指定:

```python
from azure.identity import AzureCliCredential
credential = AzureCliCredential()
```

または環境変数でテナントを指定:

```bash
export AZURE_TENANT_ID=<テナントID>
```

### Databricks で `PermissionDenied (403)` が出る

マネージドID（ローカルでは Azure CLI ログインユーザー）が Databricks ワークスペースの  
サービスプリンシパルとして登録されていない。`doc/AppSettings.md` の「マネージドID に必要な権限」を参照。

### Log Analytics に送信できない（`HttpResponseError`）

DCR の `Monitoring Metrics Publisher` ロールが付与されているか確認:

```bash
az role assignment list \
  --assignee $(az ad signed-in-user show --query id -o tsv) \
  --scope <DCR_RESOURCE_ID> \
  --query "[].roleDefinitionName"
```

### `func start` で `WORKSPACE_LIST` 関連エラーが出る

`local.settings.json` の JSON 内部の `"` エスケープを確認。  
`\"` が正しく記述されているか確認してください。

### タイマースケジュールを変更してすぐに確認したい

`host.json` と関係なく、手動トリガー（手順 4-3）で即時実行できます。  
スケジュール変更が不要なため、`function_app.py` の `schedule` は変えなくてよいです。
