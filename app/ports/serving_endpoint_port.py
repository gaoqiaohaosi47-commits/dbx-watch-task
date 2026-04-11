# ports/serving_endpoint_port.py
"""
Databricks サービングエンドポイント取得のポートインターフェース（抽象）。

このポートを実装するアダプターは Databricks SDK や HTTP クライアントなど
具体的な取得手段を持つ。ドメイン層はこの ABC のみを参照する。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from domain.model import WorkspaceConfig


class ServingEndpointPort(ABC):
    """Databricks ワークスペースからサービングエンドポイント情報を取得する抽象ポート。"""

    @abstractmethod
    def fetch_endpoints(self, workspace: WorkspaceConfig) -> List[Dict[str, Any]]:
        """指定されたワークスペースの全サービングエンドポイントを取得する。

        Args:
            workspace: 取得対象のワークスペース設定。

        Returns:
            List[Dict[str, Any]]: エンドポイント情報の dict リスト。
                各 dict は少なくとも 'name' と 'state' キーを含む。
                Databricks SDK の as_dict() 結果を想定。

        Raises:
            Exception: 認証失敗・ネットワークエラー等の例外をそのまま raise する。
                サービス層でキャッチしてエラーレコードに変換する。
        """
        ...
