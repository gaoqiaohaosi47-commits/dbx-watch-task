# domain/service.py
"""
エンドポイント監視のオーケストレーション（ユースケース層）。

Azure・Databricks への直接依存を持たない純粋なビジネスロジック。
外部との通信はすべてポートインターフェース経由で行う。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from domain.model import EndpointRecord, WorkspaceConfig
from ports.serving_endpoint_port import ServingEndpointPort

logger = logging.getLogger(__name__)


class EndpointMonitorService:
    """全監視対象ワークスペースの 1 サイクル監視を行うサービス。

    ポート実装（アダプター）をコンストラクタで注入する。
    Azure / Databricks SDK の知識を持たない。
    """

    def __init__(self, endpoint_port: ServingEndpointPort) -> None:
        """
        Args:
            endpoint_port: Databricks サービングエンドポイント取得の実装。
        """
        self._endpoint_port = endpoint_port

    def run(self, workspace_list: List[WorkspaceConfig]) -> List[EndpointRecord]:
        """全ワークスペースに対して監視サイクルを実行する。

        monitor_enabled=True のワークスペースのみ処理する。
        1 件のワークスペース処理が失敗しても、他ワークスペースへの処理を継続する。

        Args:
            workspace_list: 監視対象ワークスペースの一覧。

        Returns:
            List[EndpointRecord]: 全レコード（正常・エラー）の結合リスト。
        """
        all_records: List[EndpointRecord] = []
        for workspace in workspace_list:
            if not workspace.monitor_enabled:
                logger.info("スキップ: %s (monitor_enabled=False)", workspace.workspace_url)
                continue
            records = self._process_workspace(workspace)
            all_records.extend(records)
        return all_records

    def _process_workspace(self, workspace: WorkspaceConfig) -> List[EndpointRecord]:
        """1 ワークスペース分のレコードを生成する。

        API 呼び出し成功時はエンドポイント単位でレコードを生成し、
        失敗時はワークスペース単位でエラーレコードを 1 件生成する。

        Args:
            workspace: 処理対象のワークスペース。

        Returns:
            List[EndpointRecord]: 成功時は N 件（エンドポイント数）、失敗時は 1 件。
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            endpoints = self._endpoint_port.fetch_endpoints(workspace)
            records = [
                EndpointRecord(
                    time_generated=timestamp,
                    workspace_id=workspace.workspace_id,
                    workspace_url=workspace.workspace_url,
                    api_status_code=200,
                    api_error_message=None,
                    endpoint_name=ep_dict.get("name"),
                    endpoint_state=ep_dict.get("state", {}).get("ready"),
                    endpoint_raw_data=ep_dict,
                )
                for ep_dict in endpoints
            ]
            logger.info(
                "取得完了: %s - エンドポイント %d 件",
                workspace.workspace_url, len(records),
            )
            return records
        except Exception as e:
            status_code: int = getattr(e, "status_code", 0)
            logger.error(
                "ワークスペース %s の処理に失敗 (status=%s): %s",
                workspace.workspace_url, status_code, e,
            )
            return [EndpointRecord(
                time_generated=timestamp,
                workspace_id=workspace.workspace_id,
                workspace_url=workspace.workspace_url,
                api_status_code=status_code,
                api_error_message=str(e),
                endpoint_name=None,
                endpoint_state=None,
                endpoint_raw_data=None,
            )]
