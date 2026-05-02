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

- [x] Timeout処理のバグ修正、テスト反映
- [x] 存在しないホスト名をWS URL指定時のタイムアウトが長い、修正する
- [x] app/domain/service.pyのapi_status_codeが200指定になっている、返却のHTTPステータスコードを指定する
- [x] Databricks SDKのタイムアウト問題、REST API直の置き換えを検討（→ doc/Architecture.md 参照）
- [ ] DatabricksAdapter を REST API（requests）に置き換える（→ レビュー対応セクション参照）

---

## レビュー対応

- [ ] **`use_monitor=False` を削除（Timer Trigger 設定修正）**  
  `function_app.py` の `@app.timer_trigger` で `use_monitor=False` を指定しているが、
  30分間隔のスケジュールでは非推奨。  
  複数インスタンスにスケールアウトした場合の重複実行を防ぐため、
  `use_monitor=False` を削除して Azure Functions デフォルト（`True`）に戻す。

- [ ] **Config 遅延初期化**  
  `function_app.py` のモジュールレベルで `Config.from_env()` を即時呼び出しているため、
  起動時に失敗すると Function がロード不能になる。  
  遅延初期化＋モジュールキャッシュパターン（`_config = None` をハンドラ内で初期化）へ変更する。

- [ ] **DatabricksAdapter を REST API に置き換え（タイムアウト付き）**  
  Databricks SDK は Managed ID をサポートしておらず、タイムアウト制御も複雑になるため REST API 直呼び出しへ変更。  
  `requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=N)` を使用する。

- [ ] **バリデーション堅牢化**  
  `config.py` の `workspace_url` に HTTPS 必須チェックなど、より詳細なバリデーションを追加する。

- [ ] **Log Analytics 送信リトライ**  
  `LogAnalyticsAdapter.send()` の `LogsIngestionClient.upload()` 呼び出しに  
  エクスポーネンシャルバックオフによるリトライ処理を追加する。

- [ ] **logging 改善: logger 経由に統一**  
  全モジュールで `logger = logging.getLogger(__name__)` を定義し、  
  `logging.info` 等の直接呼び出しを `logger.info` / `logger.error` 等へ変更する。

- [ ] **デバッグログ追加**  
  主要処理・モジュールの開始・終端に `logger.debug` を追加する。

- [ ] **`EndpointRecord.to_log_dict()` を `LogAnalyticsAdapter` へ移動**  
  モデルは純粋なデータ定義のみ持つべき（ヘキサゴナルアーキ整合）。  
  LA フィールド名変換ロジック（`TimeGenerated` 等へのマッピング）をアダプター内に移動する。

- [ ] **Config 責務の整理**  
  `config.py` の Azure Functions 固有処理（環境変数ロード）をアダプター/エントリーポイントへ移動。  
  モデル（`WorkspaceConfig`）はドメイン層に残し、I/F はポートに定義する。