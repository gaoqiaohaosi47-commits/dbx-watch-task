# adapters/log_analytics_adapter.py
"""
Log Analytics アダプター。LogSenderPort の Azure 向け実装。

Azure Monitor Ingestion SDK（LogsIngestionClient）を使って
Log Analytics カスタムテーブルにレコードを一括送信する。

参照: local/poc.py, doc/AppSettings.md
"""
from __future__ import annotations

import logging
from typing import List

from azure.core.credentials import TokenCredential
from azure.monitor.ingestion import LogsIngestionClient

from domain.model import EndpointRecord
from ports.log_sender_port import LogSenderPort

logger = logging.getLogger(__name__)


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
        2. 各 EndpointRecord を to_log_dict() で LA フィールド名の dict に変換
        3. LogsIngestionClient.upload() で一括送信（1 回の API コール）

        Args:
            records: 送信するレコードのリスト。

        Raises:
            azure.core.exceptions.HttpResponseError: インジェスト API エラー（認証失敗・不正な DCR ID 等）。
        """
        if not records:
            logger.info("送信レコードなし。スキップ。")
            return

        logs = [record.to_log_dict() for record in records]
        self._client.upload(
            rule_id=self._dcr_immutable_id,
            stream_name=self._dcr_stream_name,
            logs=logs,
        )
        logger.info("Log Analytics に %d 件を送信しました", len(logs))
