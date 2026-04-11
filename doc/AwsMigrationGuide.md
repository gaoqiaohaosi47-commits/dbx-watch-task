# AWS 移植ガイド

Azure Functions → AWS Lambda、Log Analytics → CloudWatch Logs、Managed Identity → Databricks PAT への移植手順。

ヘキサゴナルアーキテクチャにより **ドメイン層・ポート層は変更不要**。アダプターとエントリーポイントのみ差し替える。

---

## 変更箇所サマリー

| ファイル | 対応 | 変更内容 |
|---|---|---|
| `function_app.py` | **書き換え** | Lambda ハンドラに差し替え |
| `config.py` | **修正** | 環境変数キーを AWS 用に変更 |
| `adapters/databricks_adapter.py` | **修正** | Managed Identity → PAT 認証に変更 |
| `adapters/log_analytics_adapter.py` | **新規作成で差し替え** | CloudWatch Logs アダプターに差し替え |
| `requirements.txt` | **修正** | azure-* を削除、boto3 を追加 |
| `domain/model.py` | **変更不要** | — |
| `domain/service.py` | **変更不要** | — |
| `ports/serving_endpoint_port.py` | **変更不要** | — |
| `ports/log_sender_port.py` | **変更不要** | — |

---

## 1. エントリーポイント: `function_app.py` → `lambda_function.py`

Azure Functions の Timer Trigger を AWS Lambda ハンドラに差し替える。
スケジュール実行は EventBridge Scheduler で設定する（コード変更不要）。

**Before: `app/function_app.py`**

```python
import azure.functions as func
from azure.identity import DefaultAzureCredential          # 削除
from adapters.log_analytics_adapter import LogAnalyticsAdapter

_credential = DefaultAzureCredential()                      # 削除
_log_analytics_adapter = LogAnalyticsAdapter(
    credential=_credential,                                 # 削除
    dce_endpoint=_config.dce_endpoint,                      # 削除
    dcr_immutable_id=_config.dcr_immutable_id,              # 削除
    dcr_stream_name=_config.dcr_stream_name,                # 削除
)
_service = EndpointMonitorService(
    endpoint_port=DatabricksAdapter(_credential),           # 変更: credential → pat_token
)

app = func.FunctionApp()

@app.timer_trigger(schedule="0 */30 * * * *", ...)
def timerTrigger(myTimer: func.TimerRequest) -> None:       # 変更: ハンドラシグネチャ
    ...
```

**After: `app/lambda_function.py`（新規作成）**

```python
import logging
from adapters.databricks_adapter import DatabricksAdapter
from adapters.cloudwatch_adapter import CloudWatchAdapter   # 新規アダプター
from config import Config
from domain.service import EndpointMonitorService

_config = Config.from_env()
_service = EndpointMonitorService(
    endpoint_port=DatabricksAdapter(pat_token=_config.databricks_pat_token),
)
_cloudwatch_adapter = CloudWatchAdapter(
    log_group_name=_config.log_group_name,
    log_stream_name=_config.log_stream_name,
    region_name=_config.aws_region,
)

def handler(event, context):
    """Lambda ハンドラ。EventBridge Scheduler から呼び出される。"""
    try:
        records = _service.run(_config.workspace_list)
        _cloudwatch_adapter.send(records)
        logging.info("[実行完了] 送信レコード数: %d", len(records))
    except Exception as e:
        logging.error("[実行エラー] %s", e, exc_info=True)
        raise
```

**ポイント:**
- `azure.functions` のインポートを削除
- `azure.identity.DefaultAzureCredential` を削除
- Lambda の `handler(event, context)` シグネチャに変更
- DI 組み立ての構造は維持

---

## 2. Databricks アダプター: `adapters/databricks_adapter.py`

Managed Identity によるトークン取得を PAT（Personal Access Token）に差し替える。
`fetch_endpoints()` の本体ロジックは変更不要。

**修正箇所: `app/adapters/databricks_adapter.py`**

```python
# --- 削除 ---
from azure.core.credentials import TokenCredential
AZURE_DATABRICKS_RESOURCE_ID = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"

# --- 変更前 ---
class DatabricksAdapter(ServingEndpointPort):
    def __init__(self, credential: TokenCredential) -> None:
        self._credential = credential

    def fetch_endpoints(self, workspace: WorkspaceConfig):
        token = self._credential.get_token(             # ← 削除
            f"{AZURE_DATABRICKS_RESOURCE_ID}/.default"  # ← 削除
        )                                               # ← 削除
        w = WorkspaceClient(
            host=workspace.workspace_url,
            token=token.token,                          # ← 変更
            http_timeout_seconds=HTTP_TIMEOUT_SECONDS,
        )

# --- 変更後 ---
class DatabricksAdapter(ServingEndpointPort):
    def __init__(self, pat_token: str) -> None:         # ← credential → pat_token: str
        self._pat_token = pat_token

    def fetch_endpoints(self, workspace: WorkspaceConfig):
        w = WorkspaceClient(
            host=workspace.workspace_url,
            token=self._pat_token,                      # ← PAT を直接渡す
            http_timeout_seconds=HTTP_TIMEOUT_SECONDS,
        )
        # 以降は変更不要
```

**ポイント:**
- `get_token()` の呼び出しが不要になるため、4行削除
- `__init__` の引数を `credential: TokenCredential` → `pat_token: str` に変更
- `AZURE_DATABRICKS_RESOURCE_ID` 定数は不要になるため削除

---

## 3. ログ送信アダプター: CloudWatch Logs 用を新規作成

`adapters/log_analytics_adapter.py` は Azure 専用のため、AWS 用アダプターを別ファイルで作成し、DI 差し替えのみで対応する。`LogSenderPort` インターフェースは変更不要。

**新規作成: `app/adapters/cloudwatch_adapter.py`**

```python
import json
import logging
import time
import boto3
from botocore.exceptions import ClientError
from domain.model import EndpointRecord
from ports.log_sender_port import LogSenderPort

logger = logging.getLogger(__name__)


class CloudWatchAdapter(LogSenderPort):
    """boto3 を使った CloudWatch Logs 送信アダプター。"""

    def __init__(self, log_group_name: str, log_stream_name: str, region_name: str) -> None:
        self._log_group = log_group_name
        self._log_stream = log_stream_name
        self._client = boto3.client("logs", region_name=region_name)
        self._ensure_log_stream()

    def _ensure_log_stream(self) -> None:
        """ロググループ・ストリームが存在しない場合は作成する。"""
        try:
            self._client.create_log_group(logGroupName=self._log_group)
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceAlreadyExistsException":
                raise
        try:
            self._client.create_log_stream(
                logGroupName=self._log_group,
                logStreamName=self._log_stream,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceAlreadyExistsException":
                raise

    def send(self, records: list[EndpointRecord]) -> None:
        if not records:
            logger.info("送信レコードなし。スキップ。")
            return

        log_events = [
            {
                "timestamp": int(time.time() * 1000),  # ミリ秒
                "message": json.dumps(record.to_log_dict(), ensure_ascii=False),
            }
            for record in records
        ]
        self._client.put_log_events(
            logGroupName=self._log_group,
            logStreamName=self._log_stream,
            logEvents=log_events,
        )
        logger.info("CloudWatch Logs に %d 件を送信しました", len(log_events))
```

**Log Analytics との主な違い:**

| 項目 | Log Analytics | CloudWatch Logs |
|---|---|---|
| 認証 | Managed Identity / DCR ロール | Lambda 実行ロール（IAM）で自動 |
| ログ形式 | dict のリスト | JSON 文字列（`message` フィールド） |
| タイムスタンプ | `TimeGenerated`（ISO8601） | `timestamp`（ミリ秒 epoch） |
| 送信先指定 | DCE URL + DCR Immutable ID | ロググループ名 + ストリーム名 |

---

## 4. 設定: `config.py`

環境変数キーを AWS 用に差し替える。クラス構造・バリデーションロジックは変更不要。

**修正箇所: `app/config.py`**

```python
# --- 削除する環境変数 ---
dce_endpoint: str          # DCE_ENDPOINT
dcr_immutable_id: str      # DCR_IMMUTABLE_ID
dcr_stream_name: str       # DCR_STREAM_NAME

# --- 追加する環境変数 ---
databricks_pat_token: str  # DATABRICKS_PAT_TOKEN  (Databricks PAT)
log_group_name: str        # CW_LOG_GROUP_NAME      (例: /dbx-watch-task/endpoints)
log_stream_name: str       # CW_LOG_STREAM_NAME     (例: prod)
aws_region: str            # AWS_REGION             (例: ap-northeast-1)
```

`from_env()` 内の `_require()` 呼び出しを上記に合わせて書き換える。

---

## 5. 依存パッケージ: `requirements.txt`

```diff
- azure-functions
- azure-identity
- azure-monitor-ingestion
  databricks-sdk
+ boto3
```

`databricks-sdk` はマルチクラウド対応のため変更不要。

---

## 6. IAM 権限設定（AWS）

Lambda 実行ロールに以下のポリシーを付与する。

```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "arn:aws:logs:<region>:<account-id>:log-group:/dbx-watch-task/*"
}
```

Databricks PAT はシークレットとして AWS Secrets Manager または Lambda 環境変数（暗号化済み）に格納することを推奨。

---

## 7. 変更不要なファイル

以下はクラウドへの依存を持たないため、**一切変更不要**。

| ファイル | 理由 |
|---|---|
| `domain/model.py` | データクラスのみ。Azure/AWS 依存なし |
| `domain/service.py` | ポート経由でのみ外部と通信。依存なし |
| `ports/serving_endpoint_port.py` | ABC のみ |
| `ports/log_sender_port.py` | ABC のみ |
| `host.json` | Lambda では不要（削除可） |

---

## 8. 移植後のファイル構成

```
app/
├── lambda_function.py                  # ← function_app.py を差し替え
├── config.py                           # ← 環境変数キーのみ変更
├── requirements.txt                    # ← azure-* 削除、boto3 追加
├── domain/                             # ← 変更なし
│   ├── model.py
│   └── service.py
├── ports/                              # ← 変更なし
│   ├── serving_endpoint_port.py
│   └── log_sender_port.py
└── adapters/
    ├── databricks_adapter.py           # ← PAT 認証に変更（数行）
    ├── log_analytics_adapter.py        # ← 残置（Azure 環境用）
    └── cloudwatch_adapter.py           # ← 新規作成
```
