# domain/model.py
"""
ドメインデータモデル。

Azure・Databricks への依存を一切持たない純粋な Python データクラス群。
フィールド定義の詳細は doc/DataModel.md を参照。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class WorkspaceConfig:
    """監視対象の Databricks ワークスペース設定。

    WORKSPACE_LIST 環境変数の JSON 配列要素 1 件に対応する。
    """

    workspace_id: str
    workspace_url: str
    monitor_enabled: bool


@dataclass
class EndpointRecord:
    """Log Analytics に送信する 1 レコード。

    成功時（エンドポイント 1 件ごと）:
        api_status_code = 200
        api_error_message = None
        endpoint_name, endpoint_state, endpoint_raw_data に値あり

    失敗時（ワークスペース 1 件ごと）:
        api_status_code = HTTP エラーコード or 0（非 HTTP エラー）
        api_error_message = エラー内容
        endpoint_name, endpoint_state, endpoint_raw_data = None

    LA フィールド名への変換は LogAnalyticsAdapter が担う（adapters/log_analytics_adapter.py 参照）。
    """

    time_generated: str                         # ISO 8601 UTC 形式
    workspace_id: str
    workspace_url: str
    api_status_code: int
    api_error_message: Optional[str]
    endpoint_name: Optional[str]
    endpoint_state: Optional[str]
    endpoint_raw_data: Optional[Dict[str, Any]]
