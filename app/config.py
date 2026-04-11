# config.py
"""
アプリケーション設定ローダー。

Azure Function の App Settings（環境変数）から設定を読み込み、バリデーションする。
設定キーの定義・説明は doc/AppSettings.md を参照。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List

from domain.model import WorkspaceConfig


@dataclass
class Config:
    """環境変数から読み込んだアプリケーション設定。"""

    workspace_list: List[WorkspaceConfig]
    dce_endpoint: str
    dcr_immutable_id: str
    dcr_stream_name: str

    @classmethod
    def from_env(cls) -> Config:
        """環境変数からConfigを生成・バリデーションする。

        読み込む環境変数:
            WORKSPACE_LIST:    監視対象ワークスペースの JSON 配列（文字列）
            DCE_ENDPOINT:      Data Collection Endpoint の URL
            DCR_IMMUTABLE_ID:  DCR の Immutable ID
            DCR_STREAM_NAME:   DCR ストリーム名

        Returns:
            Config: バリデーション済みの設定オブジェクト。

        Raises:
            ValueError: 必須環境変数が未設定、または WORKSPACE_LIST が不正な JSON の場合。
        """
        def _require(key: str) -> str:
            val = os.environ.get(key)
            if not val:
                raise ValueError(f"必須環境変数 '{key}' が未設定です")
            return val

        raw_workspace_list = _require("WORKSPACE_LIST")
        dce_endpoint = _require("DCE_ENDPOINT")
        dcr_immutable_id = _require("DCR_IMMUTABLE_ID")
        dcr_stream_name = _require("DCR_STREAM_NAME")

        try:
            workspace_data = json.loads(raw_workspace_list)
        except json.JSONDecodeError as e:
            raise ValueError(f"WORKSPACE_LIST が不正な JSON です: {e}") from e

        if not isinstance(workspace_data, list):
            raise ValueError("WORKSPACE_LIST は JSON 配列である必要があります")

        workspace_list: List[WorkspaceConfig] = []
        for i, item in enumerate(workspace_data):
            try:
                workspace_list.append(WorkspaceConfig(
                    workspace_id=item["workspace_id"],
                    workspace_url=item["workspace_url"],
                    monitor_enabled=item["monitor_enabled"],
                ))
            except KeyError as e:
                raise ValueError(
                    f"WORKSPACE_LIST[{i}] に必須フィールドがありません: {e}"
                ) from e

        return cls(
            workspace_list=workspace_list,
            dce_endpoint=dce_endpoint,
            dcr_immutable_id=dcr_immutable_id,
            dcr_stream_name=dcr_stream_name,
        )
