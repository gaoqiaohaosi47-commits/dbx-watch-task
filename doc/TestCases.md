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
- **観点**: テストの目的・確認ポイント
- **前提/入力**: テストの初期状態・入力値
- **操作**: 実施する操作
- **期待値/結果**: 確認すべき結果

| ID | モジュール | クラス/関数 | 種別 | 観点 | 前提/入力 | 操作 | 期待値/結果 |
|---|---|---|---|---|---|---|---|
| UT-01 | domain/model.py | `WorkspaceConfig` | 正常 | 正常生成・全フィールド設定 | 正常なフィールド値（id, url, enabled=True） | dataclassをインスタンス化 | 全フィールドが正しく設定される |
| UT-02 | domain/model.py | `WorkspaceConfig` | 境界 | monitor_enabled=False の設定 | monitor_enabled=False | dataclassをインスタンス化 | monitor_enabled=False が設定される |
| UT-03 | domain/model.py | `EndpointRecord` | 正常 | 成功時フィールドの設定 | 成功フィールド（api_status_code=200、endpoint_name等あり） | dataclassをインスタンス化 | 全フィールドが正しく設定される |
| UT-04 | domain/model.py | `EndpointRecord` | 正常 | 失敗時の Null フィールド設定 | 失敗フィールド（api_status_code=403、endpoint_name等=None） | dataclassをインスタンス化 | Noneフィールドが正しく設定される |
| UT-05 | domain/model.py | `EndpointRecord.to_log_dict()` | 正常 | 成功レコードの dict 変換・TimeGenerated キー | 成功レコードのインスタンス | to_log_dict() を呼び出す | "TimeGenerated"キーが存在し、値がISO8601形式。全フィールドがLA用キー名でdictに含まれる |
| UT-06 | domain/model.py | `EndpointRecord.to_log_dict()` | 正常 | 失敗レコードの Null フィールド変換 | 失敗レコードのインスタンス | to_log_dict() を呼び出す | "endpoint_name", "endpoint_state", "endpoint_raw_data" がNullで含まれる |
| UT-07 | config.py | `Config.from_env()` | 正常 | 全環境変数正常設定時の Config 生成 | 全環境変数が正しく設定 | from_env() を呼び出す | Configオブジェクトが生成され、全フィールドが正しい値 |
| UT-08 | config.py | `Config.from_env()` | 異常 | DCE_ENDPOINT 未設定のバリデーション | DCE_ENDPOINT が未設定 | from_env() を呼び出す | ValueError または EnvironmentError が発生する |
| UT-09 | config.py | `Config.from_env()` | 異常 | WORKSPACE_LIST 不正 JSON のバリデーション | WORKSPACE_LIST が不正なJSON | from_env() を呼び出す | ValueError が発生する |
| UT-10 | config.py | `Config.from_env()` | 境界 | WORKSPACE_LIST 空配列時の Config 生成 | WORKSPACE_LIST が空配列 `[]` | from_env() を呼び出す | workspace_list が空リストのConfigオブジェクトが生成される |
| UT-11 | domain/service.py | `EndpointMonitorService.run()` | 正常 | 正常2エンドポイント取得・レコード生成 | モックアダプターが2件のエンドポイントを返す（1WS） | run(workspace_list) を呼び出す | EndpointRecordのリスト2件が返される |
| UT-12 | domain/service.py | `EndpointMonitorService.run()` | 異常 | 例外発生時のエラーレコード生成・処理継続 | モックアダプターが例外を発生させる（1WS） | run(workspace_list) を呼び出す | 例外はキャッチされ、エラーEndpointRecord1件（endpoint_name/state/raw_data=None）が返される |
| UT-13 | domain/service.py | `EndpointMonitorService.run()` | 正常 | monitor_enabled=False の WS スキップ | monitor_enabled=False のWS | run(workspace_list) を呼び出す | アダプターの呼び出しなし。返却リストは空 |
| UT-14 | domain/service.py | `EndpointMonitorService.run()` | 正常 | 複数 WS・複数エンドポイントの集計 | 2WS、両方とも2エンドポイント | run(workspace_list) を呼び出す | 計4件のEndpointRecordが返される |
| UT-15 | domain/service.py | `EndpointMonitorService.run()` | 異常 | 一部 WS 失敗時の処理継続 | 2WS、WS1失敗・WS2成功 | run(workspace_list) を呼び出す | WS1のエラーレコード1件 + WS2の正常レコードN件が返される |
| UT-16 | adapters/databricks_adapter.py | `DatabricksAdapter.fetch_endpoints()` | 正常 | 正常2エンドポイント取得・dict 変換 | WorkspaceClientをモック化、2エンドポイントを返す | fetch_endpoints(workspace) を呼び出す | dict形式のエンドポイントリスト2件が返される |
| UT-17 | adapters/databricks_adapter.py | `DatabricksAdapter.fetch_endpoints()` | 異常 | API 例外のサービス層への伝播 | WorkspaceClientがDatabricksError を発生 | fetch_endpoints(workspace) を呼び出す | 例外がサービス層に伝播する |
| UT-18 | adapters/log_analytics_adapter.py | `LogAnalyticsAdapter.send()` | 正常 | 複数レコードの一括 upload 呼び出し | LogsIngestionClientをモック化、3件のレコード | send(records) を呼び出す | client.upload() が1回呼ばれ、3件分のdictリストが渡される |
| UT-19 | adapters/log_analytics_adapter.py | `LogAnalyticsAdapter.send()` | 境界 | 空リスト時の早期リターン（upload 未呼び出し） | レコードリストが空 | send([]) を呼び出す | client.upload() が呼ばれない（早期リターン） |
| UT-20 | adapters/log_analytics_adapter.py | `LogAnalyticsAdapter.send()` | 異常 | HttpResponseError の呼び出し元への伝播 | LogsIngestionClientがHttpResponseError を発生 | send(records) を呼び出す | 例外がfunction_app.py に伝播する |
| UT-21 | ports/serving_endpoint_port.py | `ServingEndpointPort` | 正常 | ABC による実装強制（TypeError） | ABCを実装せずにサブクラス定義 | サブクラスをインスタンス化 | TypeError が発生する（ABC強制） |
| UT-22 | ports/log_sender_port.py | `LogSenderPort` | 正常 | ABC による実装強制（TypeError） | ABCを実装せずにサブクラス定義 | サブクラスをインスタンス化 | TypeError が発生する（ABC強制） |
| UT-23 | adapters/databricks_adapter.py | `DatabricksAdapter.fetch_endpoints()` | 正常 | http_timeout_seconds の WorkspaceClient への引き渡し | WorkspaceClientをモック化 | fetch_endpoints(workspace) を呼び出す | WorkspaceClientに `http_timeout_seconds=HTTP_TIMEOUT_SECONDS` が渡される |
| UT-24 | adapters/databricks_adapter.py | `DatabricksAdapter.fetch_endpoints()` | 異常 | TimeoutError のサービス層への伝播 | WorkspaceClientが TimeoutError を発生 | fetch_endpoints(workspace) を呼び出す | TimeoutError が呼び出し元（サービス層）に伝播する |
| UT-25 | domain/service.py | `EndpointMonitorService.run()` | 正常 | 成功レコードへの workspace_id 記録 | モックが1エンドポイントを返す・workspace_id="ws-id-9999" | run(workspace_list) を呼び出す | 成功レコードの workspace_id が "ws-id-9999" である |
| UT-26 | domain/service.py | `EndpointMonitorService.run()` | 異常 | エラーレコードへの workspace_id 記録 | モックが例外を発生・workspace_id="ws-id-error" | run(workspace_list) を呼び出す | エラーレコードの workspace_id が "ws-id-error" である |
| UT-27 | domain/service.py | `EndpointMonitorService.run()` | 異常 | HTTP 例外の status_code 取得 | status_code=403 属性を持つ例外 | run(workspace_list) を呼び出す | エラーレコードの api_status_code が 403 になる |
| UT-28 | domain/service.py | `EndpointMonitorService.run()` | 異常 | 非 HTTP 例外の api_status_code=0 デフォルト | status_code 属性を持たない例外（ConnectionError等） | run(workspace_list) を呼び出す | エラーレコードの api_status_code が 0 になる |
| UT-29 | domain/model.py | `EndpointRecord.to_log_dict()` | 正常 | to_log_dict() の全キー網羅確認 | 正常なEndpointRecordインスタンス | to_log_dict() を呼び出す | 返り値のキーが期待する8キー（TimeGenerated, workspace_id, workspace_url, api_status_code, api_error_message, endpoint_name, endpoint_state, endpoint_raw_data）と完全一致 |
| UT-30 | adapters/log_analytics_adapter.py | `LogAnalyticsAdapter.send()` | 正常 | LA ペイロードへの workspace_id 含有確認 | 成功レコード1件 | send(records) を呼び出す | upload に渡される logs の要素に workspace_id が含まれる |
| UT-31 | config.py | `Config.from_env()` | 異常 | WORKSPACE_LIST 未設定のバリデーション | WORKSPACE_LIST が未設定 | from_env() を呼び出す | ValueError が発生する |
| UT-32 | config.py | `Config.from_env()` | 異常 | DCR_IMMUTABLE_ID 未設定のバリデーション | DCR_IMMUTABLE_ID が未設定 | from_env() を呼び出す | ValueError が発生する |
| UT-33 | config.py | `Config.from_env()` | 異常 | DCR_STREAM_NAME 未設定のバリデーション | DCR_STREAM_NAME が未設定 | from_env() を呼び出す | ValueError が発生する |
| UT-34 | config.py | `Config.from_env()` | 異常 | workspace_id フィールド欠落のバリデーション | WORKSPACE_LIST 要素に workspace_id フィールドが欠落 | from_env() を呼び出す | ValueError が発生する |
| UT-35 | config.py | `Config.from_env()` | 異常 | monitor_enabled フィールド欠落のバリデーション | WORKSPACE_LIST 要素に monitor_enabled フィールドが欠落 | from_env() を呼び出す | ValueError が発生する |
| UT-36 | domain/service.py | `EndpointMonitorService.run()` | 境界 | 空リスト入力時のアダプター未呼び出し | workspace_list=[]（空リスト） | run([]) を呼び出す | 空リストが返りアダプターは呼ばれない |
| UT-37 | domain/service.py | `EndpointMonitorService.run()` | 異常 | api_error_message への例外メッセージ文字列変換 | 例外メッセージ "detailed error info" | run(workspace_list) を呼び出す | エラーレコードの api_error_message が "detailed error info" である |
| UT-38 | domain/service.py | `EndpointMonitorService.run()` | 正常 | time_generated の UTC ISO8601 形式 | 正常な1WS・1エンドポイント | run(workspace_list) を呼び出す | レコードの time_generated に "+00:00" が含まれる（UTC形式） |
| UT-39 | adapters/databricks_adapter.py | `DatabricksAdapter.fetch_endpoints()` | 正常 | 各エンドポイントへの as_dict() 呼び出し確認 | WorkspaceClientが2件のエンドポイントオブジェクトを返す | fetch_endpoints(workspace) を呼び出す | 各エンドポイントオブジェクトに対して as_dict() が1回ずつ呼ばれる |
| UT-40 | adapters/log_analytics_adapter.py | `LogAnalyticsAdapter.send()` | 境界 | 1件レコードの send() 正常動作 | 1件のレコード | send([record]) を呼び出す | client.upload() が1回呼ばれ、1件分の logs が渡される |
| UT-41 | domain/service.py | `EndpointMonitorService.run()` | 正常 | monitor_enabled 混在時の False WS スキップ | 3WS（True/False/True の順で monitor_enabled 設定） | run(workspace_list) を呼び出す | fetch_endpoints の呼び出しが2回のみ（False のWSはスキップ） |
| UT-42 | domain/service.py | `EndpointMonitorService.run()` | 正常 | fetch_endpoints への正しい WorkspaceConfig 引き渡し | 1WS・特定の WorkspaceConfig オブジェクト | run(workspace_list) を呼び出す | fetch_endpoints に渡される引数が元の WorkspaceConfig オブジェクトと一致する |
| UT-43 | config.py | `Config.from_env()` | 異常 | workspace_url フィールド欠落のバリデーション | WORKSPACE_LIST 要素に workspace_url フィールドが欠落 | from_env() を呼び出す | ValueError が発生する |
| UT-44 | config.py | `Config.from_env()` | 正常 | 複数 WS の正常読み込み | WORKSPACE_LIST に2件（monitor_enabled=True/False）設定 | from_env() を呼び出す | workspace_list に2件が読み込まれ、各フィールドが正しい値になっている |
