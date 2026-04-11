# ports/log_sender_port.py
"""
ログ送信のポートインターフェース（抽象）。

Azure Log Analytics・AWS CloudWatch など、送信先を抽象化する。
将来のマルチクラウド対応において、このポートを差し替えることでドメイン層を変更せずに
送信先を変更できる。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from domain.model import EndpointRecord


class LogSenderPort(ABC):
    """EndpointRecord をログ収集基盤へ送信する抽象ポート。"""

    @abstractmethod
    def send(self, records: List[EndpointRecord]) -> None:
        """レコードのリストをログ収集基盤に一括送信する。

        Args:
            records: 送信するレコードのリスト。空リストの場合は送信処理をスキップする。

        Raises:
            Exception: 認証失敗・API エラー等の例外を raise する。
                function_app.py に伝播させて最終ログ出力する。
        """
        ...
