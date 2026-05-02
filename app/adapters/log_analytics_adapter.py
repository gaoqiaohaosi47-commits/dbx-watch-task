# adapters/log_analytics_adapter.py
"""
Log Analytics アダプター。LogSenderPort の Azure 向け実装。

Azure Monitor Ingestion SDK（LogsIngestionClient）を使って
Log Analytics カスタムテーブルにレコードを一括送信する。
送信失敗時はエクスポーネンシャルバックオフでリトライする。

参照: local/poc.py, doc/AppSettings.md
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from azure.core.credentials import TokenCredential
from azure.monitor.ingestion import LogsIngestionClient

from domain.model import EndpointRecord
from ports.log_sender_port import LogSenderPort

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # 秒


def _to_log_dict(record: EndpointRecord) -> Dict[str, Any]:
    """EndpointRecord を Log Analytics インジェスト用 dict に変換する。

    ドメインモデルの snake_case フィールドを LA フィールド名（TimeGenerated 等）にマッピングする。
    変換ロジックはアダプター層のみに閉じる（ヘキサゴナルアーキ整合）。
    """
    return {
        "TimeGenerated": record.time_generated,
        "workspace_id": record.workspace_id,
        "workspace_url": record.workspace_url,
        "api_status_code": record.api_status_code,
        "api_error_message": record.api_error_message,
        "endpoint_name": record.endpoint_name,
        "endpoint_state": record.endpoint_state,
        "endpoint_raw_data": record.endpoint_raw_data,
    }


class LogAnalyticsAdapter(LogSenderPort):
    """Azure Monitor Logs Ingestion API を使った Log Analytics 送信アダプター。"""

    def __init__(
        self,
        credential: TokenCredential,
        dce_endpoint: str,
        dcr_immutable_id: str,
        dcr_stream_name: str,
    ) -> None:
        """
        Args:
            credential: DCR に対して Monitoring Metrics Publisher ロールを持つ認証クレデンシャル。
            dce_endpoint: Data Collection Endpoint の URL（DCE_ENDPOINT 環境変数）。
            dcr_immutable_id: DCR の Immutable ID（DCR_IMMUTABLE_ID 環境変数）。
            dcr_stream_name: DCR ストリーム名（DCR_STREAM_NAME 環境変数）。
        """
        self._client = LogsIngestionClient(endpoint=dce_endpoint, credential=credential)
        self._dcr_immutable_id = dcr_immutable_id
        self._dcr_stream_name = dcr_stream_name

    def send(self, records: List[EndpointRecord]) -> None:
        """レコードを Log Analytics に一括アップロードする。

        1. records が空の場合は早期リターン（API 呼び出しなし）
        2. 各 EndpointRecord を LA フィールド名の dict に変換
        3. LogsIngestionClient.upload() で一括送信
           失敗時はエクスポーネンシャルバックオフ（1s, 2s）で最大 _MAX_RETRIES 回リトライ

        Args:
            records: 送信するレコードのリスト。

        Raises:
            Exception: _MAX_RETRIES 回リトライ後も失敗した場合に最後の例外を送出。
        """
        if not records:
            logger.info("送信レコードなし。スキップ。")
            return

        logger.debug("send 開始: %d 件", len(records))
        logs = [_to_log_dict(record) for record in records]

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                self._client.upload(
                    rule_id=self._dcr_immutable_id,
                    stream_name=self._dcr_stream_name,
                    logs=logs,
                )
                logger.info("Log Analytics に %d 件を送信しました", len(logs))
                logger.debug("send 完了")
                return
            except Exception as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "送信失敗（%d/%d 回目）、%.1f 秒後にリトライ: %s",
                        attempt, _MAX_RETRIES, delay, e,
                    )
                    time.sleep(delay)
                else:
                    logger.error("送信失敗（%d 回試行）: %s", _MAX_RETRIES, e)

        assert last_exc is not None
        raise last_exc
