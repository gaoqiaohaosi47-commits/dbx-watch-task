# Todo

## 前準備（Doc整備・スケルトン作成）

- [x] `doc/Plan.md` 作成
- [x] `doc/Todo.md` 作成
- [x] `doc/Architecture.md` 作成
- [x] `doc/DataModel.md` 作成
- [x] `doc/AppSettings.md` 作成
- [x] `doc/TestCases.md` 作成
- [x] `app/domain/model.py` 更新（WorkspaceConfig + EndpointRecord dataclass）
- [x] `app/domain/__init__.py` / `app/ports/__init__.py` / `app/adapters/__init__.py` 作成
- [x] `app/config.py` スケルトン作成
- [x] `app/domain/service.py` スケルトン作成
- [x] `app/ports/serving_endpoint_port.py` スケルトン作成
- [x] `app/ports/log_sender_port.py` スケルトン作成
- [x] `app/adapters/databricks_adapter.py` スケルトン作成
- [x] `app/adapters/log_analytics_adapter.py` スケルトン作成
- [x] `app/function_app.py` 更新（DI配線スケルトン）
- [x] `app/requirements.txt` 更新（依存追加）

---

## 実装

### 設定・モデル

- [x] `config.py`: `Config.from_env()` 実装（JSON parse、バリデーション）
- [x] `domain/model.py`: `EndpointRecord.to_log_dict()` 実装（LAフィールド名マッピング）

### ポート実装（アダプター）

- [x] `adapters/databricks_adapter.py`: `DatabricksAdapter.fetch_endpoints()` 実装
  - credential.get_token() でAzureトークン取得
  - WorkspaceClient 初期化
  - serving_endpoints.list() 呼び出し
  - as_dict() でシリアライズ
- [x] `adapters/log_analytics_adapter.py`: `LogAnalyticsAdapter.send()` 実装
  - records が空の場合は早期リターン
  - to_log_dict() で変換
  - LogsIngestionClient.upload() 呼び出し

### ドメインサービス

- [x] `domain/service.py`: `EndpointMonitorService.run()` 実装
  - monitor_enabled=False のスキップ
  - ワークスペース毎のtry/except
  - エラーレコード生成（api_status_code, api_error_message）
- [x] `domain/service.py`: `_process_workspace()` 実装

### エントリーポイント

- [x] `function_app.py`: DI配線実装
  - DefaultAzureCredential / ManagedIdentityCredential 選択
  - Config.from_env() 呼び出し
  - EndpointMonitorService インスタンス化
  - run() 呼び出し → send() 呼び出し
  - 実行結果ログ出力
- [x] `local.settings.json`: 開発用環境変数追加（WORKSPACE_LIST 等のダミー値）

### インフラ（別タスク）

- [x] `infra/main.tf`: カスタムテーブルスキーマをデータモデルに合わせて更新

---

## テスト

### ユニットテスト

- [x] `tests/unit/` ディレクトリ作成
- [x] `test_model.py`: WorkspaceConfig / EndpointRecord テスト
- [x] `test_config.py`: Config.from_env() テスト（正常・異常・境界）
- [x] `test_service.py`: EndpointMonitorService.run() テスト（モックアダプター使用）
- [x] `test_databricks_adapter.py`: DatabricksAdapter テスト（SDK モック）
- [x] `test_log_analytics_adapter.py`: LogAnalyticsAdapter テスト（クライアントモック）
- [x] `test_ports.py`: ServingEndpointPort / LogSenderPort ABC 強制テスト
- 実行結果: **33 passed** (`pytest --tb=short -q`)

### 内部結合テスト

- [ ] `tests/integration/` ディレクトリ作成
- [ ] テストケース `doc/TestCases.md` の IT-01〜IT-30 を実施（Azure 実環境が必要）
- [ ] テスト結果をTestCases.mdに記録

## 改修

- [ ] Timeout処理のバグ修正、テスト反映
- [ ] 存在しないホスト名をWS URL指定時のタイムアウトが長い、修正する
- [ ] app/domain/service.pyのapi_status_codeが200指定になっている、返却のHTTPステータスコードを指定する
