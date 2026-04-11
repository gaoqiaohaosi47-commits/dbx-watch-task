# tests/unit/test_ports.py
"""
ports/ の ABC 強制テスト。
対象: ServingEndpointPort, LogSenderPort
"""
import pytest

from ports.log_sender_port import LogSenderPort
from ports.serving_endpoint_port import ServingEndpointPort


# UT-21: ServingEndpointPort — 抽象メソッド未実装のサブクラスはインスタンス化不可
def test_serving_endpoint_port_cannot_instantiate_without_implementation():
    class IncompleteAdapter(ServingEndpointPort):
        pass

    with pytest.raises(TypeError):
        IncompleteAdapter()


# UT-22: LogSenderPort — 抽象メソッド未実装のサブクラスはインスタンス化不可
def test_log_sender_port_cannot_instantiate_without_implementation():
    class IncompleteAdapter(LogSenderPort):
        pass

    with pytest.raises(TypeError):
        IncompleteAdapter()


# UT-extra: ServingEndpointPort — 正しく実装したサブクラスはインスタンス化可能
def test_serving_endpoint_port_valid_implementation():
    class ValidAdapter(ServingEndpointPort):
        def fetch_endpoints(self, workspace):
            return []

    adapter = ValidAdapter()
    assert isinstance(adapter, ServingEndpointPort)


# UT-extra: LogSenderPort — 正しく実装したサブクラスはインスタンス化可能
def test_log_sender_port_valid_implementation():
    class ValidAdapter(LogSenderPort):
        def send(self, records):
            pass

    adapter = ValidAdapter()
    assert isinstance(adapter, LogSenderPort)
