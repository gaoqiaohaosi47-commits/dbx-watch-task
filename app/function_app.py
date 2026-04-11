# function_app.py
"""
Azure Functions エントリーポイント（Timer Trigger）。

責務:
- DI 組み立て（credential → adapters → service）
- Config.from_env() による設定ロード
- EndpointMonitorService の実行
- 実行結果ログ出力
"""
import logging

import azure.functions as func
from azure.identity import DefaultAzureCredential

from adapters.databricks_adapter import DatabricksAdapter
from adapters.log_analytics_adapter import LogAnalyticsAdapter
from config import Config
from domain.service import EndpointMonitorService

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 */5 * * * *",  # 5分毎（要件に合わせて変更）
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def timerTrigger(myTimer: func.TimerRequest) -> None:
    """Timer Trigger ハンドラ。

    DI 組み立て・設定ロード・監視サイクル実行・結果ログ出力を行う。
    """
    if myTimer.past_due:
        logging.info("The timer is past due!")

    # TODO: 以下を実装する
    # 1. Config.from_env() で設定ロード
    # 2. DefaultAzureCredential（or ManagedIdentityCredential）生成
    # 3. DatabricksAdapter / LogAnalyticsAdapter 生成
    # 4. EndpointMonitorService 生成
    # 5. service.run(config.workspace_list) で監視実行
    # 6. adapter.send(records) で LA 送信
    # 7. 送信件数・結果をログ出力
    raise NotImplementedError