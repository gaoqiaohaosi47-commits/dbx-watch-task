# config.py
"""
アプリケーション設定。

設定キーの定義・説明は doc/AppSettings.md を参照。
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import List

from domain.model import WorkspaceConfig

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """アプリケーション設定の純粋データクラス。Azure 依存を持たない。"""

    workspace_list: List[WorkspaceConfig]
    dce_endpoint: str
    dcr_immutable_id: str
    dcr_stream_name: str


def load_config_from_env() -> Config:
    """環境変数から Config を生成・バリデーションする（Azure Functions 固有）。

    読み込む環境変数:
        WORKSPACE_LIST:    監視対象ワークスペースの JSON 配列（文字列）
        DCE_ENDPOINT:      Data Collection Endpoint の URL
        DCR_IMMUTABLE_ID:  DCR の Immutable ID
        DCR_STREAM_NAME:   DCR ストリーム名

    Returns:
        Config: バリデーション済みの設定オブジェクト。

    Raises:
        ValueError: 必須環境変数が未設定、WORKSPACE_LIST が不正な JSON、
                    または URL が https:// で始まらない場合。
    """
    logger.debug("設定ロード開始")

    def _require(key: str) -> str:
        val = os.environ.get(key)
        if not val:
            raise ValueError(f"必須環境変数 '{key}' が未設定です")
        return val

    def _validate_https_url(key: str, url: str) -> None:
        if not url.lower().startswith("https://"):
            raise ValueError(f"'{key}' は https:// で始まる必要があります: {url!r}")

    raw_workspace_list = _require("WORKSPACE_LIST")
    dce_endpoint = _require("DCE_ENDPOINT")
    dcr_immutable_id = _require("DCR_IMMUTABLE_ID")
    dcr_stream_name = _require("DCR_STREAM_NAME")

    _validate_https_url("DCE_ENDPOINT", dce_endpoint)

    try:
        workspace_data = json.loads(raw_workspace_list)
    except json.JSONDecodeError as e:
        raise ValueError(f"WORKSPACE_LIST が不正な JSON です: {e}") from e

    if not isinstance(workspace_data, list):
        raise ValueError("WORKSPACE_LIST は JSON 配列である必要があります")

    workspace_list: List[WorkspaceConfig] = []
    for i, item in enumerate(workspace_data):
        try:
            workspace_url = item["workspace_url"]
            _validate_https_url(f"WORKSPACE_LIST[{i}].workspace_url", workspace_url)
            workspace_list.append(WorkspaceConfig(
                workspace_id=item["workspace_id"],
                workspace_url=workspace_url.rstrip("/"),
                monitor_enabled=item["monitor_enabled"],
            ))
        except KeyError as e:
            raise ValueError(
                f"WORKSPACE_LIST[{i}] に必須フィールドがありません: {e}"
            ) from e

    logger.debug("設定ロード完了: ワークスペース %d 件", len(workspace_list))
    return Config(
        workspace_list=workspace_list,
        dce_endpoint=dce_endpoint,
        dcr_immutable_id=dcr_immutable_id,
        dcr_stream_name=dcr_stream_name,
    )
