# function_app.py
"""
Azure Functions エントリーポイント（Timer Trigger）。

責務:
- 遅延初期化（初回 Trigger 呼び出し時に DI 組み立て）
- EndpointMonitorService の実行
- 実行結果ログ出力
"""
from __future__ import annotations

import logging

import azure.functions as func
from azure.identity import DefaultAzureCredential

from adapters.databricks_adapter import DatabricksAdapter
from adapters.log_analytics_adapter import LogAnalyticsAdapter
from config import Config, load_config_from_env
from domain.service import EndpointMonitorService

logger = logging.getLogger(__name__)

# ウォームインスタンス間で再利用するモジュールレベルキャッシュ。
# モジュールインポート時には初期化しない（load_config_from_env() 失敗で
# Function がロード不能になることを防ぐ）。
_config: Config | None = None
_log_analytics_adapter: LogAnalyticsAdapter | None = None
_service: EndpointMonitorService | None = None


def _ensure_initialized() -> None:
    """初回呼び出し時にのみ DI オブジェクトをすべて初期化する。"""
    global _config, _log_analytics_adapter, _service
    if _config is not None:
        return
    logger.debug("初期化開始")
    _config = load_config_from_env()
    credential = DefaultAzureCredential()
    _log_analytics_adapter = LogAnalyticsAdapter(
        credential=credential,
        dce_endpoint=_config.dce_endpoint,
        dcr_immutable_id=_config.dcr_immutable_id,
        dcr_stream_name=_config.dcr_stream_name,
    )
    _service = EndpointMonitorService(
        endpoint_port=DatabricksAdapter(credential),
    )
    logger.debug("初期化完了")


app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 */30 * * * *",
    arg_name="myTimer",
    run_on_startup=False,
)
def timerTrigger(myTimer: func.TimerRequest) -> None:
    """Timer Trigger ハンドラ。"""
    if myTimer.past_due:
        logger.info("The timer is past due!")

    _ensure_initialized()

    try:
        records = _service.run(_config.workspace_list)
        _log_analytics_adapter.send(records)
        logger.info("[実行完了] 送信レコード数: %d", len(records))
    except Exception as e:
        logger.error("[実行エラー] %s", e, exc_info=True)
        raise
