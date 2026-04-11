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
        # TODO: 実装する
        raise NotImplementedError
