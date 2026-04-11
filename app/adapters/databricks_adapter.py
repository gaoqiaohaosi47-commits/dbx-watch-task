# adapters/databricks_adapter.py
"""
Databricks アダプター。ServingEndpointPort の Azure 向け実装。

Databricks SDK（WorkspaceClient）を使ってサービングエンドポイント情報を取得する。
Azure マネージドID のトークンを明示的に取得し、WorkspaceClient に渡す POC 実績パターンを採用。

参照: local/poc.py
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from azure.core.credentials import TokenCredential
from databricks.sdk import WorkspaceClient

from domain.model import WorkspaceConfig
from ports.serving_endpoint_port import ServingEndpointPort

logger = logging.getLogger(__name__)

# Azure 全体で固定の Databricks サービスリソース ID
AZURE_DATABRICKS_RESOURCE_ID = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"

# Databricks API の HTTP タイムアウト（秒）
# 存在しないホストへの接続待機を抑制する
HTTP_TIMEOUT_SECONDS = 30


class DatabricksAdapter(ServingEndpointPort):
    """Databricks SDK を使ったサービングエンドポイント取得アダプター。

    ワークスペース毎に WorkspaceClient を新規初期化する。
    （各ワークスペースはホスト URL が異なるため共有不可）
    credential は共有して再利用する。
    """

    def __init__(self, credential: TokenCredential) -> None:
        """
        Args:
            credential: Azure 認証クレデンシャル。
                ローカル: DefaultAzureCredential
                本番: ManagedIdentityCredential
                テスト: モッククレデンシャル
        """
        self._credential = credential

    def fetch_endpoints(self, workspace: WorkspaceConfig) -> List[Dict[str, Any]]:
        """指定ワークスペースの全サービングエンドポイントを取得する。

        1. credential.get_token() で Azure Databricks スコープのトークンを取得
        2. WorkspaceClient(host=workspace_url, token=token.token) を初期化
        3. serving_endpoints.list() を呼び出し
        4. 各エンドポイントを as_dict() で dict に変換して返す

        Args:
            workspace: 取得対象ワークスペース。workspace_url をホスト URL として使用。

        Returns:
            List[Dict[str, Any]]: エンドポイントの dict リスト。
                Databricks API レスポンスの各エンドポイント情報（as_dict() 結果）。

        Raises:
            databricks.sdk.errors.DatabricksError: 認証・権限・API エラー。
            Exception: その他の接続エラー（タイムアウト等）。
        """
        token = self._credential.get_token(f"{AZURE_DATABRICKS_RESOURCE_ID}/.default")
        w = WorkspaceClient(
            host=workspace.workspace_url,
            token=token.token,
            http_timeout_seconds=HTTP_TIMEOUT_SECONDS,
        )
        endpoints = w.serving_endpoints.list()
        return [ep.as_dict() for ep in endpoints]
