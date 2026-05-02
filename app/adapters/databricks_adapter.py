# adapters/databricks_adapter.py
"""
Databricks アダプター。ServingEndpointPort の Azure 向け実装。

Databricks REST API（requests）を使ってサービングエンドポイント情報を取得する。
Azure マネージドID のトークンを Bearer ヘッダーにセットして直接 REST API を呼び出す。

Databricks SDK は使用しない（Managed ID 非対応・タイムアウト制御が複雑なため）。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests
from azure.core.credentials import TokenCredential

from domain.model import WorkspaceConfig
from ports.serving_endpoint_port import ServingEndpointPort

logger = logging.getLogger(__name__)

# Azure 全体で固定の Databricks サービスリソース ID
AZURE_DATABRICKS_RESOURCE_ID = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"

# Databricks API の HTTP タイムアウト（秒）
HTTP_TIMEOUT_SECONDS = 30


class DatabricksAdapter(ServingEndpointPort):
    """Databricks REST API を使ったサービングエンドポイント取得アダプター。

    ワークスペース毎に REST API へリクエストを送信する。
    credential は共有して再利用し、都度トークンを取得して Bearer ヘッダーにセットする。
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
        2. GET /api/2.0/serving-endpoints を Bearer 認証で呼び出す
        3. レスポンス JSON の "endpoints" リストを返す

        Args:
            workspace: 取得対象ワークスペース。workspace_url をベースに URL を構築。

        Returns:
            List[Dict[str, Any]]: エンドポイントの dict リスト（REST API レスポンス JSON）。

        Raises:
            TimeoutError: HTTP_TIMEOUT_SECONDS 以内に完了しなかった場合。
            requests.HTTPError: HTTP エラー応答。status_code 属性にコードを付与して再送出。
            Exception: その他の接続エラー。
        """
        logger.debug("fetch_endpoints 開始: %s", workspace.workspace_url)
        token = self._credential.get_token(f"{AZURE_DATABRICKS_RESOURCE_ID}/.default")
        url = f"{workspace.workspace_url}/api/2.0/serving-endpoints"

        try:
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {token.token}"},
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        except requests.Timeout:
            raise TimeoutError(
                f"Timed out after {HTTP_TIMEOUT_SECONDS}s: {workspace.workspace_url}"
            )

        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            # service.py の getattr(e, "status_code", 0) で参照できるよう属性を付与する
            e.status_code = e.response.status_code
            raise

        endpoints = resp.json().get("endpoints", [])
        logger.debug("fetch_endpoints 完了: %s - %d 件", workspace.workspace_url, len(endpoints))
        return endpoints
