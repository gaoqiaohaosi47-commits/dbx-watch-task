# Test Cases

## 内部結合テスト（Integration Tests）

**列の説明**:
- **分類**: 正常 / 異常 / 準正常 / データ整合 / 運用
- **観点**: テストの目的・確認ポイント
- **事前条件**: テスト実施前の環境状態
- **入力値**: 環境変数・テスト対象への入力
- **実施手順**: 操作手順
- **期待値/結果**: 確認すべき結果

| ID | 分類 | 観点 | 事前条件 | 入力値 | 実施手順 | 期待値/結果 |
|---|---|---|---|---|---|---|
| IT-01 | 正常 | 正常終了（1WS・2エンドポイント） | 1WSが設定済み、エンドポイント2件存在 | 正常な環境変数（全項目設定済み） | Functionを実行する | LAに2件のレコードが送信される。実行ログに成功が出力される |
| IT-02 | 正常 | 正常終了（2WS・各3エンドポイント） | 2WSが設定済み、各WSにエンドポイント3件 | 正常な環境変数 | Functionを実行する | LAに計6件のレコードが送信される |
| IT-03 | 正常 | エンドポイント0件 | 1WSが設定済み、エンドポイントが存在しない | 正常な環境変数 | Functionを実行する | エラーなく正常終了。LAへのレコード送信は0件（upload呼び出しなし） |
| IT-04 | 準正常 | 一部WS失敗・残りWS継続 | 2WS設定済み、WS1のAPIが失敗（403） | 正常な環境変数 | Functionを実行する | WS1:エラーレコード1件、WS2:正常レコードN件。合計N+1件がLAに送信される |
| IT-05 | 異常 | 全WS失敗 | 2WS設定済み、全WSのAPIが失敗 | 正常な環境変数 | Functionを実行する | エラーレコードがWS数（2件）分生成され、LAに送信される |
| IT-06 | 異常 | Databricks認証失敗（401） | マネージドIDにDatabricksのエンタイトルメントなし | 正常な環境変数 | Functionを実行する | api_status_code=401 のエラーレコードがLAに送信される |
| IT-07 | 異常 | Databricks認証失敗（403） | マネージドIDが権限不足 | 正常な環境変数 | Functionを実行する | api_status_code=403 のエラーレコードがLAに送信される |
| IT-08 | 異常 | LAインジェスト失敗（認証不足） | DCRに対してMonitoring Metrics Publisherロールなし | 正常な環境変数（DCRの権限のみ欠如） | Functionを実行する | LogAnalyticsAdapter.send()で例外が発生し、ログに出力される |
| IT-09 | 異常 | ネットワークエラー（Databricks到達不能） | 存在しないホスト名（例: `xxxxxxxxxxxx.xxxxxxxx`）を指定 | 正常な環境変数 | Functionを実行する | `HTTP_TIMEOUT_SECONDS`（30秒）以内にタイムアウトし、api_status_code=0・api_error_message にタイムアウト旨のメッセージが含まれるエラーレコードが生成される |
| IT-10 | 異常 | 環境変数異常（WORKSPACE_LIST が不正JSON） | - | WORKSPACE_LIST に不正なJSON文字列を設定 | Functionを実行する | config.py のfrom_env()で例外発生。エラーログが出力される |
| IT-11 | 異常 | 環境変数欠落（DCE_ENDPOINT 未設定） | - | DCE_ENDPOINT を削除した環境変数 | Functionを実行する | config.py のfrom_env()で例外発生。エラーログが出力される |
| IT-12 | 異常 | 環境変数欠落（DCR_IMMUTABLE_ID 未設定） | - | DCR_IMMUTABLE_ID を削除した環境変数 | Functionを実行する | config.py のfrom_env()で例外発生。エラーログが出力される |
| IT-13 | 準正常 | monitor_enabled=false のWSスキップ | 2WS設定済み、1WSがmonitor_enabled=false | 正常な環境変数 | Functionを実行する | monitor_enabled=false のWSはAPI呼び出しなし。有効WSのみレコードが生成される |
| IT-14 | データ整合 | TimeGenerated の精度 | 1WS・1エンドポイント | 正常な環境変数 | Functionを実行する | LAに届いたレコードのTimeGeneratedが実行時刻と5秒以内の差異である |
| IT-15 | データ整合 | workspace_url の正確性 | 2WS設定済み | 正常な環境変数 | Functionを実行する | 各レコードのworkspace_urlが送信元WSのURLと一致する |
| IT-16 | データ整合 | endpoint_raw_data の完全性 | 1WS・1エンドポイント（configあり） | 正常な環境変数 | Functionを実行する | endpoint_raw_dataがDatabricks APIのレスポンス（name, state, config等）を含む |
| IT-17 | データ整合 | 失敗時のnullフィールド | 1WSが認証失敗 | 正常な環境変数 | Functionを実行する | エラーレコードの endpoint_name, endpoint_state, endpoint_raw_data がnull |
| IT-18 | データ整合 | api_error_message の内容（HTTPエラー） | 1WSがHTTP 502を返す | 正常な環境変数 | Functionを実行する | api_error_messageに意味のあるエラー説明文字列が含まれる |
| IT-19 | データ整合 | api_status_code（非HTTPエラー） | ネットワーク断 | 正常な環境変数 | Functionを実行する | api_status_code=0 |
| IT-20 | データ整合 | endpoint_state の値 | 1WS・エンドポイントがNOT_READY状態 | 正常な環境変数 | Functionを実行する | レコードの endpoint_state="NOT_READY" |
| IT-21 | 正常 | WORKSPACE_LIST が空配列 | - | WORKSPACE_LIST=[] | Functionを実行する | エラーなく正常終了。LA送信なし |
| IT-22 | 正常 | 大量データ（10WS・各5エンドポイント） | 10WS設定済み、各5エンドポイント | 正常な環境変数 | Functionを実行する | 計50件のレコードがLAに一括送信される。upload()の呼び出しは1回 |
| IT-23 | データ整合 | LAへの一括送信（upload1回） | 2WS・各3エンドポイント | 正常な環境変数 | Functionを実行する | LogsIngestionClient.upload() の呼び出しが1回のみ |
| IT-24 | データ整合 | UTF-8エンコード（非ASCII文字を含むエンドポイント名） | エンドポイント名に日本語/記号 | 正常な環境変数 | Functionを実行する | LAにレコードが正常に届き、endpoint_nameが文字化けしない |
| IT-25 | 運用 | タイマースケジュール（定刻起動） | Functionデプロイ済み | 正常な設定 | 設定した実行間隔（5分）待機 | 設定間隔で定刻にFunctionが起動する |
| IT-26 | 運用 | past_due ログ出力 | 前回実行が遅延 | 正常な環境変数 | Timer past_due 状態でFunction起動 | past_dueのログが出力され、処理は正常継続する |
| IT-27 | 運用 | 実行ログの出力 | 1WS・1エンドポイント | 正常な環境変数 | Functionを実行する | Application InsightsまたはFunctionsログに送信件数等の実行結果ログが出力される |
| IT-28 | 準正常 | 0件エンドポイントWSと有効WSの混在 | 2WS：WS1にエンドポイント0件、WS2に3件 | 正常な環境変数 | Functionを実行する | WS1からレコード生成なし。WS2から3件のみLAに送信 |
| IT-29 | 異常 | WORKSPACE_LIST の要素にworkspace_url欠落 | - | workspace_url フィールドがない要素を含むWORKSPACE_LIST | Functionを実行する | 例外が発生し、エラーログが出力される |
| IT-30 | 異常 | LA Ingestion API の DCR_IMMUTABLE_ID 不正 | - | DCR_IMMUTABLE_ID に無効な値を設定 | Functionを実行する | LogsIngestionClient.upload() が例外を発生させ、エラーログに出力される |

---

## ユニットテスト（Unit Tests）

**列の説明**:
- **モジュール**: テスト対象ファイル
- **クラス/関数**: テスト対象
- **種別**: 正常 / 異常 / 境界
- **前提/入力**: テストの初期状態・入力値
- **操作**: 実施する操作
- **期待値/結果**: 確認すべき結果

| ID | モジュール | クラス/関数 | 種別 | 前提/入力 | 操作 | 期待値/結果 |
|---|---|---|---|---|---|---|
| UT-01 | domain/model.py | `WorkspaceConfig` | 正常 | 正常なフィールド値（id, url, enabled=True） | dataclassをインスタンス化 | 全フィールドが正しく設定される |
| UT-02 | domain/model.py | `WorkspaceConfig` | 境界 | monitor_enabled=False | dataclassをインスタンス化 | monitor_enabled=False が設定される |
| UT-03 | domain/model.py | `EndpointRecord` | 正常 | 成功フィールド（api_status_code=200、endpoint_name等あり） | dataclassをインスタンス化 | 全フィールドが正しく設定される |
| UT-04 | domain/model.py | `EndpointRecord` | 正常 | 失敗フィールド（api_status_code=403、endpoint_name等=None） | dataclassをインスタンス化 | Noneフィールドが正しく設定される |
| UT-05 | domain/model.py | `EndpointRecord.to_log_dict()` | 正常 | 成功レコードのインスタンス | to_log_dict() を呼び出す | "TimeGenerated"キーが存在し、値がISO8601形式。全フィールドがLA用キー名でdictに含まれる |
| UT-06 | domain/model.py | `EndpointRecord.to_log_dict()` | 正常 | 失敗レコードのインスタンス | to_log_dict() を呼び出す | "endpoint_name", "endpoint_state", "endpoint_raw_data" がNullで含まれる |
| UT-07 | config.py | `Config.from_env()` | 正常 | 全環境変数が正しく設定 | from_env() を呼び出す | Configオブジェクトが生成され、全フィールドが正しい値 |
| UT-08 | config.py | `Config.from_env()` | 異常 | DCE_ENDPOINT が未設定 | from_env() を呼び出す | ValueError または EnvironmentError が発生する |
| UT-09 | config.py | `Config.from_env()` | 異常 | WORKSPACE_LIST が不正なJSON | from_env() を呼び出す | ValueError が発生する |
| UT-10 | config.py | `Config.from_env()` | 境界 | WORKSPACE_LIST が空配列 `[]` | from_env() を呼び出す | workspace_list が空リストのConfigオブジェクトが生成される |
| UT-11 | domain/service.py | `EndpointMonitorService.run()` | 正常 | モックアダプターが2件のエンドポイントを返す（1WS） | run(workspace_list) を呼び出す | EndpointRecordのリスト2件が返される |
| UT-12 | domain/service.py | `EndpointMonitorService.run()` | 異常 | モックアダプターが例外を発生させる（1WS） | run(workspace_list) を呼び出す | 例外はキャッチされ、エラーEndpointRecord1件が返される |
| UT-13 | domain/service.py | `EndpointMonitorService.run()` | 正常 | monitor_enabled=False のWS | run(workspace_list) を呼び出す | アダプターの呼び出しなし。返却リストは空 |
| UT-14 | domain/service.py | `EndpointMonitorService.run()` | 正常 | 2WS、両方とも2エンドポイント | run(workspace_list) を呼び出す | 計4件のEndpointRecordが返される |
| UT-15 | domain/service.py | `EndpointMonitorService.run()` | 異常 | 2WS、WS1失敗・WS2成功 | run(workspace_list) を呼び出す | WS1のエラーレコード1件 + WS2の正常レコードN件が返される |
| UT-16 | adapters/databricks_adapter.py | `DatabricksAdapter.fetch_endpoints()` | 正常 | WorkspaceClientをモック化、2エンドポイントを返す | fetch_endpoints(workspace) を呼び出す | dict形式のエンドポイントリスト2件が返される |
| UT-17 | adapters/databricks_adapter.py | `DatabricksAdapter.fetch_endpoints()` | 異常 | WorkspaceClientがDatabricksError を発生 | fetch_endpoints(workspace) を呼び出す | 例外がサービス層に伝播する |
| UT-18 | adapters/log_analytics_adapter.py | `LogAnalyticsAdapter.send()` | 正常 | LogsIngestionClientをモック化、3件のレコード | send(records) を呼び出す | client.upload() が1回呼ばれ、3件分のdictリストが渡される |
| UT-19 | adapters/log_analytics_adapter.py | `LogAnalyticsAdapter.send()` | 境界 | レコードリストが空 | send([]) を呼び出す | client.upload() が呼ばれない（早期リターン） |
| UT-20 | adapters/log_analytics_adapter.py | `LogAnalyticsAdapter.send()` | 異常 | LogsIngestionClientがHttpResponseError を発生 | send(records) を呼び出す | 例外がfunction_app.py に伝播する |
| UT-21 | ports/serving_endpoint_port.py | `ServingEndpointPort` | 正常 | ABCを実装せずにサブクラス定義 | サブクラスをインスタンス化 | TypeError が発生する（ABC強制） |
| UT-22 | ports/log_sender_port.py | `LogSenderPort` | 正常 | ABCを実装せずにサブクラス定義 | サブクラスをインスタンス化 | TypeError が発生する（ABC強制） |
| UT-23 | adapters/databricks_adapter.py | `DatabricksAdapter.fetch_endpoints()` | 正常 | WorkspaceClientをモック化 | fetch_endpoints(workspace) を呼び出す | WorkspaceClientに `http_timeout_seconds=HTTP_TIMEOUT_SECONDS` が渡される |
| UT-24 | adapters/databricks_adapter.py | `DatabricksAdapter.fetch_endpoints()` | 異常 | WorkspaceClientが TimeoutError を発生 | fetch_endpoints(workspace) を呼び出す | TimeoutError が呼び出し元（サービス層）に伝播する |
