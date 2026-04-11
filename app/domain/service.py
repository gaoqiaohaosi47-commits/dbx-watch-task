# domain/service.py
"""
エンドポイント監視のオーケストレーション（ユースケース層）。

Azure・Databricks への直接依存を持たない純粋なビジネスロジック。
外部との通信はすべてポートインターフェース経由で行う。
"""
from __future__ import annotations

import logging
from typing import List

from domain.model import EndpointRecord, WorkspaceConfig
from ports.log_sender_port import LogSenderPort
from ports.serving_endpoint_port import ServingEndpointPort

logger = logging.getLogger(__name__)


class EndpointMonitorService:
    """全監視対象ワークスペースの 1 サイクル監視を行うサービス。

    ポート実装（アダプター）をコンストラクタで注入する。
    Azure / Databricks SDK の知識を持たない。
    """

    def __init__(
        self,
        endpoint_port: ServingEndpointPort,
        log_sender_port: LogSenderPort,
    ) -> None:
        """
        Args:
            endpoint_port: Databricks サービングエンドポイント取得の実装。
            log_sender_port: Log Analytics 送信の実装。
        """
        # TODO: 実装する
        raise NotImplementedError

    def run(self, workspace_list: List[WorkspaceConfig]) -> List[EndpointRecord]:
        """全ワークスペースに対して監視サイクルを実行する。

        monitor_enabled=True のワークスペースのみ処理する。
        1 件のワークスペース処理が失敗しても、他ワークスペースへの処理を継続する。

        Args:
            workspace_list: 監視対象ワークスペースの一覧。

        Returns:
            List[EndpointRecord]: 全レコード（正常・エラー）の結合リスト。
        """
        # TODO: 実装する
        raise NotImplementedError

    def _process_workspace(self, workspace: WorkspaceConfig) -> List[EndpointRecord]:
        """1 ワークスペース分のレコードを生成する。

        API 呼び出し成功時はエンドポイント単位でレコードを生成し、
        失敗時はワークスペース単位でエラーレコードを 1 件生成する。

        Args:
            workspace: 処理対象のワークスペース。

        Returns:
            List[EndpointRecord]: 成功時は N 件（エンドポイント数）、失敗時は 1 件。
        """
        # TODO: 実装する
        raise NotImplementedError
