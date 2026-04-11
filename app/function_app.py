# function_app.py
"""
Azure Functions エントリーポイント（Timer Trigger）。

責務:
- モジュールレベルで DI 組み立て（ウォームインスタンス間で再利用）
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

# モジュールレベルで初期化することでウォームインスタンス間の再初期化コストを回避する。
# Azure Functions は同一インスタンスで複数回起動されるためここで生成した
# オブジェクトはプロセス生存中に再利用される。
_config = Config.from_env()
_credential = DefaultAzureCredential()
_log_analytics_adapter = LogAnalyticsAdapter(
    credential=_credential,
    dce_endpoint=_config.dce_endpoint,
    dcr_immutable_id=_config.dcr_immutable_id,
    dcr_stream_name=_config.dcr_stream_name,
)
_service = EndpointMonitorService(
    endpoint_port=DatabricksAdapter(_credential),
)

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 */30 * * * *",  # 30分毎（要件に合わせて変更）
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def timerTrigger(myTimer: func.TimerRequest) -> None:
    """Timer Trigger ハンドラ。"""
    if myTimer.past_due:
        logging.info("The timer is past due!")

    try:
        records = _service.run(_config.workspace_list)
        _log_analytics_adapter.send(records)
        logging.info("[実行完了] 送信レコード数: %d", len(records))
    except Exception as e:
        logging.error("[実行エラー] %s", e, exc_info=True)
        raise